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