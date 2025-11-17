import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from static.__vectorStore import initialize_vector_store

# Load environment variables
load_dotenv()

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Get vector store
print("Getting vector store...")
VECTOR_STORE_ID = initialize_vector_store(client)
print(f"Vector Store ID: {VECTOR_STORE_ID}\n")

def list_vector_store_files():
    """List all files in the vector store."""
    print("=" * 60)
    print("FILES IN VECTOR STORE")
    print("=" * 60)
    
    try:
        vs_api = client.vector_stores
    except AttributeError:
        vs_api = client.beta.vector_stores
    
    files = vs_api.files.list(vector_store_id=VECTOR_STORE_ID)
    
    print(f"Total files: {len(files.data)}\n")
    for file_item in files.data:
        # Get file details
        try:
            file_detail = client.files.retrieve(file_item.id)
            print(f"File ID: {file_item.id}")
            print(f"  Name: {file_detail.filename if hasattr(file_detail, 'filename') else 'N/A'}")
            print(f"  Status: {file_item.status if hasattr(file_item, 'status') else 'N/A'}")
            print()
        except Exception as e:
            print(f"File ID: {file_item.id}")
            print(f"  Error retrieving details: {e}\n")

def test_query(query: str, show_details: bool = True):
    """Test a query to see what content is retrieved."""
    print("=" * 60)
    print(f"TESTING QUERY: {query}")
    print("=" * 60)
    
    # Create assistant
    assistant = client.beta.assistants.create(
        name="Test Inspector",
        instructions="You are a helpful assistant that shows what content you can access. When asked about lecture materials, show the exact content you retrieved, including document names and slide numbers if available.",
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [VECTOR_STORE_ID]
            }
        }
    )
    
    # Create thread and ask query
    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query
    )
    
    # Run assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    
    # Wait for completion
    print("Processing...", end="", flush=True)
    while run.status in ["queued", "in_progress", "requires_action"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        print(".", end="", flush=True)
    print("\n")
    
    if run.status == "completed":
        # Get messages
        messages = client.beta.threads.messages.list(
            thread_id=thread.id,
            order="asc"
        )
        
        # Get assistant response
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        if assistant_messages:
            latest_message = assistant_messages[-1]
            
            if latest_message.content:
                response_text = ""
                for content_block in latest_message.content:
                    if content_block.type == "text":
                        response_text += content_block.text.value
                        if show_details and hasattr(content_block.text, 'annotations'):
                            # Show file citations if available
                            annotations = content_block.text.annotations
                            if annotations:
                                print("File Citations Found:")
                                for ann in annotations:
                                    if hasattr(ann, 'file_citation'):
                                        print(f"  - File ID: {ann.file_citation.file_id}")
                
                print("RESPONSE:")
                print("-" * 60)
                print(response_text)
                print("-" * 60)
                
                # Check for slide numbers or document references
                if "slide" in response_text.lower() or "module" in response_text.lower():
                    print("\n✓ Contains references to slides/modules")
                else:
                    print("\n⚠ No explicit slide/module references found")
    else:
        print(f"Error: Run status is {run.status}")
        if run.last_error:
            print(f"Error details: {run.last_error}")
    
    # Clean up
    try:
        client.beta.assistants.delete(assistant.id)
    except:
        pass

def test_specific_queries():
    """Test with specific queries to check content accessibility."""
    print("\n" + "=" * 60)
    print("TESTING SPECIFIC QUERIES")
    print("=" * 60 + "\n")
    
    test_queries = [
        "What lecture materials do you have access to? List all document names.",
        "List all slide numbers or page numbers you can see in the documents.",
        # "What is Business Process Re-engineering? Show me which slide or module this comes from.",
        # "What topics are covered in Module 1?",
        # "What topics are covered in Module 2?",
        # "What topics are covered in Module 3?",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}/{len(test_queries)}]")
        test_query(query, show_details=True)
        print("\n" + "-" * 60 + "\n")
        time.sleep(2)  # Small delay between queries

if __name__ == "__main__":
    print("VECTOR STORE CONTENT INSPECTOR")
    print("=" * 60 + "\n")
    
    # List files
    list_vector_store_files()
    
    # Test queries
    print("\n" + "=" * 60)
    print("Choose an option:")
    print("1. List files only")
    print("2. Test with specific queries")
    print("3. Custom query")
    print("=" * 60)
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        pass  # Already listed files
    elif choice == "2":
        test_specific_queries()
    elif choice == "3":
        custom_query = input("Enter your query: ").strip()
        if custom_query:
            test_query(custom_query)
    else:
        print("Invalid choice. Running default tests...")
        test_specific_queries()