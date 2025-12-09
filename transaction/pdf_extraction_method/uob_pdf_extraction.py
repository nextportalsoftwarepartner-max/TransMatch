# flake8: noqa: E501
from datetime import datetime
import re
import logger
import json
import fitz  # type: ignore # PyMuPDF
from transaction.name_extractor import NER_extraction
from transaction.name_extractor import NER_extraction_ML
from datetime import datetime


def output_rawdata(text):
    # # To output the raw data from "text"
    output_path = r"D:\CHIANWEILON\Software_Dev\TransMatch\Sample\OUTPUT_TEXT\OUTPUT_TEXT_.txt"
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(text)

# ===================== UOB Bank & ISLAMIC BANK =====================
# UOB & ISLAMIC TEMPLATE - GENERAL INFO EXTRACTION --------------------------------------------
def extract_docInfo(text, id_bnk, pdf_path_global):
    logger.logger.info("[uob_pdf_extraction][extract_docInfo()] : Executing the UOB pdf file extraction operation, for the general PDF info only")
    # output_rawdata(text)

    bank_name = "UOB Bank Berhad"
    bank_regNo = 'NA'
    bank_address = 'NA'
    cust_address = 'NA'
    customer_name = 'NA'
    account_number = 'NA'
    statement_date = 'NA'
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 🔹 Get customer name Info
    for line in lines:
        if re.search(r"\bSDN\.?\s+BHD\.?\b", line, re.IGNORECASE):
            customer_name = line.strip().title()
            break

    # 🔹 Get account number info
    for line in lines:
        if "CURRENT ACCOUNT" in line.upper():
            # Example: "Current Account MYR 1103010670"
            match = re.search(r"Current\s+Account.*?(\d{6,})", line, re.IGNORECASE)
            if match:
                account_number = match.group(1).strip()
                break   
    
    # 🔹 Get statement date (max) info
    for i, line in enumerate(lines):
        if line.strip().lower() == "statement date":
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Example: "01/06/2024 - 30/06/2024"
                date_matches = re.findall(r"\d{2}/\d{2}/\d{4}", next_line)
                if date_matches:
                    try:
                        parsed_dates = [datetime.strptime(d, "%d/%m/%Y") for d in date_matches]
                        statement_date = max(parsed_dates).strftime("%d/%m/%y")
                        logger.logger.info(f"[uob_pdf_extraction] : Extracted statement_date = {statement_date}")
                    except Exception as e:
                        logger.logger.warning(f"[uob_pdf_extraction] : Failed to parse statement_date → {e}")
            break

    return {
        "Bank Name": bank_name,
        "Bank Registration No": bank_regNo,
        "Bank Address": bank_address,
        "Customer Name": customer_name,
        "Customer Address": cust_address,
        "Statement Date": statement_date,
        "Account Number": account_number
    }

# UOB & UOB ISLAMIC  BANK TEMPLATE - TRANSACTION EXTRACTION --------------------------------------------
def extract_trxInfo(text, id_bnk, pdf_path_global):
    logger.logger.info("[uob_pdf_extraction][extract_trxInfo()] : Executing the UOB pdf file extraction operation, for the transaction(s) data only")
    # output_rawdata(text)

    # 1️⃣ Perform pre-cleaning (Step 1) in the text to remove unnecessary text
    lines = text.split("\n")
    cleaned_lines = []
    skip = False

    for line in lines:
        current = line.strip()
        if not current:
            continue  # skip blank lines

        # 🔹 Start skipping when "Account Activities" found
        if "ACCOUNT ACTIVITIES" in current.upper():
            skip = True
            continue

        # 🔹 Stop skipping when "Ledger Balance(MYR)" found
        if "LEDGER BALANCE(MYR)" in current.upper():
            skip = False
            continue

        if not skip:
            cleaned_lines.append(current)

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)
    output_rawdata(textCleaned)

    # 2️⃣ Perform pre-cleaning (Step 2) in the text to remove unnecessary text
    lines = textCleaned.split("\n")
    cleaned_lines = []
    skip = False

    for line in lines:
        current = line.strip()
        if not current:
            continue  # skip blank lines

        # 🔹 Start skipping when "Account Activities" found
        if "TOTAL DEPOSITS(MYR)" in current.upper():
            skip = True
            continue

        if not skip:
            cleaned_lines.append(current)

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)
    output_rawdata(textCleaned)

    # 3️⃣ Perform pre-cleaning (Step 3) in the text to remove unnecessary text
    lines = textCleaned.split("\n")
    cleaned_lines = []
    skip_next = False

    for line in lines:
        current = line.strip()
        if not current:
            continue

        # If previous iteration flagged to skip this line → skip it
        if skip_next:
            skip_next = False
            continue

        # Detect date+time pattern (e.g. 01/06/2024 10:33:32)
        if re.search(r"\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}", current):
            skip_next = True   # also skip next line (e.g., "AM" / "PM")
            continue

        cleaned_lines.append(current)

    textCleaned = "\n".join(cleaned_lines)
    # output_rawdata(textCleaned)

    # Group transactions by date pattern (e.g., 02 Jul, 05 Jul, etc.)
    lines = [ln.strip() for ln in textCleaned.split("\n") if ln.strip()]

    # Step 1️⃣ : Group by date (e.g., 02/06/2024)
    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    transactions = []
    current_block = []

    for line in lines:
        if date_pattern.match(line):
            if current_block:
                transactions.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        transactions.append(current_block)

    # Step 2️⃣ : Extract structured fields
    structured_trx = []
    # Regex to match all valid amount formats (e.g. 44,866.97 / -44,866.97 / 44,866.97-)
    amount_pat = re.compile(r"^-?\d{1,3}(?:,\d{3})*\.\d{2}-?$")

    def clean_amount(val: str) -> float:
        val = val.strip().replace(",", "")
        neg = False
        if val.startswith("-"):
            neg = True
            val = val[1:]
        if val.endswith("-"):
            neg = True
            val = val[:-1]
        try:
            num = float(val)
            return -num if neg else num
        except ValueError:
            return 0.0

    for block in transactions:
        if len(block) < 5:
            continue  # not enough data to form a valid transaction

        date = block[0].strip()
        description = block[1].strip() if len(block) > 1 else ""

        # Find numeric lines (supporting +/- values)
        numeric_lines_raw = [ln for ln in block if amount_pat.match(ln)]
        if len(numeric_lines_raw) < 3:
            continue  # must have 3 numeric values: DR, CR, Balance

        # 4️⃣ amount_dr = first amount
        # 5️⃣ amount_cr = second amount
        # 6️⃣ balance   = third amount
        amount_dr = clean_amount(numeric_lines_raw[0])
        amount_cr = clean_amount(numeric_lines_raw[1])
        balance = clean_amount(numeric_lines_raw[2])

        # 3️⃣ description_others = all lines between line 3 and before numeric section
        idx_first_amount = block.index(numeric_lines_raw[0])
        desc_others_lines = block[2:idx_first_amount]
        description_others = " ".join(desc_others_lines).strip()
        ner = NER_extraction_ML(description + " " + description_others) or ""

        structured_trx.append({
            "trn_pdf_date": datetime.strptime(date, "%d/%m/%Y").strftime("%d/%m/%y"),
            "trn_pdf_description": description,
            "trn_pdf_description_others": description_others,
            "trn_pdf_DR_Amount": amount_dr,
            "trn_pdf_CR_Amount": amount_cr,
            "trn_pdf_statementBalance": balance,
            "trn_pdf_ner": ner
        })

    logger.logger.info(f"[uob_pdf_extraction] : Extracted total records = {len(structured_trx)} transactions")
    return structured_trx
