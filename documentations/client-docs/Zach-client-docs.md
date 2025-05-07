# Tutorial: Using LLMs for Automated Assignment Grading Assistance

This tutorial provides a comprehensive guide on leveraging Large Language Models (LLMs), specifically via Azure OpenAI, to assist in grading assignments. The tutorial covers:

- Connecting to Azure OpenAI
- Structuring API calls
- Crafting effective prompts for grading tasks
- Understanding key hyperparameters

> **Note:** LLMs should be used as *assistants* in grading. Human oversight remains crucial for fairness, nuance, and final decision-making.

---

## 1. Connecting to Azure OpenAI with Python

To interact with Azure OpenAI, you first need to authenticate and establish a client connection. Store sensitive credentials (API key, endpoint) as environment variables instead of hardcoding them.

### Prerequisites:
- An Azure subscription with Azure OpenAI access.
- A deployed OpenAI model (e.g., `gpt-4`, `gpt-35-turbo`).
- Your Azure OpenAI endpoint and API key.
- Python (`pip install openai`).

### Steps:

#### 1. Set Environment Variables:
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint (e.g., `https://your-resource-name.openai.azure.com/`).
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key.
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Deployed model name.

#### 2. Initialize the Azure OpenAI Client:

```python
import os
from openai import AzureOpenAI

try:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not api_key or not azure_endpoint or not deployment_name:
        raise ValueError("Azure OpenAI environment variables not set.")

    client = AzureOpenAI(
        api_key=api_key,
        api_version="2024-02-01",
        azure_endpoint=azure_endpoint
    )
    print("Azure OpenAI client initialized successfully.")

except ValueError as e:
    print(f"Error: {e}")
    client = None
except Exception as e:
    print(f"Unexpected error: {e}")
    client = None
```

---

## 2. Structuring an LLM API Call for Grading

A typical chat completion request includes the model, messages, and hyperparameters:

```python
# Example prompt setup
system_prompt_content = "You are an AI Grading Assistant. Evaluate the assignment based on the rubric."

user_prompt_content = """
Please grade the submission:

**Rubric:**
- Clarity (5 points)
- Evidence (10 points)

**Student Submission:**
[Student text...]

Provide feedback and scores per criterion, and a total.
"""

if client:
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": user_prompt_content}
            ],
            temperature=0.2,
            max_tokens=1500,
            top_p=1.0
        )

        grading_output = response.choices[0].message.content
        print("\n--- Grading Output ---")
        print(grading_output)

    except Exception as e:
        print(f"API call error: {e}")
```

### Key API Call Components:
- **`model`**: Specifies deployed model.
- **`messages`**: Dictates conversation context and inputs.
- **`temperature`**: Controls randomness (low = focused, high = creative).
- **`top_p`**: Nucleus sampling (range of tokens considered).
- **`max_tokens`**: Limits response length.

---

## 3. Prompt Engineering for Assignment Grading

Effective prompts help achieve reliable grading results. Structure and clarity minimize ambiguity and improve LLM performance.

### Principles:
- **Clarity & Specificity**
- **Structured Layout**
- **Step-by-Step Reasoning**
- **Comprehensive Context**
- **Examples (Few-Shot Learning)**

### Grading Prompt Template:

```markdown
--- START GRADING PROMPT ---

# ROLE
You are an objective AI Grading Assistant.

# OBJECTIVE
Evaluate the submission per rubric criterion. Justify each score clearly.

# INPUTS

## Assignment Context
[Description]

## Grading Rubric
- **Criterion 1** ([Max Points]): Description
- **Criterion 2** ([Max Points]): Description
- **TOTAL POINTS:** [Total]

## Student Submission
[Full submission text]

---

# INSTRUCTIONS
1. Understand assignment & rubric.
2. Evaluate submission by criterion.
3. Justify each criterion score.
4. Ensure scores within limits.
5. Total scores.
6. Format strictly as below.

# REASONING STEPS
- Criterion analysis step-by-step.
- Evidence-based scoring.
- Verify totals.

# OUTPUT FORMAT

```markdown
## Grading Evaluation

**Overall Feedback:** [Summary]

---

### Criteria Breakdown:

**1. [Criterion Name]**
- **Score:** [Awarded] / [Max]
- **Justification:** [Explanation]

**2. [Criterion Name]**
- **Score:** [Awarded] / [Max]
- **Justification:** [Explanation]

---

**Total Score:** [Awarded Total] / [Possible Total]
```

# EXAMPLES (Optional)
- Provide 1–3 examples for clarity.

# FINAL INSTRUCTIONS
Grade based on provided inputs strictly.
```

---

## 4. Bias-Variance Tradeoff in LLM Grading

Understanding **bias** (accuracy) and **variance** (consistency) is crucial:

- **Bias:** Systematic errors due to unclear prompts.
- **Variance:** Output inconsistency due to randomness.

### Hyperparameter Tuning:
- **Temperature**:
  - Low (0.0–0.3): Deterministic.
  - High (0.7–1.0+): Creative, diverse.
- **Top_p**:
  - Low (0.1): Focused.
  - High (0.9–1.0): Diverse.

### Tuning Strategy:
1. **Minimize Bias (Prompt Accuracy)**:
   - Clarify instructions and rubric.
   - Provide examples.
2. **Minimize Variance (Consistency)**:
   - Lower `temperature` or `top_p` (one at a time).

> **Caution:** Reduce variance only after bias is minimized to avoid consistently incorrect outcomes.

---

By carefully structuring prompts and tuning parameters, LLMs become effective grading assistants. Always ensure human oversight for best outcomes.

