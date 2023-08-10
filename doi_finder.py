import PyPDF2
import re

def extract_dois(text):
    doi_pattern = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b', re.IGNORECASE)
    return doi_pattern.findall(text)

def extract_dois_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        pdf = PyPDF2.PdfFileReader(file)
        text = " ".join(page.extractText() for page in pdf.pages)
    return extract_dois(text)  # Using the extract_dois function from above

pdf_path = 'path_to_your_pdf.pdf'
dois = extract_dois_from_pdf(pdf_path)
print(dois)
