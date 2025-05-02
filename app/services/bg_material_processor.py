import asyncio
import base64
import logging
import os
import random
from typing import Optional, TextIO, Callable, Dict, List
from itertools import chain

import portalocker
import requests
from pydantic import FilePath

from app.models import CourseMaterialData, Grade, GradedStudentResponseReference
from app.services import AzureBlobService, AzureEmbeddingService
from app.services.azure_embedding_service import CohereEmbeddingService, EmbeddingInputType
from app.services.vector_db_service import ChromaDBService
from app.utils.bytes_to_doc_util import Document, DataType
from app.utils.error_handling_tpe import ErrorHandlingThreadPool
from app.utils.llm_service import LLMService, PromptRole, PromptBuilder

"""
Process material files in the background including processing the RAG pipeline for the course
material and the grading pipeline for the assignment. When an API endpoint submits course material,
it gets saved to a file and this background task scans that predefined directory for stuff to process.
The reason we do it like this is because:
1. Grading/RAG pipeline takes too long and API clients might timeout.
2. Holding all the course materials might be bad for memory.
3. If the process is killed, we don't want to lose the request.
4. In production, there might be multiple processes of FastAPI that are truly parallel so this
   approach has the added advantage of true multi-threading (not usually easily possible in Python).
"""


def process_grading(json_str: str):
    """
    Processes student grading for a specific student response.
    """

    #  Step 0: Convert the json string into a student response object and download raw binary content of response
    student_response = GradedStudentResponseReference.model_validate_json(json_str)
    binary_content = requests.get(student_response.data.uri).content
    #  Step 1: Convert the student's response (which might be a pdf, txt, etc)
    #          into a Document object that we can work with.
    covert_to_doc = student_response.data.data_type.get_to_doc_func()
    student_response_documents = covert_to_doc(
        f"student_response.{student_response.data.data_type.extension}",
        binary_content,
        False
    )
    #  Step 2: Grab the rubric for the assignment and the question instructions
    blob_service = AzureBlobService.get_instance()
    rubric = blob_service.get_rubric(
        student_response.semester, student_response.course_id,
        student_response.assignment_id, False
    )
    rubric.sub_rubrics = [blob_service.get_sub_rubric(
        student_response.semester, student_response.course_id,
        student_response.assignment_id, student_response.question_index
    )]
    assignment = blob_service.get_assignment_metadata(
        semester_key=student_response.semester,
        course_id=student_response.course_id,
        assignment_id=student_response.assignment_id,
    )
    assignment.questions = blob_service.list_questions(student_response.semester,
                                                       student_response.course_id,
                                                       student_response.assignment_id)
    assignment_question = assignment.questions[student_response.question_index]
    #  Step 3: Query the vector database with the student's response grabbing all topn
    #          relevant documents.

    # Step 3a: Compile a list of relevant course materials using the student's response, the question,
    # and the rubric.
    embedding_service = CohereEmbeddingService.get_instance()
    student_response_embeddings: List[List[float]] = []
    for id, response_chunk in student_response_documents.contents.items():
        if response_chunk.data_type.is_text():
            vector = embedding_service.embed_text(response_chunk.get_as_string(), EmbeddingInputType.SEARCH_QUERY)
        else:
            b64_img = base64.b64encode(response_chunk.get_as_bytes()).decode('utf-8')
            vector = embedding_service.embed_image(response_chunk.data_type.mime_type, b64_img)
        student_response_embeddings.append(vector)
    vector_db = ChromaDBService.get_instance()
    # todo: top k is pretty naive
    relevant_document_paths: List[List[str]] = vector_db.search(student_response.semester, student_response.course_id, student_response_embeddings, top_k=5)
    relevant_document_paths: List[str] = chain.from_iterable(relevant_document_paths)  # flatten list

    #  Step 4: Go grab those documents (texts and images) from Azure blob storage. It might
    #          also be possible to simply get azure to generate a URL for these documents
    #          and then send that to the LLM.
    course_material_documents = blob_service.get_chunks_from_blob_path(relevant_document_paths)
    #  Step 5: Once we have the RAG-ed documents associated with the prompt, use the
    #          assignment instructions, rubric, RAG-ed course material chunks, and student
    #          response to generate a prompt for auto-grading.
    prompt = (PromptBuilder.builder()
              .add_message(PromptRole.SYSTEM, "You are a grader responsible for grading a student's response "
                                              "ensuring accuracy and fairness.")
              .add_message(PromptRole.USER, "Here is course material that might be relevant to this assignment."
                                            "When evaluating accuracy for your grades, in your grading responses, "
                                            "cite these relevant sources including with any in the following format: "
                                            "[source_name - page_numbers if present]. Only use this citation for the"
                                            " course material."))

    for file_name, document in course_material_documents:
        assert document.data_type.is_fundamental()
        doc_ref_str = f"Document name: {file_name}"
        if 'page_num' in document.metadata:
            doc_ref_str += f" (Page(s): {document.metadata['page_num']})"
        prompt.add_message(PromptRole.USER, doc_ref_str)
        if document.data_type.is_image():
            prompt.add_image_bytes(PromptRole.USER, document.content, document.data_type.mime_type)
        elif document.data_type.is_text():
            prompt.add_message(PromptRole.USER, document.get_as_string())

    (prompt.add_message(PromptRole.USER, "We have reached the end of the course material.")
     .add_message(PromptRole.USER, "The instructions for this assignment are as follows. Use this information as"
                                   "context to evaluate whether the student completed all that was asked in the "
                                   "question alongside the Rubric:")
     .add_json_input(PromptRole.USER, assignment, excluded_fields={"questions"})
     .add_json_input(PromptRole.USER, assignment_question)
     .add_message(PromptRole.USER, "Grading for this assignment should be"
                                   "exclusively based on the following rubric. You are required to explicitly "
                                   "reference the rubric explaining which parts of the rubric did the student fulfill "
                                   "and which parts the student missed (if any).")
     .add_json_input(PromptRole.USER, rubric))
    for grading_flag in rubric.grading_flags:
        prompt.add_message(PromptRole.USER, f"Since the rubric is marked with the flag: {grading_flag.value},"
                                            f"it means you should: {grading_flag.get_description()}")

    prompt.add_message(PromptRole.USER, "Here is the student's response which you are grading:")
    for chunk_id, resp_chunk in student_response_documents.contents.items():
        if resp_chunk.data_type.is_image():
            prompt.add_image_bytes(PromptRole.USER, resp_chunk.content, resp_chunk.data_type.mime_type)
        elif resp_chunk.data_type.is_text():
            prompt.add_message(PromptRole.USER, resp_chunk.get_as_string())

    logging.debug(f"Sending the following prompt to the LLM:\n{prompt.debug_string()}")

    #  Step 6: Grab the auto-graded response, upload it to Azure, and move on to the next assignment
    #          in the queue (if any).
    llm = LLMService.get_instance()
    student_grade = llm.generate_structured_response(
        prompt.build(),
        Grade
    )
    blob_service.upload_student_grade(
        semester_key=student_response.semester,
        course_id=student_response.course_id,
        assignment_id=student_response.assignment_id,
        question_index=student_response.question_index,
        student_id=student_response.student_id,
        grade=student_grade
    )


