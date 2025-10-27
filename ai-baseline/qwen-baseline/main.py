from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-1.5B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

answer = """
Business Process Re-engineering is a crucial activity to conduct while implemeting an EHR. It can promote performance by making sure that all interrelated processes, activities, and businesses are smoothly aligned. Thus, enhancing overall quality levels by reducing errors and their huge costs. It can also make sure that all stakeholders are involved, aware and familiar with the coming changes given that EHR implementation can be absulotley overwhelming to hospital staff as observed in litrature. Having the staff familiar does not only affect their stress levels resulting from the change, but also causes them to collaborate and navigate their way through the change better leading to a faster and less problematic organizational shift to the newly implemented EHR.

"""
messages = [
    {
        "role": "system",
        "content": """
You are a supportive and encouraging computer science professor grading a student\’s short-answer quiz. Use the following question and rubric to assign a numerical score out of 16 and provide a short explanation. Be VERY lenient in your grading — the goal is to reward ANY signs of understanding, even if incomplete or partially incorrect. Give VERY generous partial points. Even if the answer is not perfect, reward the student for any effort.

Question:
Why do we need to do Business Process Re-engineering as a part of implementing an EHR? Note: Your answer should be at minimum 4 to 5 sentences and must be in your own words.

Grading Rubric
Up to 6 Points for identifying issues that need BPR
Up to 10 Points for identifying why we need BPR to address the issue(s)
Maximum of 16 Points
Possible reasons could include the ones below, but other reasonable ones are fine.
- Support quality decision-making such as investment choices and to manage the impact of
changes on the organization.
- Optimize IT to support business operations in a cost-effective manner by helping to:
a. Reduce redundancy
b. Reuse existing information and software components
c. Leverage new technology solutions in an EHR system effectively
d. Align closely with an organization&#39;s mission and goals and the goals of key
stakeholders, both internal and external to the enterprise.
- Combine the technology, systems, business and market options to fulfill the enterprise
mission, taking into consideration the:
a. External environment—Like regulations or CMS payment requirements
b. Mission of the healthcare organization—A large, metropolitan teaching hospital has
different needs from a small private practice in the suburbs.
c. Business strategy (such as emphasis on particular populations or diseases)
d. Business models (e.g., transformation to shared financial risk business models like
accountable care organizations)
e. Technology (including existing and new technologies like an EHR  
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
a. Buying decisions are simpler, because the information governing procurement is
readily available in a coherent plan.
b. The procurement process is faster—maximizing procurement speed and flexibility
without sacrificing architectural coherence.
c. The ability to procure heterogeneous, multi-vendor, open systems.

Your Task:
Evaluate the student’s answer using the rubric.
Output exactly in this format:
Score: (number)/16
Explanation: (2–4 sentences explaining your reasoning)
"""
    },
    {
        "role": "user",
        "content": f"{answer}"
    }
]

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=8192
)
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
print("Response:", response)


# from transformers import AutoModelForCausalLM, AutoTokenizer

# model_name = "Qwen/Qwen3-0.6B"

# # load the tokenizer and the model
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# model = AutoModelForCausalLM.from_pretrained(
#     model_name,
#     dtype="auto",
#     device_map="auto"
# )

# # prepare the model input
# prompt = """
# You are a professor of computer science grading a student’s short-answer quiz. The question, grading rubric, and student’s answer are provided below. You must assign a numerical score out of 16 points and a brief explanation following the rubric exactly.

# Question:
# Why do we need to do Business Process Re-engineering (BPR) as a part of implementing an Electronic Health Record (EHR)?
# (Your answer should be a minimum of 4–5 sentences and in your own words.)

# Grading Rubric (Total: 16 Points)

# Identification of Issues that Need BPR (0–6 points)
# Award points based on how clearly the student identifies what problems or inefficiencies exist that justify BPR during EHR implementation.
# Examples include (but are not limited to):

# Redundant or outdated workflows

# Poor data flow or information silos

# Misalignment between current processes and EHR capabilities

# Inefficient manual processes or duplicated efforts

# Lack of interoperability or unclear responsibilities

# Explanation of Why BPR is Needed to Address the Issues (0–10 points)
# Award points based on how well the student explains why BPR is necessary to solve these problems and ensure successful EHR adoption.
# Possible strong reasons may include:

# Improving quality decision-making and organizational alignment

# Reducing redundancy and waste

# Enabling effective use of EHR technology

# Increasing interoperability and efficiency

# Supporting better patient care outcomes

# Lowering long-term costs and simplifying operations


# Student’s Answer:

# to be able to segregate data accurately for research, population health analytics
# for administrative purposes to have more accurate billing and inventory management. improve prompt communications among health care workers.
# protection of patients''s data privacy and having accountability especially while including AI use.
# increase clinical care by giving more awareness to patients and alerting physicians for adverse interactions.
# to have mor ecost effective software or interface that is compatible with multiple interfaces or softwares used for lab and radiology results.
# answering patients about including fitness tracker data and limit of till what extent their data would be included.

# Your Task:

# Evaluate the student’s answer strictly using the rubric above.

# Assign a numerical score (0–16):

# Provide a brief explanation (2–4 sentences) justifying the score.

# Output Format:
# Score: (number between 0 and 16)
# Explanation: (your concise reasoning)
# """
# messages = [
#     {"role": "user", "content": prompt}
# ]
# text = tokenizer.apply_chat_template(
#     messages,
#     tokenize=False,
#     add_generation_prompt=True,
#     enable_thinking=True # Switches between thinking and non-thinking modes. Default is True.
# )
# model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

# # conduct text completion
# generated_ids = model.generate(
#     **model_inputs,
#     max_new_tokens=32768
# )
# output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 

# # parsing thinking content
# try:
#     # rindex finding 151668 (</think>)
#     index = len(output_ids) - output_ids[::-1].index(151668)
# except ValueError:
#     index = 0

# thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
# content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

# # print("thinking content:", thinking_content)
# print("content:", content)
