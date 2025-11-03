import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from static.__variables import SYSTEM_ROLE

# Load environment variables from .env file
load_dotenv()

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

"""
Grades a set of quiz (input-provided) answers using the LLM.

Continously talk to the LLM (GPT5).
Commands:
    /exit  - quit
    /reset - clear conversation history
    
TODO:
Automatically pass in student answers, etc.

TODO:
Implement file searching for contextual info.
"""
def gradeQuizAnswers():
	history = [{"role": "system", "content": SYSTEM_ROLE}]
	print("Chat started. Type /exit to quit, /reset to clear history.")
	try:
		while True:
			user_input = input("\nYou: ").strip()
			if not user_input:
				continue
			if user_input.lower() == "/exit":
				print("Exiting chat.")
				break
			if user_input.lower() == "/reset":
				history = [{"role": "system", "content": SYSTEM_ROLE}]
				print("Conversation history cleared.")
				continue
			# append user message and send request
			history.append({"role": "user", "content": user_input})
			try:
				response = client.chat.completions.create(
					model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
					messages=history,
					temperature=0.7, # controls reproducibility
					# max_tokens=1000 # controls length
				)
				assistant_msg = response.choices[0].message.content
				# append assistant reply to history so context is preserved
				history.append({"role": "assistant", "content": assistant_msg})
				print(f"\Response: {assistant_msg}")
			except Exception as e:
				print(f"Error from API: {e}")
				# don't lose the ability to continue; keep history as-is
	except (KeyboardInterrupt, EOFError):
		print("\nChat terminated.")

if __name__ == "__main__":
	gradeQuizAnswers()