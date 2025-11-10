import os
import time
from pathlib import Path
from openai import AzureOpenAI

def get_or_create_vector_store(client: AzureOpenAI, store_name: str = "lecture-slides-store"):
    """
    Get existing vector store or create a new one.
    Returns vector_store_id.
    """
    # List existing vector stores - try direct access first, then beta
    try:
        stores = client.vector_stores.list()
    except AttributeError:
        # Fallback to beta if direct access doesn't work
        stores = client.beta.vector_stores.list()
    
    # Check if store with this name already exists
    for store in stores.data:
        if store.name == store_name:
            print(f"Found existing vector store: {store.id} ({store.name})")
            return store.id
    
    # Create new vector store - remove description parameter
    print(f"Creating new vector store: {store_name}")
    try:
        vector_store = client.vector_stores.create(
            name=store_name
        )
    except AttributeError:
        # Fallback to beta if direct access doesn't work
        vector_store = client.beta.vector_stores.create(
            name=store_name
        )
    
    print(f"Created vector store: {vector_store.id}")
    return vector_store.id

def get_existing_files_in_vector_store(client: AzureOpenAI, vector_store_id: str):
    """
    Get a set of filenames that already exist in the vector store.
    Returns a set of filenames.
    """
    existing_filenames = set()
    
    # Helper function to get the right API access
    def get_vector_stores_api():
        try:
            return client.vector_stores
        except AttributeError:
            return client.beta.vector_stores
    
    vs_api = get_vector_stores_api()
    
    try:
        vector_store_files = vs_api.files.list(vector_store_id=vector_store_id)
        
        for file_item in vector_store_files.data:
            try:
                # Get file details to get the filename
                file_detail = client.files.retrieve(file_item.id)
                if hasattr(file_detail, 'filename') and file_detail.filename:
                    existing_filenames.add(file_detail.filename)
            except Exception as e:
                # If we can't get filename, skip this file
                pass
    except Exception as e:
        print(f"  Warning: Could not list existing files: {e}")
    
    return existing_filenames

def upload_pdfs_to_vector_store(client: AzureOpenAI, vector_store_id: str, materials_path: Path):
    """
    Upload all PDFs from materials folder to vector store.
    Only uploads files that don't already exist (checked by filename).
    Returns list of file IDs.
    """
    pdf_files = list(materials_path.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in materials folder.")
        return []
    
    # Get existing files in vector store
    print("Checking for existing files in vector store...")
    existing_filenames = get_existing_files_in_vector_store(client, vector_store_id)
    
    if existing_filenames:
        print(f"  Found {len(existing_filenames)} existing file(s) in vector store")
    
    # Filter out files that already exist
    files_to_upload = [f for f in pdf_files if f.name not in existing_filenames]
    
    if not files_to_upload:
        print("All PDF files already exist in vector store. Skipping upload.")
        return []
    
    print(f"Uploading {len(files_to_upload)} new file(s)...")
    
    file_ids = []
    
    for pdf_file in files_to_upload:
        print(f"Uploading: {pdf_file.name}")
        
        # Upload file - use "assistants" purpose for Azure OpenAI
        with open(pdf_file, "rb") as f:
            file = client.files.create(
                file=f,
                purpose="assistants"  # Required for Azure OpenAI vector stores
            )
        
        file_ids.append(file.id)
        print(f"  → File ID: {file.id}")
        
        # Add file to vector store - try direct access first, then beta
        try:
            client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file.id
            )
        except AttributeError:
            # Fallback to beta if direct access doesn't work
            client.beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file.id
            )
        
        print(f"  → Added to vector store")
    
    return file_ids

def wait_for_indexing(client: AzureOpenAI, vector_store_id: str, max_wait_minutes: int = 30):
    """
    Poll vector store status until all files are indexed.
    """
    print("\nWaiting for files to be indexed...")
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    # Helper function to get the right API access
    def get_vector_stores_api():
        try:
            return client.vector_stores
        except AttributeError:
            return client.beta.vector_stores
    
    vs_api = get_vector_stores_api()
    
    # Get list of files in the vector store
    try:
        vector_store_files = vs_api.files.list(vector_store_id=vector_store_id)
    except AttributeError:
        # If list doesn't work, try a different approach
        vector_store_files = None
    
    print("  Checking indexing status...")
    
    while True:
        all_complete = True
        
        # Check vector store status
        try:
            vector_store = vs_api.retrieve(vector_store_id)
            
            # Check individual file statuses if we can list them
            if vector_store_files:
                for file_item in vector_store_files.data:
                    file_status = vs_api.files.retrieve(
                        vector_store_id=vector_store_id,
                        file_id=file_item.id
                    )
                    # Check if file is still being processed
                    if hasattr(file_status, 'status'):
                        if file_status.status == "in_progress":
                            all_complete = False
                            print(f"  File {file_item.id[:20]}... still indexing...")
                            break
                        elif file_status.status == "failed":
                            print(f"  ⚠️  File {file_item.id[:20]}... failed to index!")
                            all_complete = False
                            break
            
            # If we can't check individual files, use a simpler approach:
            # Wait a bit and assume indexing is complete after a reasonable time
            if vector_store_files is None:
                elapsed = time.time() - start_time
                if elapsed < 30:  # Wait at least 30 seconds
                    all_complete = False
                    print(f"  Waiting for initial indexing... ({int(elapsed)}s)")
                else:
                    # After 30 seconds, assume indexing is mostly done
                    print("  Assuming indexing is complete (could not verify individual files)")
                    all_complete = True
                    
        except Exception as e:
            # If we can't check status, wait a bit and then proceed
            elapsed = time.time() - start_time
            if elapsed < 30:
                all_complete = False
                print(f"  Waiting... ({int(elapsed)}s)")
            else:
                print(f"  ⚠️  Could not verify status, proceeding anyway after {int(elapsed)}s")
                all_complete = True
        
        if all_complete:
            print("✅ Files should be indexed (or indexing in progress in background)")
            break
        
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print(f"⚠️  Timeout after {max_wait_minutes} minutes. Some files may still be indexing.")
            break
        
        time.sleep(5)  # Poll every 5 seconds

def initialize_vector_store(client: AzureOpenAI, materials_path: Path = None):
    """
    Main function to initialize vector store with all PDFs.
    Only uploads files that don't already exist.
    Returns vector_store_id.
    """
    if materials_path is None:
        materials_path = Path(__file__).parent / "materials"
    
    # Get or create vector store
    vector_store_id = get_or_create_vector_store(client)
    
    # Upload PDFs (only new ones)
    file_ids = upload_pdfs_to_vector_store(client, vector_store_id, materials_path)
    
    if file_ids:
        # Wait for indexing only if new files were uploaded
        wait_for_indexing(client, vector_store_id)
    else:
        print("No new files to index.")
    
    return vector_store_id