import requests
from fpdf import FPDF
from bs4 import BeautifulSoup

# URLs of the ChainLit documentation pages
urls = [
    "https://docs.chainlit.io/api-reference/message",
    "https://docs.chainlit.io/api-reference/step-decorator",
    "https://docs.chainlit.io/api-reference/step-class"
]

# Function to get the title and content from a webpage
def get_content(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.find('title').text
    content = soup.find_all(['h1', 'h2', 'h3', 'p', 'pre'])
    return title, content

# Create a PDF document
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)

# Add content to the PDF
for url in urls:
    title, content = get_content(url)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    
    for tag in content:
        if tag.name in ['h1', 'h2', 'h3']:
            pdf.set_font("Arial", 'B', size=12)
            pdf.cell(0, 10, txt=tag.text, ln=True)
        elif tag.name == 'pre':
            pdf.set_font("Courier", size=10)
            pdf.multi_cell(0, 10, txt=tag.text)
        else:
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, txt=tag.text)

# Save the PDF
pdf_file_path = "chainlit_docs.pdf"
pdf.output(pdf_file_path)