def process_course_material(json_str: str):
    """
    Processes submitted course material. This function is called by
    bg_material_processor.py. See its logic for more details
    """

    #  Step 0: Convert the json string into CourseMaterialData
    course_material = CourseMaterialData.model_validate_json(json_str)
    #  Step 2: Convert the binary data of the course material into document chunks using
    #          bytes_to_doc_util.py.
    to_doc_func = course_material.data.data_type.get_to_doc_func()
    document: Document = to_doc_func(
        f"{course_material.material_id}.{course_material.data.data_type.extension}",
        course_material.data.content_as_bytes(),
        True
    )
    #  Step 3: Upload these chunks to azure and get the blob paths
    blob_uploader = AzureBlobService.get_instance()
    uploaded_chunks: Dict[int, str] = blob_uploader.upload_material_chunks(
        course_material.semester,
        course_material.course_id,
        course_material.material_id,
        document
    )
    #  Step 4: Vectorize the chunks (text or images).
    embedding_service = CohereEmbeddingService.get_instance()
    vectorized_chunks: Dict[str, List[float]] = {}  # the key is blob_path, value is vector
    text_paths: List[str] = []
    texts: List[str] = []
    for chunk_id, chunk_path in uploaded_chunks.items():
        # if the way this is handled looks a bit convoluted, just know there is logic to the madness:
        # specifically there are performance benefits to vectorizing a batch of texts together
        # but on the other hand, images cannot be batched and must be processed individually
        chunked_doc = document.get_chunk(chunk_id)
        if chunked_doc.data_type.is_image():
            vectorized_chunks[chunk_path] = embedding_service.embed_image(
                chunked_doc.data_type.mime_type, chunked_doc.get_as_base64()
            )
        elif chunked_doc.data_type == DataType.TEXT:
            text_paths.append(chunk_path)
            texts.append(chunked_doc.get_as_string()[:100])
        else:
            # the data types should only be either image or text
            raise Exception(f"Unsupported data type: {course_material.data.data_type}")
    vectors = embedding_service.embed_texts(texts, EmbeddingInputType.DOCUMENT)

    for blob_path, vector in zip(text_paths, vectors):
        vectorized_chunks[blob_path] = vector
    #  Step 5: Take the pairs of the blob paths and vectorized chunks, and upload them
    #          to Azure's AI search. And thats it!
    vector_service = ChromaDBService.get_instance()
    vector_ids = list(vectorized_chunks.keys())  # Using blob_paths as vector IDs
    vector_values = list(vectorized_chunks.values())

    vector_service.add_vectors(
        course_material.semester,
        course_material.course_id,
        vector_ids,
        vector_values
    )



