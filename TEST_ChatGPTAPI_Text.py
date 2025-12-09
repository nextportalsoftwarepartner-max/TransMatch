# flake8: noqa: E501

import fitz  # PyMuPDF
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_pdf_text(pdf_path):
    """Extract raw text from all pages using fitz (PyMuPDF)."""
    doc = fitz.open(pdf_path)
    text_pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            text_pages.append(f"--- PAGE {page_num} ---\n{text}")
    doc.close()
    return "\n\n".join(text_pages)


def chatgpt_parse_statement(pdf_text):
    """Send extracted text to ChatGPT and get structured JSON."""
    prompt = """
    You are a financial document parser.
    The following is raw extracted text from a bank statement PDF.

    Rules:
    - Extract Document Info:
      • Bank Name, Bank Registration No, Bank Address
      • Customer Code (if available), Customer Name, Customer Address
      • Account Number
      • Statement Date → If more than one date is found, pick the latest (maximum).

    - Extract Transactions:
      • Each transaction usually has one date.
      • Each transaction may have one or more description lines → 
        merge into 'trn_pdf_description' (first line) and 'trn_pdf_description_others' (remaining).
      • Extract:
        - trn_pdf_date
        - trn_pdf_description
        - trn_pdf_description_others
        - trn_pdf_ner (counterparty: recipient, payee, merchant, or company; "" if unclear)
        - trn_pdf_CR_Amount (credit, numeric, 0 if none)
        - trn_pdf_DR_Amount (debit, numeric, 0 if none)
        - trn_pdf_statementBalance (balance after transaction)

    Return ONLY valid JSON with this schema:
    {
      "Document Info": {...},
      "Transactions": [...]
    }

    Now parse this statement text:
    """

    response = client.responses.create(
        model="gpt-4.1",  # or gpt-4o-mini for cheaper test
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt + "\n\n" + pdf_text}
            ]
        }],
        # response_format={"type": "json_object"}  # ✅ force JSON
    )

    return json.loads(response.output_text)


if __name__ == "__main__":
    pdf_path = r"D:\CHIANWEILON\Software_Dev\TransMatch\Sample\PDF\MUAMALAT_sample_1.pdf"
    text = extract_pdf_text(pdf_path)            # 1. Extract with fitz
    structured = chatgpt_parse_statement(text)   # 2. Send to ChatGPT
    print(json.dumps(structured, indent=2))
