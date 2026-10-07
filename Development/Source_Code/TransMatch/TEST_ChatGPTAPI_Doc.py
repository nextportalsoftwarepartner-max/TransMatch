# flake8: noqa: E501

import os
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def upload_and_parse(pdf_path, prompt):
    """Send full PDF file to ChatGPT Responses API"""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    response = client.responses.create(
        model="gpt-4.1",  # or gpt-4o for speed
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_file", "file_id": file_obj.id}
            ]
        }]
    )

    return response.output_text


def parse_pdf_page_by_page(pdf_path, prompt):
    """Fallback: Extract text page by page, stop after 'C/F BALANCE'."""
    doc = fitz.open(pdf_path)
    merged = {"Document Info": {}, "Transactions": []}
    stop_processing = False

    for i, page in enumerate(doc, start=1):
        if stop_processing:
            print(
                f"[Stop] Reached 'C/F BALANCE' on previous page. Skipping remaining pages.")
            break

        page_text = page.get_text("text").strip()

        # Stop condition: if C/F BALANCE appears on this page
        if "C/F BALANCE" in page_text.upper():
            stop_processing = True  # mark to stop after this page

        # Skip empty or very short pages
        if len(page_text) < 20:
            print(f"[Skip] Page {i} looks empty, skipping...")
            continue

        # (Optional) Skip pages without any date-like pattern
        if not re.search(r"\d{2}[/-]\d{2}", page_text):
            print(f"[Skip] Page {i} has no transactions, skipping...")
            continue

        success = False
        for attempt in range(2):  # retry max 2 times
            try:
                response = client.responses.create(
                    model="gpt-4.1",
                    input=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": prompt + f"\n\nPage {i}:\n{page_text}"
                            }
                        ]
                    }],
                    # ✅ force JSON output
                    response_format={"type": "json_object"}
                )

                chunk_data = json.loads(response.output_text)

                # Merge Document Info (only take from page 1)
                if i == 1 and "Document Info" in chunk_data:
                    merged["Document Info"] = chunk_data["Document Info"]

                # Merge Transactions
                if "Transactions" in chunk_data:
                    merged["Transactions"].extend(chunk_data["Transactions"])

                success = True
                break  # ✅ stop retry loop if successful

            except Exception as e:
                print(
                    f"[Warning] Page {i} JSON parse error (attempt {attempt+1}): {e}")
                time.sleep(2)  # wait before retry

        if not success:
            print(f"[Error] Page {i} skipped after 2 failed attempts")

    doc.close()
    return merged


def chatgpt_extract_from_pdf(pdf_path):
    prompt = """
    You are a financial document parser.

    Your task:
    1. Extract ALL information from this bank statement PDF. 
    2. Return ONLY valid JSON according to the schema below. 
    3. Do not include any extra commentary or explanations.

    Rules:
    - Document Info:
    • Bank Name, Bank Registration No, Bank Address
    • Customer Code (if available), Customer Name, Customer Address
    • Account Number
    • Statement Date → If more than one date is found, always select the latest (maximum) date.

    - Transactions:
    • Each transaction is usually identified by one date.
    • Each transaction may contain one or more lines of description. 
        If multiple lines belong to the same date/transaction, merge them into:
        - trn_pdf_description (the main description or first line)
        - trn_pdf_description_others (additional description lines, joined as a single string).
    • Extract:
        - trn_pdf_date → transaction date
        - trn_pdf_description → main description text
        - trn_pdf_description_others → merged text of additional detail lines (if any)
        - trn_pdf_ner → the counterparty name (recipient, payee, merchant, or company) 
                        extracted from the description. If no clear name, leave as "".
        - trn_pdf_CR_Amount → credit amount (numeric, 0 if not credit)
        - trn_pdf_DR_Amount → debit amount (numeric, 0 if not debit)
        - trn_pdf_statementBalance → balance after transaction (numeric)

    Schema (strict JSON only):

    {
    "Document Info": {
        "Bank Name": "...",
        "Bank Registration No": "...",
        "Bank Address": "...",
        "Customer Code": "...",
        "Customer Name": "...",
        "Customer Address": "...",
        "Statement Date": "...",
        "Account Number": "..."
    },
    "Transactions": [
        {
        "trn_pdf_date": "...",
        "trn_pdf_description": "...",
        "trn_pdf_description_others": "...",
        "trn_pdf_ner": "...",
        "trn_pdf_CR_Amount": ...,
        "trn_pdf_DR_Amount": ...,
        "trn_pdf_statementBalance": ...
        }
    ]
    }
    """

    try:
        print("[INFO] Trying full PDF upload...")
        raw_output = upload_and_parse(pdf_path, prompt)
        return json.loads(raw_output)
    except Exception as e:
        print(
            f"[WARN] Full PDF parse failed ({e}), fallback to page-by-page...")
        return parse_pdf_page_by_page(pdf_path, prompt)


if __name__ == "__main__":
    pdf_path = r"D:\CHIANWEILON\Software_Dev\TransMatch\Sample\PDF\MUAMALAT_sample_1.pdf"
    data = chatgpt_extract_from_pdf(pdf_path)
    print(json.dumps(data, indent=2))
    print(
        f"\n[INFO] Extracted {len(data.get('Transactions', []))} transactions.")
