# Optimal Model Recommendation Documentation for AI-Assisted Grading

## 1. Objective

Design and recommend an optimal AI model architecture for a scalable, accurate, and cost-efficient automated grading system that supports:

- Rubric-aligned text grading
- Summarization of content
- Retrieval of supporting material
- Optional multimodal input (text, scanned documents, slides)

---

## 2. Recommended Model Architecture

| Task                                | Recommended Model                 | Justification                                                                 |
|------------------------------------|----------------------------------|-------------------------------------------------------------------------------|
| Rubric-based grading (complex)      | **GPT-4.1 (Azure OpenAI)**       | Best-in-class instruction following, high alignment with rubrics, consistent outputs. |
| Rubric-based grading (simple)       | **GPT-4.1 mini**                 | Similar accuracy for simpler, fact-based tasks with lower inference cost.      |
| Semantic search (text/images)       | **Cohere Embed v4 Multimodal**    | State-of-the-art embeddings for text and image vectors; critical for retrieval-augmented grading (RAG). |
| OCR preprocessing (if needed)       | **Azure AI Document Intelligence**| Reliable OCR extraction from scanned handwritten/printed documents.            |

---

## 3. Model Configurations & Hyperparameters (Updated)

### ✅ GPT-4.1 (Azure OpenAI)

- **Temperature:** `0.2` (low variance → consistent rubric alignment)
- **Top-p:** `1.0`
- **Max tokens per call:** `2048`
- **Frequency penalty:** `0`
- **Presence penalty:** `0`
- **Recommended use:** Narrative-heavy grading, final pass.

### ✅ GPT-4.1 mini

- **Temperature:** `0.3–0.4` (moderate variance → flexible summarization across file types)
- **Top-p:** `1.0`
- **Max tokens per call:** `1024`
- **Recommended use:** First-pass summarization of DOCX, PDF captions, PPTX content.

### ✅ Cohere Embed v4 Multimodal

- **efSearch:** `1000`
- **topK:** `10`
- **Dimension:** `1024`
- **Embedding source:** Pre-compute vectors across all uploaded files.
- **Recommended use:** Retrieve supporting material across multi-document context.

### ✅ Azure AI Document Intelligence

- Default OCR config unless handwriting-specific OCR is required.

---

## 4. Updated Pricing Estimates (per typical submission)

Assuming a student submission includes:
- 1 DOCX (~1,000 tokens)
- 1 PDF with diagrams (~500 tokens)
- 1 PPTX (~300 tokens)

Estimated token counts:
- **Total input tokens:** ~1,700
- **Total output tokens (feedback):** ~600

| Model Strategy                    | Estimated Cost per Submission      | Notes                                          |
|----------------------------------|-----------------------------------|------------------------------------------------|
| GPT-4.1 only                     | ~$0.14                            | Direct grading and feedback in GPT-4.1         |
| GPT-4.1 mini + GPT-4.1 final     | ~$0.10                            | Summarize with mini; final pass with GPT-4.1   |
| Optional OCR (1–2 pages)         | ~$0.0015–$0.003                   | Add if scanned files need text extraction      |

✅ Using GPT-4.1 mini for pre-processing reduces costs by ~30% while maintaining quality for rubric-based grading.

---

| Criterion          | GPT-4.1                 | GPT-4.1 mini            | Cohere Embed v4             |
|-------------------|------------------------|------------------------|-----------------------------|
| Accuracy           | ✅✅✅                   | ✅✅                     | N/A                         |
| Speed              | ✅                      | ✅✅✅                   | ✅✅✅                        |
| Cost-efficiency    | ❌                      | ✅✅✅                   | ✅✅✅                        |
| Multimodal support | ❌                      | ❌                      | ✅✅✅                        |
| Explainability     | ✅✅✅                   | ✅✅                     | N/A                         |

---

## 5. Variance and Bias Considerations (Updated for Multi-Document Submissions)

With submissions consisting of DOCX (text), PDF (annotated diagrams), and PPTX (slide summaries), the AI model must handle:

✅ Structured text (narrative)  
✅ Sparse/informal text (slides)  
✅ Diagram captions and figure descriptions  
✅ Optional OCR-extracted text (from scanned PDFs)

This increases **input variability**, which impacts both **variance** and **bias** in model outputs.

| Model               | Baseline Tendency            | Impact of Configs (Multi-Document)         | Recommendation                                   |
|--------------------|-----------------------------|-------------------------------------------|------------------------------------------------|
| **GPT-4.1**         | ✅ Low variance, low bias    | Works well with mixed input but risks overfitting long narratives | Use **temp = 0.2**, **freq/pres penalty = 0** for grading narrative-heavy docs. |
| **GPT-4.1 mini**    | ✅ Low bias, ↑ variance      | Handles summarizing sparse/informal text well | Keep **temp = 0.3–0.4** → allows flexible summarization across formats. |
| **Cohere Embed v4** | N/A (embedding model)       | Higher **topK** may be needed to retrieve scattered info across files | Use **efSearch = 1000**, **topK = 10** to ensure retrieval doesn’t miss diagram metadata. |

