import os
from dotenv import load_dotenv
from openai import AzureOpenAI
import PyPDF2
from pathlib import Path

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

"""
Extract text from a PDF file and return it as a single string.
"""
def extractTextFromPdf(pdfPath):
    
    with open(pdfPath, 'rb') as file:
        pdfReader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdfReader.pages:
            text += page.extract_text()
    return text

"""
Query all PDF files in a folder and return the model's answer.

The function finds all .pdf files in folderPath, extracts their text,
concatenates them with simple separators indicating the source filename,
then sends the combined content and the question to the Azure OpenAI chat
completions endpoint. Returns the assistant's content string.
"""
def queryFolderPdfs(folderPath, question):

    folder = Path(folderPath)
    pdfFiles = list(folder.glob("*.pdf"))
    
    if not pdfFiles:
        return "No PDF files found in the folder."
    
    print(f"Found {len(pdfFiles)} PDF file(s)")
    
    allContent = ""
    for pdfFile in pdfFiles:
        print(f"Processing: {pdfFile.name}")
        try:
            content = extractTextFromPdf(pdfFile)
            allContent += f"\n\n{'='*50}\n=== Document: {pdfFile.name} ===\n{'='*50}\n\n{content}"
        except Exception as e:
            print(f"Error processing {pdfFile.name}: {e}")
    
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided documents. When referencing information, mention which document it came from."},
            {"role": "user", "content": f"Documents:\n{allContent}\n\nQuestion: {question}"}
        ],
        temperature=0.7,
        max_tokens=3000
    )
    
    return response.choices[0].message.content

"""
Query a single PDF's content and return the model's answer.

Extracts the PDF text and sends it plus the user question to the chat
completions endpoint. Returns the assistant's content string.
"""
def querySinglePdf(pdfPath, question):

    pdfContent = extractTextFromPdf(pdfPath)
    
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided document."},
            {"role": "user", "content": f"Document content:\n\n{pdfContent}\n\nQuestion: {question}"}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    folderPath = r"C:\Users\level\OneDrive\Desktop\ml-bu-autograder\ai-baseline\openai-baseline\app\static\materials"
    question = "What topics are covered in these documents?"
    
    answer = queryFolderPdfs(folderPath, question)
    print(f"\nQuestion: {question}")
    print(f"\nAnswer:\n{answer}")