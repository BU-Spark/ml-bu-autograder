import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from static.__vectorStore import get_or_create_vector_store

# Load environment variables
load_dotenv()

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

def get_vector_stores_api(client):
    """Helper to get the right API access."""
    try:
        return client.vector_stores
    except AttributeError:
        return client.beta.vector_stores

def list_vector_store_files(vector_store_id: str):
    """List all files in the vector store with their details."""
    vs_api = get_vector_stores_api(client)
    
    try:
        files = vs_api.files.list(vector_store_id=vector_store_id)
        
        print(f"\nFiles in vector store ({len(files.data)} total):")
        print("=" * 80)
        
        file_list = []
        for idx, file_item in enumerate(files.data, 1):
            try:
                file_detail = client.files.retrieve(file_item.id)
                filename = file_detail.filename if hasattr(file_detail, 'filename') else 'Unknown'
                status = file_item.status if hasattr(file_item, 'status') else 'Unknown'
                
                file_list.append({
                    'index': idx,
                    'file_id': file_item.id,
                    'filename': filename,
                    'status': status
                })
                
                print(f"{idx:3d}. {filename}")
                print(f"     File ID: {file_item.id}")
                print(f"     Status: {status}")
                print()
            except Exception as e:
                print(f"{idx:3d}. File ID: {file_item.id} (Error retrieving details: {e})")
                file_list.append({
                    'index': idx,
                    'file_id': file_item.id,
                    'filename': 'Unknown',
                    'status': 'Unknown'
                })
        
        return file_list
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

def delete_file_from_vector_store(vector_store_id: str, file_id: str):
    """Delete a specific file from the vector store."""
    vs_api = get_vector_stores_api(client)
    
    try:
        vs_api.files.delete(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
        print(f"✓ Deleted file: {file_id}")
        return True
    except Exception as e:
        print(f"✗ Error deleting file {file_id}: {e}")
        return False

def delete_all_files_from_vector_store(vector_store_id: str):
    """Delete all files from the vector store."""
    files = list_vector_store_files(vector_store_id)
    
    if not files:
        print("No files to delete.")
        return
    
    print(f"\n⚠️  WARNING: This will delete ALL {len(files)} files from the vector store!")
    confirm = input("Type 'DELETE ALL' to confirm: ").strip()
    
    if confirm != "DELETE ALL":
        print("Cancelled.")
        return
    
    print("\nDeleting files...")
    deleted_count = 0
    for file_info in files:
        if delete_file_from_vector_store(vector_store_id, file_info['file_id']):
            deleted_count += 1
    
    print(f"\n✓ Deleted {deleted_count} out of {len(files)} files.")

def delete_vector_store(vector_store_id: str):
    """Delete the entire vector store."""
    vs_api = get_vector_stores_api(client)
    
    print(f"\n⚠️  WARNING: This will delete the ENTIRE vector store: {vector_store_id}")
    confirm = input("Type 'DELETE STORE' to confirm: ").strip()
    
    if confirm != "DELETE STORE":
        print("Cancelled.")
        return
    
    try:
        vs_api.delete(vector_store_id)
        print(f"✓ Deleted vector store: {vector_store_id}")
    except Exception as e:
        print(f"✗ Error deleting vector store: {e}")

def main():
    print("VECTOR STORE CLEANUP UTILITY")
    print("=" * 80)
    
    # Get vector store
    vector_store_id = get_or_create_vector_store(client)
    print(f"\nVector Store ID: {vector_store_id}\n")
    
    while True:
        print("\n" + "=" * 80)
        print("OPTIONS:")
        print("1. List all files in vector store")
        print("2. Delete specific file(s)")
        print("3. Delete ALL files from vector store")
        print("4. Delete entire vector store (and all files)")
        print("5. Exit")
        print("=" * 80)
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            list_vector_store_files(vector_store_id)
        
        elif choice == "2":
            files = list_vector_store_files(vector_store_id)
            if files:
                print("\nEnter file numbers to delete (comma-separated, e.g., 1,3,5)")
                print("Or 'all' to delete all files")
                selection = input("Selection: ").strip()
                
                if selection.lower() == "all":
                    delete_all_files_from_vector_store(vector_store_id)
                else:
                    try:
                        indices = [int(x.strip()) for x in selection.split(",")]
                        deleted_count = 0
                        for idx in indices:
                            if 1 <= idx <= len(files):
                                file_info = files[idx - 1]
                                if delete_file_from_vector_store(vector_store_id, file_info['file_id']):
                                    deleted_count += 1
                            else:
                                print(f"Invalid index: {idx}")
                        print(f"\n✓ Deleted {deleted_count} file(s).")
                    except ValueError:
                        print("Invalid input. Please enter numbers separated by commas.")
        
        elif choice == "3":
            delete_all_files_from_vector_store(vector_store_id)
        
        elif choice == "4":
            delete_vector_store(vector_store_id)
            print("\nVector store deleted. Exiting.")
            break
        
        elif choice == "5":
            print("Exiting.")
            break
        
        else:
            print("Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()