class BackgroundMaterialProcessor:
    save_dir: FilePath

    def __init__(self, save_dir: FilePath):
        if not save_dir.exists():
            save_dir.mkdir(parents=True)
        if not save_dir.is_dir():
            raise ValueError(f"save_dir must be a directory, got {save_dir}")
        self.save_dir = save_dir
        self.executor = ErrorHandlingThreadPool(max_workers=4)

    def start_task_scan_loop(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._scan_loop())

    async def _scan_loop(self):
        while True:
            files = os.listdir(self.save_dir)
            # randomly permute to improve the chances
            # of a fair distribution between processes
            random.shuffle(files)
            for file in files:

                process_func: Callable[[str], None]
                if file.endswith(".course_materials.json"):
                    process_func = process_course_material
                elif file.endswith(".student_response.json"):
                    process_func = process_grading
                else:
                    logging.warning(f"Unknown file type: {file} in unprocessed files. Skipping.")
                    continue

                self.executor.submit(self.process, self.save_dir / file, process_func)

                # add a small random delay between to improve the
                # chances of a fair distribution between processes
                await asyncio.sleep(random.random() * 0.25)
            # sleep for 30 seconds
            await asyncio.sleep(30)

    @classmethod
    def process(cls, file_path: FilePath, process_func: Callable[[str], None] = None):
        f = cls.open_file_with_lock(file_path, "r+")
        if f is None:
            return
        content = f.read()
        # if the file is empty, it was already processed
        if not content.strip():
            logging.info(f"{file_path} already processed. Skipping.")
            cls.safe_delete(file_path)
            f.close()
            return
        logging.info(f"Processing {file_path}")
        process_func(content)
        # can't delete the file in all platforms without releasing the lock
        # and so to prevent duplicate processing (since we will need to release the
        # lock to actually delete it), we first wipe the contents of the file
        f.seek(0)
        f.truncate()
        f.close()
        # attempt safe deletion
        cls.safe_delete(file_path)

    """
    Open a file for reading and locking it. Must do so since there might be multiple processes
    trying to read the same file.
    """

    @classmethod
    def open_file_with_lock(cls, file_path: FilePath, mode: str) -> Optional[TextIO]:
        try:
            lockfile = open(file_path, mode)
            portalocker.lock(lockfile, portalocker.LOCK_EX | portalocker.LOCK_NB)
            return lockfile
        except portalocker.exceptions.LockException:
            return None

    @classmethod
    def safe_delete(cls, path):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass  # Already deleted, no worries
        except PermissionError:
            logging.warning(f"Couldn't delete {path}: Permission denied")
        except Exception as e:
            logging.warning(f"Failed to delete {path}: {e}")
