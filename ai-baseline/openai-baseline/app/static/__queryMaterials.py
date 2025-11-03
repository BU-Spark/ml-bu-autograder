import PyPDF2
from pathlib import Path

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
def __queryFolderPdfs():
    folderPath = r"C:\Users\level\OneDrive\Desktop\ml-bu-autograder\ai-baseline\openai-baseline\app\static\materials"
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
    
    return allContent