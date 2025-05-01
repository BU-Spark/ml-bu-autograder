import asyncio
import logging
import os
import random
from typing import Optional, TextIO, Callable, Dict, List, Tuple

import portalocker
import requests
from azure.ai.inference.models import EmbeddingInputType
from pydantic import FilePath

from app.models import CourseMaterialData, Grade, GradedStudentResponseReference
from app.services import AzureBlobService, AzureEmbeddingService, AzureVectorService
from app.utils.bytes_to_doc_util import Document, DataType, ChunkData
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
VECTOR_SEARCH_TOP_K = 5 # Number of top K results to return from the vector search
def process_grading(json_str: str):
    """
    Processes student grading for a specific student response.
    """
    logging.info("Starting process_grading...")
    #  Step 0: Convert the json string into a student response object and download raw binary content of response
    student_response = GradedStudentResponseReference.model_validate_json(json_str)
    logging.info(f"Processing grading for student {student_response.student_id}, assignment {student_response.assignment_id}, q {student_response.question_index}")
    try:
        response = requests.get(student_response.data.uri)
        response.raise_for_status() # Check for HTTP errors
        binary_content = response.content
        logging.info(f"Downloaded {len(binary_content)} bytes for student response.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download student response from {student_response.data.uri}: {e}", exc_info=True)
        # Decide how to handle: raise error, return, skip grading?
        raise Exception(f"Failed to download student response: {e}") from e

    #  Step 1: Convert the student's response into a Document object.
    try:
        covert_to_doc = student_response.data.data_type.get_to_doc_func()
        student_response_documents: Document = covert_to_doc(
            f"student_response.{student_response.data.data_type.extension}",
            binary_content,
            False # Don't chunk student response initially
        )
        logging.info("Converted student response to Document object.")
    except Exception as e:
        logging.error(f"Failed to convert student response to Document: {e}", exc_info=True)
        raise Exception(f"Failed to process student response format: {e}") from e

    #  Step 2: Grab the rubric and assignment instructions.
    blob_service = AzureBlobService.get_instance()
    try:
        rubric = blob_service.get_rubric(
            student_response.semester, student_response.course_id,
            student_response.assignment_id, False
        )
        # Assuming rubric object is mutable or handle appropriately
        rubric.sub_rubrics = [blob_service.get_sub_rubric(
            student_response.semester, student_response.course_id,
            student_response.assignment_id, student_response.question_index
        )]
        assignment = blob_service.get_assignment_metadata(
            semester_key=student_response.semester,
            course_id=student_response.course_id,
            assignment_id=student_response.assignment_id,
        )
        # Check if question_index is valid
        if student_response.question_index >= len(assignment.questions):
             raise IndexError(f"Invalid question_index {student_response.question_index} for assignment {student_response.assignment_id}")
        assignment_question = assignment.questions[student_response.question_index]
        logging.info("Retrieved rubric and assignment details.")
    except Exception as e:
        logging.error(f"Failed to retrieve grading context (rubric/assignment): {e}", exc_info=True)
        raise Exception(f"Failed to retrieve grading context: {e}") from e

    #  Step 3: Query the vector database with the student's response.
    #  --- TODO IMPLEMENTED ---
    relevant_document_paths: List[str] = []
    try:
        logging.info("Starting vector search for relevant documents...")
        vector_service = AzureVectorService.get_instance()
        embedding_service = AzureEmbeddingService.get_instance()

        # Create query text from student response
        student_text_content = ""
        if hasattr(student_response_documents, 'contents'):
             student_text_content = " ".join(
                 chunk.get_as_string() for chunk in student_response_documents.contents.values() if chunk.data_type.is_text()
             )

        if not student_text_content.strip():
            logging.warning("Student response contains no text content to query vector DB. Skipping RAG.")
        else:
            # Generate query vector
            query_vector_list = embedding_service.embed_texts([student_text_content], EmbeddingInputType.TEXT)

            if not query_vector_list:
                logging.error("Failed to generate query vector for student response.")
                # Decide how to proceed: grade without RAG, or fail?
            else:
                query_vector = query_vector_list[0] # embed_texts returns a list of vectors

                # Search the vector index
                search_results_batch = vector_service.search_vectors([query_vector], top_k=VECTOR_SEARCH_TOP_K)

                if search_results_batch and search_results_batch[0]:
                    search_results = search_results_batch[0] # Results for the first (only) query vector
                    # Extract the 'file_path' which we assume holds the blob path/ID
                    # Filter out results without a file_path
                    relevant_document_paths = [
                        result['file_path'] for result in search_results if result.get('file_path')
                    ]
                    logging.info(f"Vector search completed. Found {len(relevant_document_paths)} relevant document paths (top {VECTOR_SEARCH_TOP_K}).")
                else:
                    logging.warning("Vector search returned no results for the student response.")

    except Exception as e:
        logging.error(f"Error during vector search: {e}", exc_info=True)
        # Decide whether to continue without RAG documents or raise an error
        logging.warning("Proceeding with grading without RAG documents due to search error.")
    #  --- END TODO IMPLEMENTATION ---

    #  Step 4: Fetch RAG documents from blob storage.
    course_material_documents: List[Tuple[str, ChunkData]] = []
    if relevant_document_paths:
        try:
            course_material_documents = blob_service.get_chunks_from_blob_path(relevant_document_paths)
            logging.info(f"Retrieved {len(course_material_documents)} relevant course material chunks from blob storage.")
        except Exception as e:
            logging.error(f"Failed to retrieve RAG documents from blob storage: {e}", exc_info=True)
            # Continue without RAG documents
            course_material_documents = []
    else:
        logging.info("No relevant document paths found or vector search skipped; proceeding without RAG documents.")


    #  Step 5: Build the prompt for the LLM.
    logging.info("Building prompt for LLM...")
    prompt = (PromptBuilder.builder()
              .add_message(PromptRole.SYSTEM, "You are a grader responsible for grading a student's response.")
              .add_message(PromptRole.USER, "Here is course material that might be relevant to this assignment."
                                            "In your grading responses, when information is relevant, please cite these"
                                            "sources including with any other relevant reference information."))

    if course_material_documents:
         for file_name, document_chunk in course_material_documents:
             if not isinstance(document_chunk, ChunkData): # Basic type check
                 logging.warning(f"Expected ChunkData from get_chunks_from_blob_path, got {type(document_chunk)}. Skipping.")
                 continue
             if not document_chunk.data_type.is_fundamental(): # Ensure it's text or image
                 logging.warning(f"RAG document chunk {file_name} has non-fundamental type {document_chunk.data_type}. Skipping.")
                 continue

             doc_ref_str = f"Document name: {file_name}"
             if 'page_num' in document_chunk.metadata:
                 doc_ref_str += f" (page {document_chunk.metadata['page_num']})"
             prompt.add_message(PromptRole.USER, doc_ref_str)

             if document_chunk.data_type.is_image():
                 prompt.add_image_bytes(PromptRole.USER, document_chunk.content, document_chunk.data_type.mime_type)
             elif document_chunk.data_type.is_text():
                 prompt.add_message(PromptRole.USER, document_chunk.get_as_string())
    else:
         prompt.add_message(PromptRole.USER, "[No relevant course material provided for context.]")


    # Add assignment/rubric context
    (prompt.add_message(PromptRole.USER, "The instructions for this assignment question are as follows:")
     #.add_json_input(PromptRole.USER, assignment, excluded_fields={"questions"}) # Might be too verbose?
     .add_json_input(PromptRole.USER, assignment_question) # Add specific question
     .add_message(PromptRole.USER, "Grading for this assignment should be"
                                   " exclusively based on the following rubric:")
     .add_json_input(PromptRole.USER, rubric)) # Add the rubric (with sub-rubric included)

    if hasattr(rubric, 'grading_flags') and rubric.grading_flags:
        for grading_flag in rubric.grading_flags:
            if hasattr(grading_flag, 'flag_name') and hasattr(grading_flag, 'get_description'):
                prompt.add_message(PromptRole.USER, f"Note the rubric flag '{grading_flag.flag_name}': {grading_flag.get_description()}")

    # Add student response
    prompt.add_message(PromptRole.USER, "Here is the student's response to be graded:")
    if hasattr(student_response_documents, 'contents'):
        if not student_response_documents.contents:
             prompt.add_message(PromptRole.USER, "[Student response appears to be empty or could not be processed.]")
        for chunk_id, resp_chunk in student_response_documents.contents.items():
            if resp_chunk.data_type.is_image():
                prompt.add_image_bytes(PromptRole.USER, resp_chunk.content, resp_chunk.data_type.mime_type)
            elif resp_chunk.data_type.is_text():
                prompt.add_message(PromptRole.USER, resp_chunk.get_as_string())
    else:
        prompt.add_message(PromptRole.USER, "[Student response content not available.]")

    logging.info("Prompt built successfully.")

    #  Step 6: Generate grade and upload.
    try:
        logging.info("Sending request to LLM for grading...")
        llm = LLMService.get_instance()
        prompt_data_for_llm = prompt.build()
        student_grade = llm.generate_structured_response(
            prompt_data_for_llm,
            Grade # Expect a Grade object back
        )
        logging.info(f"Received structured grade from LLM: Score={getattr(student_grade, 'score', 'N/A')}")

        blob_service.upload_student_grade(
            semester_key=student_response.semester,
            course_id=student_response.course_id,
            assignment_id=student_response.assignment_id,
            question_index=student_response.question_index,
            student_id=student_response.student_id,
            grade=student_grade
        )
        logging.info("Uploaded student grade to blob storage.")
    except Exception as e:
        logging.error(f"Error during LLM grading or grade upload: {e}", exc_info=True)
        # Decide how to handle: maybe store error state?
        raise Exception(f"LLM grading or upload failed: {e}") from e

    logging.info("Finished process_grading successfully.")


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
        course_material.data.content,
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
    embedding_service = AzureEmbeddingService.get_instance()
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
                chunked_doc.data_type.mime_type, chunked_doc.get_as_bytes()
            )
        elif chunked_doc.data_type == DataType.TEXT:
            text_paths.append(chunk_path)
            texts.append(chunked_doc.get_as_string())
        else:
            # the data types should only be either image or text
            raise Exception(f"Unsupported data type: {course_material.data.data_type}")
    vectors = embedding_service.embed_texts(texts, EmbeddingInputType.TEXT)
    for blob_path, vector in zip(text_paths, vectors):
        vectorized_chunks[blob_path] = vector
    #  Step 5: Upload the vectorized chunks to the vector database
    vector_service = AzureVectorService.get_instance()  
    vector_service.add_vectors(ids=uploaded_chunks.keys, vectors=uploaded_chunks.values(), metadata=texts)
    #  Step 5: Take the pairs of the blob paths and vectorized chunks, and upload them
    #          to Azure's AI search. And thats it!
    # TODO: josh you do this



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
