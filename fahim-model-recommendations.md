# Optimal Model Recommendation Documentation for AI-Assisted Grading

## 1. Objective

Design and recommend an optimal AI model architecture for a scalable, accurate, and cost-efficient automated grading system that supports:

- Rubric-aligned text grading
- Summarization of content
- Retrieval of supporting material
- Optional multimodal input (text, scanned documents)

---

## 2. Recommended Model Architecture

| Task                                | Recommended Model                 | Justification                                                                 |
|------------------------------------|----------------------------------|-------------------------------------------------------------------------------|
| Rubric-based grading (complex)      | **GPT-4.1 (Azure OpenAI)**       | Best-in-class instruction following, high alignment with rubrics, consistent outputs. |
| Rubric-based grading (simple)       | **GPT-4.1 mini**                 | Similar accuracy for simpler, fact-based tasks with lower inference cost.      |
| Semantic search (text/images)       | **Cohere Embed v4 Multimodal**    | State-of-the-art embeddings for text and image vectors; critical for retrieval-augmented grading (RAG). |
| OCR preprocessing (if needed)       | **Azure AI Document Intelligence**| Reliable OCR extraction from scanned handwritten/printed documents.            |

---

## 3. Model Configurations & Hyperparameters

### ✅ GPT-4.1 (Azure OpenAI)

- **Temperature:** `0.2` (low variability, high rubric alignment)
- **Top-p:** `1.0`
- **Max tokens per call:** `2048`
- **Frequency penalty:** `0`
- **Presence penalty:** `0`

### ✅ GPT-4.1 mini

- **Temperature:** `0.3` (slightly higher for natural summarization)
- **Top-p:** `1.0`
- **Max tokens per call:** `1024`

### ✅ Cohere Embed v4 Multimodal

- **efSearch:** `500–1000`
- **topK:** `5–10`
- **Dimension:** `1024`
- Embeddings precomputed and stored in a vector DB.

### ✅ Azure AI Document Intelligence

- Default OCR config unless handwriting-specific OCR is required.

---

## 4. Pricing Estimates (as of April 2025)

| Model                     | Estimated Price (per 1K tokens) | Notes                                                   |
|--------------------------|--------------------------------|--------------------------------------------------------|
| **GPT-4.1**               | **$0.06–$0.08**                | Higher cost, use for final grading and complex feedback.|
| **GPT-4.1 mini**          | **$0.015–$0.02**               | 3–4x cheaper; use for intermediate summaries.          |
| **Cohere Embed v4**       | **$0.0001–$0.0002 per embed**  | Pay per embedding vector generation.                   |
| **Azure AI OCR**          | **$1.50 per 1,000 pages**       | OCR charge for document ingestion.                     |

**Example:**

For a 1,000-word essay (~750 tokens input, ~250 tokens output):

- GPT-4.1 grading → ~$0.06
- GPT-4.1 mini summary + GPT-4.1 final → ~$0.08 total
- Optional OCR (1 page) → ~$0.0015

---

| Criterion          | GPT-4.1                 | GPT-4.1 mini            | Cohere Embed v4             |
|-------------------|------------------------|------------------------|-----------------------------|
| Accuracy           | ✅✅✅                   | ✅✅                     | N/A                         |
| Speed              | ✅                      | ✅✅✅                   | ✅✅✅                        |
| Cost-efficiency    | ❌                      | ✅✅✅                   | ✅✅✅                        |
| Multimodal support | ❌                      | ❌                      | ✅✅✅                        |
| Explainability     | ✅✅✅                   | ✅✅                     | N/A                         |