---

### 🔍 Key Observations (Multi-Document):

✅ **GPT-4.1** → reliable for long narrative grading but needs low temp to avoid drift across inconsistent formats.

✅ **GPT-4.1 mini** → introduces helpful variance to **compress diverse inputs** (diagrams + slides → short summary).

✅ **Variance increases naturally when combining document types → control using temp + low penalty settings.**

---

### How to control variance & bias:

- **Temperature:** lower → deterministic, lower variance; higher → more diverse but less aligned.
- **Frequency/Presence penalties:** prevent repetition or overuse; keep **0** to avoid penalizing rubric terms.
- **Search params (Cohere):** higher **efSearch/topK** → reduces retrieval variance (missed info).

---

## 6. When to Favor Bias or Variance?

| Scenario                              | Recommendation                                            |
|--------------------------------------|----------------------------------------------------------|
| Strict rubric adherence               | Low variance → GPT-4.1, temp = 0.2                        |
| Flexible interpretation allowed       | Slight ↑ variance → GPT-4.1 mini, temp = 0.3–0.4          |
| Grading novel/creative responses      | Higher variance → temp = 0.4–0.5                          |
| High-stakes final exams               | Minimize variance → GPT-4.1, temp ≤ 0.2                   |

---

## 7. Practical Example:

✅ **Final exam essay →**  
Use GPT-4.1, temperature = 0.2, freq_penalty = 0, pres_penalty = 0

✅ **Weekly reflection →**  
Use GPT-4.1 mini, temperature = 0.3–0.4

✅ **Multi-file grading (DOCX + PDF + PPTX) →**  
Summarize with GPT-4.1 mini (temp = 0.3–0.4)

Final grading with GPT-4.1 (temp = 0.2)


# Running the Recommended AI Models for Grading Pipeline

This guide explains how to run each recommended AI model in the optimal grading architecture:

✅ GPT-4.1 (Azure OpenAI) → final grading  
✅ GPT-4.1 mini (Azure OpenAI) → summarizing course materials  
✅ Cohere Embed v4 Multimodal → semantic embedding (optional)  
✅ Azure AI Document Intelligence → OCR for scanned PDFs

---

# Running the Recommended AI Models for Grading Pipeline

This guide explains how to run each recommended AI model in the optimal grading architecture:

✅ GPT-4.1 (Azure OpenAI) → final grading  
✅ GPT-4.1 mini (Azure OpenAI) → summarizing course materials  
✅ Cohere Embed v4 Multimodal → semantic embedding (optional)  
✅ Azure AI Document Intelligence → OCR for scanned PDFs

---

## 1️⃣ Running GPT-4.1 (Final Grading)

**Prerequisites:**

- Deployed **GPT-4.1** model in Azure OpenAI
- Endpoint (e.g. `https://<your-resource>.openai.azure.com`)
- API Key
- Deployment name (e.g. `gpt-4` or `gpt-4.1`)

👉 **Notebook cell:**

```python
import requests

endpoint = "https://<your-resource>.openai.azure.com/openai/deployments/<deployment-name>/chat/completions?api-version=2024-03-01-preview"
api_key = "<your-api-key>"

headers = {
    "Content-Type": "application/json",
    "api-key": api_key
}

payload = {
    "messages": [
        {"role": "system", "content": "You are an AI grading assistant."},
        {"role": "user", "content": "Grade this student essay: [insert text here]"}
    ],
    "temperature": 0.2,
    "max_tokens": 1500
}

response = requests.post(endpoint, headers=headers, json=payload)
response.raise_for_status()

result = response.json()
print(result["choices"][0]["message"]["content"])




## References

- [Ajami, S., & Arab-Chadegani, R. (2013). Barriers to implement Electronic Health Records (EHRs). *Materia Socio-Medica*, 25(3), 213–215.](https://doi.org/10.5455/msm.2013.25.213-215)

- [Bayomy, N. A., Khedr, A. E., & Abd-Elmegid, L. A. (2021). Adaptive model to support business process reengineering. *PeerJ Computer Science*, 7, e505.](https://doi.org/10.7717/peerj-cs.505)

- [OpenAI. (2024). GPT-4 technical report.](https://openai.com/research/gpt-4)

- [Cohere. (2024). Introducing Cohere Embed v4 Multimodal.](https://docs.cohere.com/docs/embed)

- [Microsoft Azure. (2024). Azure AI Document Intelligence documentation.](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)

- [OpenAI. (2024). Pricing for GPT-4.](https://openai.com/pricing)

- [Cohere. (2024). Pricing.](https://cohere.com/pricing)

- [Microsoft Azure. (2024). Azure Cognitive Services pricing.](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/)
