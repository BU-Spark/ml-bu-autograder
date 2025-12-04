import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
import pandas as pd
from static.__variables import SYSTEM_ROLE
from static.__vectorStore import initialize_vector_store

# Load environment variables from .env file
load_dotenv()

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_LLM_DEPLOYMENT_KEY"),
    azure_endpoint=os.getenv("AZURE_LLM_DEPLOYMENT_URL"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Initialize vector store (one-time setup)
print("Initializing vector store with lecture slides...")
VECTOR_STORE_ID = initialize_vector_store(client)
print(f"Vector store ready: {VECTOR_STORE_ID}\n")

def grade_single_answer(assistant_id: str, student_answer: str):
    """
    Grade a single student answer using the assistant.
    Returns a dictionary with score, comment, and citations.
    """
    # Create a new thread for this answer
    thread = client.beta.threads.create()
    
    # Add the student answer as a user message
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=student_answer
    )
    
    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    
    # Wait for the run to complete
    while run.status in ["queued", "in_progress", "requires_action"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
    
    if run.status == "completed":
        # Retrieve the assistant's response
        messages = client.beta.threads.messages.list(
            thread_id=thread.id,
            order="asc"
        )
        
        # Get the latest assistant message
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        if assistant_messages:
            latest_message = assistant_messages[-1]
            # Extract text content
            if latest_message.content:
                response_text = ""
                for content_block in latest_message.content:
                    if content_block.type == "text":
                        response_text += content_block.text.value
                
                # Try to parse JSON from response
                try:
                    # Extract JSON from response (might have extra text)
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        result = json.loads(json_str)
                        return {
                            "score": result.get("score", "N/A"),
                            "comment": result.get("comment", ""),
                            "citations": result.get("citations", [])
                        }
                    else:
                        return {
                            "score": "N/A",
                            "comment": response_text,
                            "citations": []
                        }
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the raw response
                    return {
                        "score": "N/A",
                        "comment": response_text,
                        "citations": []
                    }
    
    # If run failed or no response
    return {
        "score": "Error",
        "comment": f"Run status: {run.status}",
        "citations": []
    }

def grade_batch_from_excel(excel_path: Path, output_path: Path = None):
    """
    Grade all quiz answers from an Excel file.
    
    Args:
        excel_path: Path to the Excel file
        output_path: Path to save results (default: same folder as input, with '_graded' suffix)
    """
    # Read the Excel file
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name='Quiz 1 Answers')
    
    # Verify columns exist
    if 'Student Number' not in df.columns or 'Student Answer' not in df.columns:
        raise ValueError("Excel file must have 'Student Number' and 'Student Answer' columns")
    
    print(f"Found {len(df)} student answers to grade\n")
    
    # Create assistant
    print("Creating assistant with file search...")
    assistant = client.beta.assistants.create(
        name="Quiz Grader Batch",
        instructions=SYSTEM_ROLE,
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [VECTOR_STORE_ID]
            }
        }
    )
    print(f"Assistant created: {assistant.id}\n")
    
    # Grade each answer
    results = []
    for idx, row in df.iterrows():
        student_number = row['Student Number']
        student_answer = str(row['Student Answer']) if pd.notna(row['Student Answer']) else ""
        
        if not student_answer.strip():
            print(f"Student {student_number}: Empty answer, skipping")
            results.append({
                "Student Number": student_number,
                "Score": "N/A",
                "Comment": "Empty answer",
                "Citations": ""
            })
            continue
        
        print(f"Grading Student {student_number} ({idx + 1}/{len(df)})...", end=" ", flush=True)
        
        try:
            grade_result = grade_single_answer(assistant.id, student_answer)
            
            # Format citations as string
            citations_str = ", ".join(grade_result["citations"]) if grade_result["citations"] else ""
            
            results.append({
                "Student Number": student_number,
                "Score": grade_result["score"],
                "Comment": grade_result["comment"],
                "Citations": citations_str
            })
            
            print(f"✓ Score: {grade_result['score']}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append({
                "Student Number": student_number,
                "Score": "Error",
                "Comment": str(e),
                "Citations": ""
            })
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Determine output path
    if output_path is None:
        output_path = excel_path.parent / f"{excel_path.stem}_graded.xlsx"
    
    # Save to Excel
    results_df.to_excel(output_path, index=False)
    print(f"\n✅ Results saved to: {output_path}")
    
    # Also save as CSV
    csv_path = output_path.with_suffix('.csv')
    results_df.to_csv(csv_path, index=False)
    print(f"✅ Results also saved to: {csv_path}")
    
    return results_df

"""
Grades a set of quiz (input-provided) answers using the LLM and document context.

Uses File Search with Vector Stores via Assistants API to retrieve relevant slide content.
Commands:
    /exit  - quit
    /reset - clear conversation history
"""
def gradeQuizAnswers():
    # Create an assistant with file_search capability
    print("Creating assistant with file search...")
    assistant = client.beta.assistants.create(
        name="Quiz Grader",
        instructions=SYSTEM_ROLE,
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [VECTOR_STORE_ID]
            }
        }
    )
    print(f"Assistant created: {assistant.id}\n")
    
    # Create a thread for the conversation
    thread = client.beta.threads.create()
    print("Chat started. Type /exit to quit, /reset to clear history.")
    print("File Search is enabled - model will retrieve relevant slide content.\n")
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "/exit":
                print("Exiting chat.")
                break
            if user_input.lower() == "/reset":
                # Create a new thread to reset conversation
                thread = client.beta.threads.create()
                print("Conversation history cleared.")
                continue
            
            # Add user message to thread
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )
            
            try:
                # Run the assistant
                run = client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=assistant.id
                )
                
                # Wait for the run to complete
                print("Processing...", end="", flush=True)
                while run.status in ["queued", "in_progress", "requires_action"]:
                    time.sleep(1)
                    run = client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                    print(".", end="", flush=True)
                
                print()  # New line after dots
                
                if run.status == "completed":
                    # Retrieve the assistant's response
                    messages = client.beta.threads.messages.list(
                        thread_id=thread.id,
                        order="asc"
                    )
                    
                    # Get the latest assistant message
                    assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
                    if assistant_messages:
                        latest_message = assistant_messages[-1]
                        # Extract text content
                        if latest_message.content:
                            response_text = ""
                            for content_block in latest_message.content:
                                if content_block.type == "text":
                                    response_text += content_block.text.value
                            
                            print(f"\nResponse: {response_text}")
                        else:
                            print("\nResponse: (No text content)")
                    else:
                        print("\nResponse: (No response generated)")
                else:
                    print(f"\nError: Run status is {run.status}")
                    if run.last_error:
                        print(f"Error details: {run.last_error}")
                
            except Exception as e:
                print(f"Error from API: {e}")
                import traceback
                traceback.print_exc()
                
    except (KeyboardInterrupt, EOFError):
        print("\nChat terminated.")

if __name__ == "__main__":
    import sys
    
    # Check if batch mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        # Batch grading mode
        excel_path = Path(__file__).resolve().parents[2] / "data" / "quiz_1" / "CS 549 Autograder Quiz 1.xlsx"
        
        if not excel_path.exists():
            print(f"Error: Excel file not found at {excel_path}")
            sys.exit(1)
        
        grade_batch_from_excel(excel_path)
    else:
        # Interactive mode
        gradeQuizAnswers()