# Azure Cognitive Search Vector Store for Autograding

This guide walks through setting up **Azure Cognitive Search** as a vector store for an autograding system. You'll learn how to provision the service, define a vector index, embed student submissions with Cohere’s multimodal model, index documents, execute vector queries, and tune the system for performance and accuracy.

---

## 🧭 Overview

- 🔍 **Purpose**: Compare student submissions (text/images) against grading rubrics using semantic similarity
- ☁️ **Platform**: Azure Cognitive Search (vector indexing with HNSW)
- 🤖 **Embedding Model**: [Cohere’s Multimodal Embed v4.0](https://docs.cohere.com/docs/multimodal-embed)
- 📁 **Supports**: Text, images, or both (e.g. screenshots + answers)
- ⚠️ **Embedding Limitation**: Each modality must be separated before vectorization (images cannot be vectorized alongside text)
- 🔑 **Index Fields**: Index schema should include a unique key (e.g. submissionId) and one or more 1024‑dimensional vector fields (e.g. textVector, imageVector)​
. We often store text and image chunks separately.


 **Key Idea:**
When a course material or submission is uploaded, we convert it into a Document (via bytes_to_doc_util.Document.from_pdf() for PDFs) that yields a sequence of DocumentChunk objects (each either text or image). We upload these chunks (as blobs) and embed them. For search, we embed the rubric or query text, then do a vector search in the index to find the most similar chunks.

## 🚀 1. Provision Azure Services

### Azure Cognitive Search
1. Go to the [Azure Portal](https://portal.azure.com/)
2. Search for **Azure Cognitive Search** → Create a new service
3. Choose:
   - A unique **name**
   - Region and **pricing tier** (Basic or above)
4. After deployment, get the Endpoint URL and Admin Key for the service.

**CLI Option:**
```bash
az search service create -n <your-service-name> -g <your-resource-group> -l <region> --sku Basic
```
>Note: In our code, we actually use a VectorDBService interface to abstract the vector store. The default is a Chroma DB (vector_db_service.py), but you could swap in Azure Cognitive Search by implementing the same interface.

### Azure Blob Storage
Create an Azure Storage account and container to store files and chunk data. Obtain credentials or use a managed identity.

### Azure Open AI
 If using Azure OpenAI for final grading or QA, set up a deployment (e.g. GPT-4o) and get its endpoint and key.

### Cohere API Key
Sign up with Cohere and get an API key for the embed-v4.0 model, or use the Azure AI Embeddings service with a Cohere model endpoint.

*(The code uses a singleton pattern; e.g. AzureEmbeddingService.init_singleton(endpoint, key, model) and AzureBlobService.init_singleton(...) are called at startup to configure these services.)*


---

## 📦 2. Create Index with Vector Fields

To support vector search, we reccomend that your index schema includes:

- A unique **key field** (`submissionId`)
- A **vector field** (`submissionVector`) of type `Collection(Edm.Single)`
- Optional: `filePath`, `submissionText`, or other metadata
- Ensure the `vectorSearchProfile` is set up with HNSW (or your chosen ANN) for cosine similarity. Example profile:
**HNSW Configuration** (for Approximate k-NN):
```json
{
  "vectorSearch": {
    "profiles": [
      {
        "name": "vec-profile",
        "algorithm": "hnsw",
        "metric": "cosine"
      }
    ]
  }
}
```
And Vector field configuration:
```json
{
  "name": "submissionVector",
  "type": "Collection(Edm.Single)",
  "searchable": true,
  "dimensions": 1024,
  "vectorSearchProfile": "vec-profile"
}
```
- **Modality Fields**: If storing text and image embeddings separately, you could add two vector fields (e.g. textVector and imageVector) and filter queries accordingly. Each modality chunk is indexed under the appropriate field. (Alternatively, we store modality as metadata and always use the submissionVector field but only one embedding per doc.)
>**Dimensionality**: Always match the dimension of your embeddings (1024 for Cohere v4.0)​. Getting the dimensions wrong will break the index.

**Vector Field Example:**
```json
{
  "name": "submissionVector",
  "type": "Collection(Edm.Single)",
  "searchable": true,
  "dimensions": 1024, #since Cohere uses 1024 size embedding, but read into which specific dimension size you would need
  "vectorSearchProfile": "vec-profile"
}
```
---

## 🧠 3. Embed Student Submissions (Text, Images)

### 🤖 Embedding Model: Cohere Multimodal (`embed-v4.0`)
**Batch vs Single**: Cohere allows batching of text inputs (up to 96 per request in our code). Images, however, must be sent one per call (they can’t be batched). The embedding dimension is 1024 for both​.
**Supports**:
- `input_type="search_document"`
- `output_dimension=1024` (adjust as needed)
- Text (plain strings)
- Image (as base64 Data URL)
#### Parsing Files into Chunks
For PDFs or mixed content, we use `Document.from_pdf()` from bytes_to_doc_util.py. This method:
- Takes a PDF’s bytes (or file content) and processes pages in order.
- Extracts text blocks and images. It chunks text when it reaches a word count threshold or an image boundary.
- Returns a Document object containing DocumentChunk items, each with a data_type (TEXT or image type) and the raw content bytes
---
Example: Suppose file_bytes holds a PDF. We do:
```python
from app.utils.bytes_to_doc_util import Document
doc = Document.from_pdf("submission.pdf", file_bytes, do_splits=True, split_len=500, overlap=50)
```
`doc.contents` is then a dict mapping chunk IDs → DocumentChunk. Each chunk is either:
- TEXT: chunk.content is UTF-8 text, chunk.get_as_string() yields the string.
- IMAGE: chunk.content is raw image bytes, chunk.get_as_base64() yields a Base64 string.

### ⚙️ Embedding Workflow

1. **Parse submission**: If PDF or doc, run `Document.from_pdf()` (or `Document.from_png()` for images). This produces mixed chunks.
2. **Store chunks**: Optionally upload chunks to Blob Storage (see next section) to persist and tag them.
3. **Embed each chunk:**
- For a text chunk: Call Cohere’s embed with input_type="search_document". In code, we use CohereEmbeddingService.embed_texts(...) for batching.
- For an image chunk: Encode bytes as base64 and call CohereEmbeddingService.embed_image(mime_type, base64_data) for a 1024-dim vector.
4. **Collect vectors:** Build a list of (chunk_path, vector) pairs.
Example embedding code using our services:
```python
from app.services.azure_embedding_service import CohereEmbeddingService, EmbeddingInputType

co = CohereEmbeddingService.get_instance()
text_vectors, image_vectors = {}, {}
texts_to_batch, batch_ids = [], []

for chunk_id, chunk in document.contents.items():
    if chunk.data_type == DataType.TEXT:
        texts_to_batch.append(chunk.get_as_string())
        batch_ids.append(chunk_id)
    elif chunk.data_type.is_image():
        vec = co.embed_image(chunk.data_type.mime_type, chunk.get_as_base64())
        image_vectors[chunk_id] = vec

# Batch-embed all text chunks together for efficiency
text_embs = co.embed_texts(texts_to_batch, EmbeddingInputType.DOCUMENT)
for cid, vec in zip(batch_ids, text_embs):
    text_vectors[cid] = vec
```
Each vec is a 1024‑length list of floats. (Our code in CohereEmbeddingService does batching internally​.)
**Tip:** Cohere embeddings may have a limit per request; the code splits text into batches of size 96 (or less) to avoid timeouts​. We purposely do single-image calls because the API requires that.
---

### ⚠️ Note on Mixed Media Inputs

To handle documents that contain **both images and text** (e.g. scanned handwritten answers + typed explanation), you must:

> 🛠️ **Build a custom parsing pipeline**:
> - Use OCR to extract text (e.g. `tesseract`, `PyMuPDF`)
> - Detect and isolate images
> - Generate **separate embeddings** for each modality:
>   - Text → vector via Cohere Embed (text input)
>   - Image → vector via Cohere Embed (image input)

---

## 🗂️ 4. Upload Documents to Azure Index
Once chunks are parsed and embedded, we save them and index the vectors.
### 1. Save Raw Chunks (Azure Blob Storage)
Use azure_blob_service.py to upload chunks to a structured path. For example, background processing code calls:
```python
from app.services.azure_blob_service import AzureBlobService
blob_service = AzureBlobService.get_instance()
# Suppose semester="2024S", course="CS101", material_id="lecture1"
chunk_paths = blob_service.upload_material_chunks(
    semester, course, material_id, document
)
```
Internally, upload_material_chunks deletes any existing /chunks folder and then uploads each chunk:
- It iterates over document.contents.items().
For each chunk_id, it creates a blob path like: `course/{semester}/{course}/course_material/{material_id}/chunks/{chunk_id}.{ext}`
where ext is txt, png, etc. from chunk.data_type​.
- It calls upload_binary_data(chunk.content, blob_path) to store it.
- Returns a dict mapping chunk_id -> blob_path.
These blob paths can be used later to retrieve content or share via SAS URLs. You can also store **metadata** (e.g. page number) on each blob. And generate_sas_url(blob_path) can produce a read-only URL if you want to serve the content.

### 2. Index Vectors in Search
We then push the embeddings to the vector index. Depending on your setup:
- **Azure Cognitive Search (Vector Index)**: Construct a document with fields matching the index, e.g.:
python```
doc = {
    "submissionId": f"{semester}-{course}-{material_id}-chunk{chunk_id}",
    "filePath": blob_path,
    "modality": document.get_chunk(chunk_id).data_type.name.lower(),
    "submissionVector": vector.tolist()  # 1024-d floats
}```
search_client.upload_documents(documents=[doc])
Alternatively, use merge_or_upload_documents if you want updates. This corresponds to the JSON example from before​.
- **Vector DB Service (e.g. Chroma):** We use vector_db_service.py’s add_vectors. In background code, after getting vectorized_chunks as {blob_path: vector}, we do:

```python
vector_service = ChromaDBService.get_instance()
ids = list(vectorized_chunks.keys())
vs = list(vectorized_chunks.values())
vector_service.add_vectors(semester, course, ids, vs)
```

Each vector entry in Chroma (or Azure Search) is now stored with ids[i] as the identifier. In the Chroma example, we also store metadata semester and course_id internally.

In both cases, each chunk’s embedding becomes searchable. (We often use the blob path or similar unique string as the ID.)

Similarly, for student submissions, you would parse their answer, embed chunks, and either search or index as needed. Often we query the index with the student’s embedding, rather than upload it.
---

## 🔍 5. Query the Index (Grading Rubric)

1. **Embed the Rubric/Question: Use Cohere to get a query vector (text query, or image description). E.g.:**
```python
from app.services.azure_embedding_service import CohereEmbeddingService, EmbeddingInputType
co = CohereEmbeddingService.get_instance()
query_text = "Explain dynamic vs static typing"
resp = co.embed_texts([query_text], EmbeddingInputType.SEARCH_QUERY)
query_vector = resp[0]
```

2. **Search the Vector Index:** Use either Azure Search or the vector DB:
- Azure Search: Construct a VectorizedQuery and call search_client.search. For example:
```python
from azure.search.documents.models import VectorizedQuery
vector_query = VectorizedQuery(
    vector=query_vector,
    k_nearest_neighbors=5,
    fields="submissionVector"
)
results = search_client.search(vector_queries=[vector_query])
for doc in results:
    print(doc["submissionId"], doc["@search.score"])
```
- Chroma (VectorDBService): Call vector_service.search(semester, course, [query_vector], top_k=5). This returns lists of IDs (e.g. blob paths) for nearest neighbors. Example:
```python
top_ids_list = vector_service.search(semester, course, [query_vector], top_k=5)
top_ids = top_ids_list[0]  # since we passed one query vector
for vid in top_ids:
    print("Match:", vid)
```
These IDs correspond to the chunk IDs or blob paths we added earlier.
3. **Use Results:** The returned documents or chunk IDs are the top‐k semantically similar chunks. You can retrieve the original text or image from blob storage (or from metadata) to present in grading or to feed to an LLM for final scoring.

>Example: If the rubric expects an explanation of typing, the student’s answer text is embedded and queried. The system returns stored chunks (from lecture notes or examples) that are semantically closest. These can help in evaluating the answer or providing feedback.
---


## 📏 6. Tuning and Optimization

| Parameter            | Purpose                                 | Recommendation             |
|----------------------|------------------------------------------|-----------------------------|
| `dimensions`         | Vector size                             | Match with model (e.g. 1024) |
| `efSearch`           | Search accuracy vs speed                | 500–1000 for best accuracy |
| `m`                  | Graph connectivity                      | 4 (default) or increase for recall |
| `quantization`       | Compress storage                        | Use scalar quantization (default) |
| `top_k`              | Top results returned                    | 5–10                        |
| `replicas`, `partitions` | Scale for performance             | Add based on latency or size |
If using Chroma or another vector store, tuning is simpler: you mainly choose how many nearest neighbors (top_k) and can periodically retrain or rebuild indexes. Chroma’s default HNSW settings usually suffice for many applications. Remember to store and query modalities separately if needed. For example, you might filter a query to only search text embeddings against text, and image against image, unless you have a fusion strategy.
---
## 🔧 Integration with Codebase

The codebase has several key components, each fulfilling a role in the vector search pipeline:

### `bytes_to_doc_util.py`
Defines `Document` and `DocumentChunk`. This parsing utility reads files (PDF, image, etc.) and splits them into ordered chunks. For PDFs, `Document.from_pdf(file_name, file_bytes)` extracts text blocks and images, chunking text by word count or page breaks. Each `DocumentChunk` has a `data_type` (e.g., TEXT, PNG) and raw content. This structuring underpins the entire pipeline.

### `azure_blob_service.py`
Manages Azure Blob Storage interactions. Key functions include:
- `upload_material_chunks(semester, course_id, material_id, document)`: Saves each `DocumentChunk` to a blob path like `course/{semester}/{course}/course_material/{material_id}/chunks/{chunkId}.{ext}`. Returns a dict mapping chunk IDs to blob paths.
- `get_file_bytes(blob_path)`, `download_file()`: Read blobs back into memory.
- `generate_sas_url(blob_path)`: Creates a time-limited URL for reading a blob.

This service is central to storing and retrieving course materials and student submissions.

### `azure_embedding_service.py` and `CohereEmbeddingService`
Handles embedding logic for both text and image chunks:
- `embed_texts(list_of_strings, purpose)`: Batches text inputs into single API calls (up to 96 per batch).
- `embed_image(mime_type, base64_data)`: Embeds a single image (encoded in base64).

Both return 1024-dimensional float vectors from Cohere’s `embed-v4.0`. The system initializes a singleton via `CohereEmbeddingService.init_singleton()` and uses `get_instance()` in downstream tasks.

### `bg_material_processor.py`
This background worker ties everything together:
- `process_course_material(json_str)`:
  - Parses metadata into a `CourseMaterialData` object.
  - Downloads file bytes and converts them to a `Document`.
  - Saves chunks using `AzureBlobService.upload_material_chunks`.
  - Embeds each chunk (text in batch, image one-by-one).
  - Stores vectors via `vector_db_service.add_vectors`.

- `process_grading(json_str)`:
  - Parses student submission into chunks.
  - Retrieves rubric.
  - Finds relevant course material using vector search.
  - Builds a multimodal grading prompt.
  - Calls `LLMService.generate_structured_response` for autograding.
  - Stores result via `upload_student_grade()`.

This enables a complete RAG (Retrieval-Augmented Generation) workflow for autograding.

### `vector_db_service.py`
Abstracts the vector storage layer:
- Defines `VectorDBService` interface with methods like `add_vectors`, `search`, and `delete_*`.
- Implements `ChromaDBService` using a persistent Chroma client. It creates collections (e.g., `"ml-bu-autograder"`), supports metadata filtering, and stores vectors by ID.

Although currently based on Chroma, this module is pluggable—developers can implement the same interface for Azure Cognitive Search.

### `llm_service.py`
Manages Azure OpenAI for grading tasks:
- `generate_structured_response()`: Sends chat prompts to a deployed Azure OpenAI model and parses structured JSON outputs (e.g., `Grade` schema).
- `PromptBuilder`: Helps construct message prompts that include system, user, and image/text parts.

This is invoked after retrieving relevant materials to assemble a grading context that the model can evaluate.

---

Each of these components fits into a modular and scalable grading pipeline where content is parsed, embedded, indexed, retrieved, and evaluated—end-to-end.
## 📚 References

- [Azure Cognitive Search Vector Search](https://learn.microsoft.com/en-us/azure/search/vector-search-overview)
- [Azure Python SDK Docs](https://learn.microsoft.com/en-us/python/api/overview/azure/search-documents-readme)
- [Cohere Embed Multimodal Docs](https://docs.cohere.com/docs/multimodal-embed)
- [How to Index Documents in Azure Search](https://learn.microsoft.com/en-us/azure/search/search-import-data)