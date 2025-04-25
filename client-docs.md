TODO: rn there are only 5 bullets but they can probably be split further

1. (Josh) Technical recommendations for optimal tools for MET's use case. The implications of this as I understanding is you are looking for something that is primary within the Azure ecosystem and if outside the Azure ecosystem, it should be something that should be integrable easily.
- tell them about Azure's offerings for pdf extract, ocr, etc
- more stuff
- cohere and how that can be integrated?

2. (Fahim) Recommendations for the optimal model (or combination of) in that tool for MET's use case.
- Maybe tell them they can use a mixture and best model depends on use case.
- use gpt 4.1 nano for content thats directly written in the course material (no reasoning needed) - pure summarization.
- gpt 4.1 mini for most general purpose tasks.
- gpt 4.1 for anything involving formal reasoning BUT the problem is widely known/well understood.
- for more complex formal math tasks a reasoning model (gemini 2.5 pro) is needed. expensive.

3. (Zach) Recommendations on optimal configurations for that model (temperature, etc) and as well as how to specify these configs.

## Optimal Strategy for Course Material Storage on Azure

When structuring your storage hierarchy in Azure Blob Storage, it's critical to understand performance implications:

- **Direct Blob Access**: Retrieving a blob by its exact path is an **O(1)** operation (extremely fast).
- **Prefix Searches**: Searching blobs by prefix takes **O(n)** time, proportional to the number of blobs under that prefix.

Generally, performance doesn't become a bottleneck until you are scaling to at least a dozen courses so we will
avoid going into too many details here.

### Metadata for Efficient Indexing and Search

When creating AI Search indexes that span multiple courses:

- Include metadata such as `course_id` and `semester`.
- Ensure metadata fields intended for filtering (e.g., `course_id`) are marked as **filterable** in your Azure AI Search index schema.

This approach allows efficient querying and vector searches with precise filtering (example):

```json
{
  "name": "course_materials",
  "fields": [
    {"name": "semester", "type": "Edm.String", "filterable": true},
    {"name": "course_id", "type": "Edm.String", "filterable": true}
  ]
}
```

---

### Integrating Custom Document Processing with Azure

While Azure provides native support for extracting text from documents, interpreting embedded images or diagrams typically requires custom processing, especially when leveraging advanced multimodal LLMs.

#### Why Focus on PDFs?

Given the universality and ease of converting various document formats (Word, Excel, PowerPoint) into PDF, centralizing document processing around PDFs streamlines the pipeline significantly.

### Automated Indexing via Azure Serverless Functions

To enable real-time indexing of course materials into Azure AI Search, leverage **Azure Functions** to process files as they arrive in **Blob Storage**.
You can do this by writing a custom function similar to the one we wrong in [bytes_to_doc_util.py](app/utils/bytes_to_doc_util.py) called *to_pdf*.
Here is how this custom document processing pipeline might look like:

#### 📥 End-to-End Pipeline Overview

1. **Instructor uploads a document (e.g. PDF) to Blob Storage**.
2. **Azure Function** is triggered by the upload event.
3. The Function:
    - Loads the document bytes.
    - Calls your `from_pdf`-like logic (adapted to return search-index-ready JSON).
    - Stores the extracted chunks as a `.jsonl` file back in Blob Storage.
4. A second Function (or the same one) pushes this `.jsonl` content into Azure AI Search using Azure's Python SDK.

#### ⚙️ Setting up the Azure Function

#### 1. Trigger Function on Blob Upload
*Disclaimer: This is intended to be more of a high level overview of how such a function might work. This code was AI generated and was not tested*
```python
import azure.functions as func
from azure.storage.blob import BlobServiceClient

# Initialize blob service client
blob_service_client = BlobServiceClient.from_connection_string("<your-connection-string>")

@func.function_name(name="BlobPDFIndexer")
@func.blob_trigger("uploads/{name}", connection="AzureWebJobsStorage")
def main(blob: func.InputStream, name: str):
    file_bytes = blob.read()
    chunks = from_pdf("input.pdf", file_bytes).to_index_format()  # ← Adapt this method

    # Write JSONL to Blob
    out_blob = blob_service_client.get_blob_client("processed", f"{name}.jsonl")
    jsonl_data = "\n".join([json.dumps(chunk) for chunk in chunks])
    out_blob.upload_blob(jsonl_data, overwrite=True)

    # Upload to AI Search (optional step)
    upload_to_ai_search(chunks)  # define this using SearchClient in Azure's "azure.search.documents" SDK package
```

