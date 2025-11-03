import os
from dotenv import load_dotenv
from openai import AzureOpenAI
import PyPDF2
from pathlib import Path

load_dotenv()

# Initialize client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def query_folder_pdfs(folder_path, question):
    """Query all PDFs in a folder"""
    # Get all PDF files in the folder
    folder = Path(folder_path)
    pdf_files = list(folder.glob("*.pdf"))
    
    if not pdf_files:
        return "No PDF files found in the folder."
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
    # Extract text from all PDFs
    all_content = ""
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        try:
            content = extract_text_from_pdf(pdf_file)
            all_content += f"\n\n{'='*50}\n=== Document: {pdf_file.name} ===\n{'='*50}\n\n{content}"
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
    
    # Query the combined content
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided documents. When referencing information, mention which document it came from."},
            {"role": "user", "content": f"Documents:\n{all_content}\n\nQuestion: {question}"}
        ],
        temperature=0.7,
        max_tokens=3000
    )
    
    return response.choices[0].message.content

def query_single_pdf(pdf_path, question):
    """Query a single PDF"""
    pdf_content = extract_text_from_pdf(pdf_path)
    
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided document."},
            {"role": "user", "content": f"Document content:\n\n{pdf_content}\n\nQuestion: {question}"}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content

# Example usage
if __name__ == "__main__":
    # Query all PDFs in a folder
    folder_path = r"C:\Users\level\OneDrive\Desktop\ml-bu-autograder\ai-baseline\openai-baseline\app\static\materials"
    question = "What topics are covered in these documents?"
    
    answer = query_folder_pdfs(folder_path, question)
    print(f"\nQuestion: {question}")
    print(f"\nAnswer:\n{answer}")