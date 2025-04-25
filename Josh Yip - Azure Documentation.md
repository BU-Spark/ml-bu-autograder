# Azure Cognitive Search Vector Store for Autograding

This guide walks through setting up **Azure Cognitive Search** as a vector store for an autograding system. You'll learn how to provision the service, define a vector index, embed student submissions with Cohere’s multimodal model, index documents, execute vector queries, and tune the system for performance and accuracy.

---

## 🧭 Overview

- 🔍 **Purpose**: Compare student submissions (text/images) against grading rubrics using semantic similarity
- ☁️ **Platform**: Azure Cognitive Search (vector indexing with HNSW)
- 🤖 **Embedding Model**: [Cohere’s Multimodal Embed v4.0](https://docs.cohere.com/docs/multimodal-embed)
- 📁 **Supports**: Text, images, or both (e.g. screenshots + answers)
- ⚠️ **Embedding Limitation**: Each modality must be separated before vectorization

---

## 🚀 1. Provision Azure Cognitive Search

1. Go to the [Azure Portal](https://portal.azure.com/)
2. Search for **Azure Cognitive Search** → Create a new service
3. Choose:
   - A unique **name**
   - Region and **pricing tier** (Basic or above)
4. Once deployed, go to **Keys** → Copy **Admin Key** and **Endpoint**

**CLI Option:**
```bash
az search service create -n <your-service-name> -g <your-resource-group> -l <region> --sku Basic
```

---

## 📦 2. Create Index with Vector Fields

To support vector search, we reccomend that your index schema includes:

- A unique **key field** (`submissionId`)
- A **vector field** (`submissionVector`) of type `Collection(Edm.Single)`
- Optional: `filePath`, `submissionText`, or other metadata

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

**Vector Field Example:**
```json
{
  "name": "submissionVector",
  "type": "Collection(Edm.Single)",
  "searchable": true,
  "dimensions": 1024, #since Cohere uses 1024 size embedding
  "vectorSearchProfile": "vec-profile"
}
```


---

## 🧠 3. Embed Student Submissions (Text, Images)

### 🤖 Embedding Model: Cohere Multimodal (`embed-v4.0`)

**Supports**:
- `input_type="search_document"`
- `output_dimension=1024` (adjust as needed)
- Text (plain strings)
- Image (as base64 Data URL)

---

### ⚙️ Embedding Workflow

1. **Text**: Convert PDFs/code into plain text
2. **Image**: Convert image to base64
3. Call Cohere Embed API for each

**Python (Image to base64):**
```python
from PIL import Image
from io import BytesIO
import base64

def image_to_data_url(path):
    with Image.open(path) as img:
        buf = BytesIO()
        img.save(buf, format=img.format)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/{img.format.lower()};base64,{encoded}"
```

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

Each submission should be formatted like:
```json
{
  "submissionId": "student123",
  "filePath": "subs/student123.pdf",
  "submissionText": "def f(x): return x*2",
  "submissionVector": [0.12, -0.04, 0.56, ...]
}
```

**Upload:**
```python
search_client.upload_documents(documents=[your_doc])
```

**Update / Merge:**
```python
search_client.merge_or_upload_documents(documents=[updated_doc])
```

**Delete:**
```python
search_client.delete_documents(documents=[{"submissionId": "student123"}])
```

---

## 🔍 5. Query the Index (Grading Rubric)

1. **Embed rubric or correct answer**
```python
resp = co.embed(
  model="embed-v4.0",
  texts=["explain dynamic vs static typing"],
  input_type="search_document",
  output_dimension=1024
)
query_vector = resp.embeddings[0]
```

2. **Vector search against index**
```python
from azure.search.documents.models import VectorizedQuery

vector_query = VectorizedQuery(
  vector=query_vector,
  k_nearest_neighbors=5,
  fields="submissionVector"
)
results = search_client.search(vector_queries=[vector_query])
```

3. **Read top-k matches**
```python
for doc in results:
    print(doc["submissionId"], doc["@search.score"])
```

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

---

## 📚 References

- [Azure Cognitive Search Vector Search](https://learn.microsoft.com/en-us/azure/search/vector-search-overview)
- [Azure Python SDK Docs](https://learn.microsoft.com/en-us/python/api/overview/azure/search-documents-readme)
- [Cohere Embed Multimodal Docs](https://docs.cohere.com/docs/multimodal-embed)
- [How to Index Documents in Azure Search](https://learn.microsoft.com/en-us/azure/search/search-import-data)