#### 2. Adapting `from_pdf` for Indexing
You’ll want to modify your `from_pdf` method to return data in a flattened, AI Search-compatible structure. Prompt a local LLM with:

> "Rewrite this function so it returns a list of dictionaries, each dictionary representing a document chunk with fields like `id`, `content`, `page_num`, and `course_id`, all serializable as JSON for Azure AI Search."

This will likely take some trial and error to completely get working.

---

## Example Output Format

Each chunk should be a JSON document that might look like:

```json
{
  "id": "CS101-intro-0",
  "course_id": "CS101",
  "module_id": "week1",
  "material_type": "lecture_notes",
  "page_num": [1,2],
  "content": "This is some long chunk of the text",
  "source_file": "introduction.pdf"
}
```

In the case of images, the "content" would include the binary data of the image encoded in base64. "Default" text embeddings like the ada text
embedding **does not** support this kind of content. Instead, you must use a multi-modal embedding like "Cohere-embed-v3-english".

---

## Configuring AI Search with Multimodal Embeddings

To enable powerful vector search over both text and image chunks, configure your Azure AI Search instance to use **Cohere embeddings**, which are currently the only **multimodal embedding model** supported in Azure.

- Cohere supports text and image embedding in a shared vector space.
- This enables unified retrieval across textual and visual components of a document.

> 📌 Azure has announced support for **OpenAI CLIP**, a state-of-the-art multimodal embedding model, but it is not yet generally available. Until then, Cohere offers excellent performance for academic and visual-rich document retrieval.

Ensure your index schema includes a `vector` field configured to accept external vector values:

```json
{
  "name": "content_vector",
  "type": "Collection(Edm.Single)",
  "dimensions": 1024,
  "vectorSearch": {
    "algorithm": "hnsw"
  }
}
```

Then, either precompute the embeddings using Cohere’s API or let Azure handle embedding via the built-in connection if you configure it accordingly in Azure AI Studio.

## What About Student Submissions?

The document so far has primarily focused on course materials. However, a similar pipeline can be applied to **student submissions**. In this case, instead of using serverless Azure Functions, you can integrate document processing directly into a **Prompt Flow pipeline**.
Student submissions would be uploaded to Azure Blob Storage, and a custom Python script component in Prompt Flow would process the submission. This script would extract relevant text or image content from the submission, generate embeddings, call AI search, and pass the 
multi-modal retrieved content to the LLM. See how to handle images in prompt flow on [Azure's documentations](https://learn.microsoft.com/en-us/azure/machine-learning/prompt-flow/how-to-process-image?view=azureml-api-2#image-type-in-prompt-flow).

## Bypassing the Complexity with Middleware or External APIs

Setting up these pipelines in Azure can be complex and often requires dealing with event triggers, custom parsing logic, and search indexing configuration. To simplify deployment and reduce infrastructure dependencies, you may instead choose to offload processing to external services via middleware.
In our original solution, we created such a middleware service to abstract away this complexity. While our implementation avoided Azure Functions due to technical constraints, the principle remains the same.
If you're using **external LLM APIs** (e.g., OpenAI, Gemini, etc.), many of them can directly accept files or support advanced document processing features without requiring you to manually extract or chunk content. **Gemini**, in particular, offers relatively low-cost multimodal capabilities and supports direct file input.
However, there is a trade-off: when using external models, especially for grading student submissions that reference course materials, the system must send the **entire relevant course material** along with the student submission. For large files, this can lead to high token usage and significant cost.
This makes such solutions best suited for smaller documents or where document relevance can be pre-filtered and trimmed.



5. (Zach) Prompt engineering methods and techniques applicable to your use case.
- idk