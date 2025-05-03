# Documentation and Advice: Using LLMs for Automated Assignment Grading Assistance

This document provides a comprehensive guide on leveraging Large Language Models (LLMs), specifically via Azure OpenAI, to assist in grading assignments. The tutorial covers:

- Connecting to Azure OpenAI
- Structuring API calls
- Crafting effective prompts for grading tasks
- Understanding key hyperparameters

---

## 1. Connecting to Azure OpenAI with Python

To interact with Azure OpenAI, you first need to authenticate and establish a client connection. Store sensitive credentials (API key, endpoint) as environment variables instead of hardcoding them.

### Prerequisites:
- An Azure subscription with Azure OpenAI access.
- A deployed OpenAI model (e.g., `gpt-4`, `gpt-35-turbo`).
- Your Azure OpenAI endpoint and API key.
- Python (`pip install openai`).
- Optional: Weights and Biases, Pandas (`pip install wandb pandas`)

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
    # Many other ways to do this if you don't have environment variables set
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

# For simplicity purposes, you can remove the "try except" statement for simplicity, it just helps handle API errors
if client:
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": user_prompt_content}
            ],
            temperature=0.2, # Note: We advise to keep either temperature or top_p at default values, don't tune both
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

### Basic Grading Prompt Template:
(You can have these in multiple variables for adaptability, then concatenate together as needed)
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
[rubric - make sure it is in a similar level of detail as this prompt. Can use LLM to optimize rubric clarity if you'd like.]

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

# OUTPUT FORMAT - Here you specify to the LLM exactly how you want it to return the grade and feedback.


## Grading Evaluation

**Overall Feedback:** [Summary]


### Criteria Breakdown:

**1. [Criterion Name]**
- **Score:** [Awarded] / [Max]
- **Justification:** [Explanation]

**2. [Criterion Name]**
- **Score:** [Awarded] / [Max]
- **Justification:** [Explanation]


**Total Score:** [Awarded Total] / [Possible Total]

# EXAMPLES (Optional)
- Provide 1–3 examples for clarity.

# FINAL INSTRUCTIONS
Grade based on provided inputs strictly.

```

An example of a good prompt structure is shown below. Note that by no means do you have to use this structure. The main idea is that you use a similar level of detail, and leave as little of a gray area as possible. In addition, make sure you use reiteration and also remind the LLM to have a detailed thinking process among other things. There is no one prompt that will work for everything, so we recommned that each prompt is tuned for the assignment that will be graded. Include important details about the assignment as well as sample graded responses. Warn the LLM about anything you could see going wrong and urge it to not make those mistakes. You can of course tailor any section to your needs. Again, the below example is mostly an example of the level of detail you should use. The content of the prompt can be changed in any way you want. Just make sure you are very detailed, specific, and direct.

```markdown
SYS_PROMPT_GRADING = """
You are an expert grader tasked with evaluating student responses to an assignment based on a rubric and reference answer.

Your task is to **grade with clarity, fairness, consistency, and rigor**, while providing **constructive feedback**. Think step by step before scoring. Be extremely thorough and NEVER stop early. Every response must be fully evaluated against the rubric. If any part of the rubric is not clearly satisfied, you must reflect deeply before awarding full credit.

Your reasoning should be transparent and detailed. Before assigning any score, always justify your decisions and confirm they are well-aligned with both the rubric and the reference solution. Only terminate your turn once you’ve:
1. Compared the response to each rubric point.
2. Justified the awarded score for each item.
3. Provided structured, constructive feedback.


You have access to all necessary information in the provided context—rubric, reference answer, and student answer—so no external resources are needed. This task **can be completed fully offline.**

# Workflow

## High-Level Strategy

1. Understand the rubric and reference answer deeply.
2. Read and interpret the student’s response holistically.
3. Break down the rubric into explicit evaluation points.
4. Grade point-by-point with precise justification.
5. Provide specific, helpful feedback for improvement.
6. Reflect on fairness, edge cases, and borderline cases before finalizing.

# Instructions

## 1. Deeply Understand the Rubric
- Read every rubric point carefully.
- Pay attention to weightings, required terminology, completeness, reasoning quality, and clarity expectations.
- Think through how each rubric point maps to features of a good answer.

## 2. Analyze the Student Response
- Read the entire student answer without judgment.
- Understand the reasoning and structure behind their response.
- Identify key claims, logical flow, correctness, and completeness.

## 3. Point-by-Point Evaluation
- For each rubric criterion:
  - Identify whether it was fully satisfied, partially satisfied, or not addressed.
  - Provide a clear justification using quotes or paraphrases from the student answer.
  - Be critical but fair: if in doubt, analyze whether the student demonstrates understanding or reasoning even if phrasing differs.
  - Use the rubric’s scoring guidance precisely.

## 4. Feedback Construction
- Feedback must be:
  - **Targeted**: linked directly to specific errors or omissions.
  - **Constructive**: includes how the student could improve.
  - **Supportive**: aim to help the student learn, not punish.

## 5. Final Reflection
- Ask yourself:
  - Are you being consistent across responses?
  - Are you rewarding reasoning and originality appropriately?
  - Did you miss any subtle strengths or hidden errors?
- Only submit the final result when you are confident in its thoroughness and fairness.

# Output Format
Your response must be a structured JSON block with the following format:

{
  "score_breakdown": {
	"criterion_1_description": {
  	"score_awarded": int,
  	"justification": "string"
	},
	"criterion_2_description": {
  	"score_awarded": int,
  	"justification": "string"
	},
	...
  },
  "total_score": int,
  "feedback": "Concise, constructive feedback message for the student"
}

# Example (for a rubric with 2 criteria)

{
  "score_breakdown": {
	"Correctly explains the principle of natural selection": {
  	"score_awarded": 3,
  	"justification": "The student explained variation, inheritance, and differential survival clearly, using a well-structured peppered moth example."
	},
	"Includes at least one accurate real-world example": {
  	"score_awarded": 2,
  	"justification": "The student used a giraffe neck example. While the general idea was conveyed, it lacked scientific specificity."
	}
  },
  "total_score": 5,
  "feedback": "Great job explaining the theory. For future assignments, aim for more detail and precision in your real-world examples to show deeper understanding."
}

# Final Note

You MUST grade **thoroughly and fairly**. Pay special attention to:
- Misconceptions
- Missing steps or vague logic
- Partial credit logic
- Consistency with other evaluations
- Rubric clarity

Do NOT stop once a score is given—reflect, validate, and ensure the feedback would help a real student improve. The success of this system depends on your rigorous attention to detail and thoughtful reflection.
"""


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

## 5. Experiments with LLM: 

For experiments with the LLM you could use the Weights and Biases platform to track your results. We will be using the "weave" portion of Weights and Biases, which is designed specifically for tracking LLM experiments. Once you run your code, you will see it pop up in the "runs" section on the website. There, you will be able to see the input, output, as well as the configuration of each experiment. There are also limitless customizations you could add. (https://wandb.ai/home)

Example Python Pipeline to Experiment with Prompt Strategies. For ease of use, we recommend using a python notebook on a platform such as google colab or jupyter notebook.

```python

# If you don't have any of these simply run "pip install name-of-missing-package"
import weave
import math
import pandas as pd
from openai import OpenAI
import tqdm # This is for progress bars when using for loops
import matplotlib.pyplot as plt
import seaborn as sns


# run wandb login, which will prompt you to add your api key, which is provided after you make an account
weave.init('ML Autograder-Grading(original)') # This makes a new section on WandB. So if you want to start a new set of experiments in their own page, then you can rerun this with a new name

# Here is where you would enter the question for the response
question = "Short Answer Question (14 Points): What is one benefit of using an Enterprise Architecture and why is it a benefit?"

# Here you can define any rubric that you would want to use as a variable. You can define multiple rubrics if you'd like and switch them in and out

# Here I enter an 'unclear' rubric as an example. It is unclear and has a lot of gray areas, thus the llm does not grade consistently with this.

unclear_rubric = '''Grading Rubric: 14 TOTAL POINTS
Other reasonable answers are also allowed.

- Present and support the current and future vision of a business and the related As-Is to Should-Be process re-engineering.
- Support quality decision-making such as investment choices and to manage the impact of changes on the organization.
- Optimize IT to support business operations in a cost-effective manner by helping to:
a. Reduce redundancy
b. Reuse existing information and software components
c. Leverage new technology solutions in an EHR system effectively
d. Align closely with an organization's mission and goals and the goals of key stakeholders, both internal and external to the enterprise.

- Combine the technology, systems, business and market options to fulfill the enterprise mission, taking into consideration the:
a. External environment—Like the ARRA and HighTech Act
b. Mission of the healthcare organization—A large, metropolitan teaching hospital has different needs from a small private practice in the suburbs.
c. Business strategy (such as emphasis on particular populations or diseases )
d. Business models (e.g., transformation to shared financial risk business models like accountable care organizations)
e. Technology (including existing and new technologies like an EHR)
 
- Help enable a more efficient IT Operation:
a. Lower software development, support, and maintenance costs
b. Increased portability of applications
c. Improved interoperability and easier system and network management
d. Improved ability to address critical enterprise-wide issues like security
e. Easier upgrade and exchange of system components

- Better return on existing investment and reduced need for future investment:
a. Reduced complexity in the IT infrastructure
b. Maximum return on investment in the existing IT infrastructure
c. The flexibility to make, buy, or out-source IT solutions
d. Reduced overall new investment lower total cost of IT ownership

- Faster, simpler, and cheaper procurement:
a. Buying decisions are simpler, because the information governing procurement is readily available in a coherent plan.
b. The procurement process is faster—maximizing procurement speed and flexibility without sacrificing architectural coherence.
c. The ability to procure heterogeneous, multi-vendor, open systems.'''

# Here I enter a more clear rubric that provides clear grading instructions to the LLM. It provides certain point ranges and reasons for point allotments. In general, you can experiment with certain types of rubrics, but you should make it as clear as possible, including many points of advice or guidelines from the instructor. You can also include graded examples in the prompt, with explanations as to why they received that grade.

clear_rubric = '''Structured Rubric:
 # Structured Grading Rubric for Short Answer Question

## Task
- **Question**: What is one benefit of using an Enterprise Architecture and why is it a benefit?
- **Note**: Students should only provide one benefit. The emphasis is on the depth and detail of the explanation for that single benefit.

## Scoring Criteria

### 1. Explanation of the Benefit (0-6 Points)
- **Detailed Explanation**: The student provides a comprehensive and detailed explanation of the chosen benefit. (5-6 Points)
- **Moderate Explanation**: The explanation of the benefit is clear but lacks depth or detail. (3-4 Points)
- **Basic Explanation**: The explanation is vague or lacks clarity. (1-2 Points)
- **No Explanation**: The benefit is mentioned without any explanation. (0 Points)

### 2. Relevance and Accuracy (0-4 Points)
- **Highly Relevant and Accurate**: The benefit is clearly relevant to Enterprise Architecture, and the explanation is accurate and precise. (3-4 Points)
- **Partially Relevant or Accurate**: Some aspects of the benefit are relevant, but there are minor inaccuracies. (1-2 Points)
- **Irrelevant or Inaccurate**: The benefit is not relevant to Enterprise Architecture or contains major inaccuracies. (0 Points)

### 3. Additional Insights and Justification (0-4 Points)
- **Comprehensive Insights**: The student provides additional insights or justifications, such as examples or implications, that enhance the understanding of the benefit. (3-4 Points)
- **Some Insights**: Some additional insights or justifications are provided, but they are limited. (1-2 Points)
- **No Additional Insights**: The explanation lacks additional insights or justifications. (0 Points) '''

# Putting this above a function will track it in WandB every time it is run
@weave.op() # 🐝 Decorator to track requests
def grade_response(question: str, student_response: str, rubric: str, temp=.5) -> str:
    client = AzureOpenAI(api_key=oai_api_key) # enter your api key however you usually do

    # Set the system prompt here. This is just a basic example of one, but you can adjust your system prompt in many ways, and we later provide suggestions on how to do so with techniques such as chain of thought reasoning, few shot prompting, and OpenAI recommended prompt templates.

    system_prompt = f"You are provided with a short response question, and a grading rubric that lists some of the acceptable repsonses. Based on the rubric and the response," \
    f"You will grade the response out of the allotted points for the question, which is 14 points, as noted in the question itself. You " \
    f"should make the grade that you provide very clear so that it can easily be located in your response. When grading the response, only take into account the content of the rubric," \
    f"and not anything else such as strength of language or spelling errors. Read the question's instructions and rubric very carefully. Here is the question: {question} \n Here is the rubric:" \
    f" {rubric} \n In addition to the grade that you provide, provide your reasoning behind the grade."
    response = client.chat.completions.create(
    model="gpt-4o", # enter model of choice here
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": student_response} # This is where the student response goes
    ],
    temperature=temp, # You can change top-p here as well
    response_format={"type": "text"}
    )
    extracted = response.choices[0].message.content
    return extracted

# You can adjust this function based on the assignment. For this assignment, there are 14 total points so I constantly reiterated that so the LLM would get it right. But essentially, you enter the llm's provided response from when it graded a response as an input, and then ask another llm to extract the number grade that the llm provided. We recommend that you use a cheap model such as gpt 4.1 nano for this. Note the reiteration in the prompt I provide. If you find it is making mistakes, then you can even provide examples of mistakes in the prompt and tell it to make sure it does not make similar mistakes.
@weave.op
def extract_llm_score(summary: str, temp=.1) -> dict:
    client = AzureOpenAI(api_key=oai_api_key) # enter your api key however you usually do
    res = client.chat.completions.create(
        model="gpt-4o", #enter your model of choice here
        messages=[
            {"role": "system", "content": "You are provided with a graded response of a student submission." \
"The graded response may include various points of feedback and words, but it will also include a number grade" \
"out of 14 points. I want you to find this score that is provided in response and respond with that score only, nothing else." \
"For example, if the grade provided is 7/14, or 7 out of 14, then I want you to return the ratio of the grade, so it would be 7/14." \
"Note that I am running automated computation with the output, so the format of the response must be NUMERATOR/DENOMINATOR and that is it!"},
            {"role": "user", "content": (
                f"Extract the grade and return in N/D format: "
                f"Summary: {summary}"
            )}], 
            temperature=temp,
            response_format={"type": "text"})
    extracted = res.choices[0].message.content
    return extracted

# This function takes the output of the previous function that extracts the numerical output from the LLM's provided grade and returns it so it can be used in further computation or visualization.

import math

def compute_ratio(ratio_str):
    try:
        # Split the string and convert to floats
        numerator, denominator = map(float, ratio_str.split('/'))
        return numerator / denominator
    except Exception:
        # Return NaN if there's any error (e.g., wrong format or conversion error)
        return math.nan


# Example of running 100 Trial Experiment

num_trials = 100

# What this does is store the trial number, raw llm output, then the number part of the output, then the number part of the output converted to a usable floating point format (processed score, which is what you would run any analysis with).

experiment_dataset = {"Trial Number": [],
                      "Unprocessed Scoring": [],
                      "Located Score": [],
                      "Processed Score": []}

submission = sentence # from previous section

# Each iteration of your experiment, you can change something such as the submission, rubric etc. The way to do this is to use lists. So, for example, if you wanted to try 100 different rubrics, you would make a list with 100 rubrics, and the at each iteration of the for loop, set your rubric to rubrics[i] if there is a list called rubrics. The best part about Weights and Biases is that you will be able to see everything about each experiment on the website.

for i in tqdm.tqdm(range(num_trials)):
    experiment_dataset["Trial Number"].append(i)

    graded_response, call = grade_response.call(question, submission, clear_rubric)
    experiment_dataset["Unprocessed Scoring"].append(graded_response)

    score = extract_llm_score(graded_response)
    experiment_dataset["Located Score"].append(score)

    processed_score = compute_ratio(score)
    experiment_dataset["Processed Score"].append(processed_score)


# Code to visualize and analyze the experiment results

df = pd.DataFrame(experiment2_dataset)
# print(df) visualize results

# This code here tells you all of the unique scores provided and how many times they are given
processed_scores = df['Processed Score']
unique_counts = processed_scores.value_counts().sort_index()
print("Unique values and their counts:")
print(unique_counts)


# Statistics on grades provided by LLM
mean_val = processed_scores.mean()
variance_val = processed_scores.var()  # sample variance
std_dev_val = processed_scores.std()    # sample standard deviation
print("Mean:", mean_val)
print("Variance:", variance_val)
print("Standard Deviation:", std_dev_val)


# Plot the distribution of the grades. Want as narrow of a distribution as possible IF you are grading the same submission each time. If you are grading different submissions at each step of the experiment, then a wider distribution is ok. 
plt.figure(figsize=(10, 6))
sns.histplot(processed_scores, bins=4, kde=True)
plt.title("Distribution of Scores")
plt.xlabel("Scores")
plt.ylabel("Frequency")
plt.show()
```