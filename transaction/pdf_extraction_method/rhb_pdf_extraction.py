# flake8: noqa: E501
from datetime import datetime
import re
import logger
import json
import fitz  # type: ignore # PyMuPDF
from transaction.name_extractor import NER_extraction
from datetime import datetime


def output_rawdata(text):
    # # To output the raw data from "text"
    output_path = r"D:\CHIANWEILON\Software_Dev\TransMatch\Sample\OUTPUT_TEXT\OUTPUT_TEXT_.txt"
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(text)


def extract_docInfo(text, id_bnk, pdf_path_global):
    if id_bnk == 8:
        return extract_docInfo_1(text, id_bnk, pdf_path_global)
    else:
        return extract_docInfo_2(text, id_bnk, pdf_path_global)

def extract_trxInfo(text, id_bnk, pdf_path_global):
    if id_bnk == 8:
        return extract_trxInfo_1(text, id_bnk, pdf_path_global)
    else:
        return extract_trxInfo_2(text, id_bnk, pdf_path_global)

# ===================== RHB Bank & ISLAMIC BANK =====================
def extract_docInfo_1(text, id_bnk, pdf_path_global):
    """
    Extract RHB document-level info (bank header fields).
    Now reads data from coordinate-based JSON extraction.
    """
    logger.logger.info("[rhb_pdf_extraction][extract_docInfo()] : Reading doc info using coordinate JSON extractor")

    try:
        # Run coordinate-based extraction (JSON format)
        json_result = text

        # Parse JSON string into dictionary
        data = json.loads(json_result)

        # Normalize missing or malformed keys
        def safe_get(key, default="NA"):
            return str(data.get(key, default)).strip() if data.get(key) else default

        # Assign fields from JSON
        bank_name = safe_get("Bank Name")
        bank_regNo = safe_get("Bank Registration No")
        bank_address = safe_get("Bank Address")
        customer_name = safe_get("Customer Name")
        cust_address = safe_get("Customer Address")
        # statement_date = safe_get("Statement Date")
        account_number = safe_get("Account Number")

        raw_date = safe_get("Statement Date").strip()
        statement_date = "NA"

        if raw_date:
            try:
                # Try to parse formats like "30 JUNE 2025" or "30 Jun 2025"
                parsed = datetime.strptime(raw_date.title(), "%d %B %Y")
            except ValueError:
                try:
                    parsed = datetime.strptime(raw_date.title(), "%d %b %Y")
                except ValueError:
                    parsed = None

            if parsed:
                statement_date = parsed.strftime("%d/%m/%y")  # ✅ → "30/06/25"

        logger.logger.info(f"[rhb_pdf_extraction][extract_docInfo()] : Successfully extracted via JSON ({bank_name}, {customer_name})")

        return {
            "Bank Name": bank_name,
            "Bank Registration No": bank_regNo,
            "Bank Address": bank_address,
            "Customer Name": customer_name,
            "Customer Address": cust_address,
            "Statement Date": statement_date,
            "Account Number": account_number
        }

    except Exception as e:
        logger.logger.exception(f"[rhb_pdf_extraction][extract_docInfo()] [ERROR]: {e}")

        # Return fallback blank values to prevent crash
        return {
            "Bank Name": "NA",
            "Bank Registration No": "NA",
            "Bank Address": "NA",
            "Customer Name": "NA",
            "Customer Address": "NA",
            "Statement Date": "NA",
            "Account Number": "NA"
        }

# RHB & ISLAMIC TEMPLATE - GENERAL INFO EXTRACTION --------------------------------------------
def extract_docInfo_2(text, id_bnk, pdf_path_global):
    logger.logger.info("[rhb_pdf_extraction][extract_docInfo()] : Executing the RHB pdf file extraction operation, for the general PDF info only")
    output_rawdata(text)

    # 1️⃣ Get Bank Info
    bank_name = "RHB Bank Berhad"
    bank_regNo = 'NA'
    bank_address = 'NA'

    # 🔍 Search for RHB Bank Berhad registration line
    match_reg = re.search(r"RHB\s+Bank\s+Berhad\s*(.+)", text, re.IGNORECASE)
    if match_reg:
        bank_regNo = match_reg.group(1).strip()

    # 2️⃣ Get Customer Info
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    cust_address_lines = []

    customer_name = lines[0].strip().title() if lines else "Unknown Customer"
    for line in lines[1:]:
        upper_line = line.upper()
        if "ACCOUNT STATEMENT / PENYATA AKAUN" in upper_line:
            break
        cust_address_lines.append(line)

    cust_address = " ".join(cust_address_lines).strip() if cust_address_lines else "Unknown Address"

    # 3️⃣ Get General PDF info
    account_number = "Unknown"
    for line in lines:
        digits_only = re.sub(r"\D", "", line)
        if re.fullmatch(r"\d{14}", digits_only):  # exactly 14 digits
            account_number = digits_only
            break

    statement_date = "NA"
    for line in lines:
        if re.search(r"Statement\s+Period|Tempoh\s+Penyata", line, re.IGNORECASE):
            # Example: "Statement Period / Tempoh Penyata : 1 Jul 24 – 31 Jul 24"
            match = re.search(r"(\d{1,2}\s+\w+\s+\d{2,4})\s*[–-]\s*(\d{1,2}\s+\w+\s+\d{2,4})", line)
            if match:
                last_date_str = match.group(2)
                try:
                    parsed = datetime.strptime(last_date_str, "%d %b %y")
                except ValueError:
                    try:
                        parsed = datetime.strptime(last_date_str, "%d %B %y")
                    except ValueError:
                        parsed = None
                if parsed:
                    statement_date = parsed.strftime("%d/%m/%y")
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

# RHB & RHB ISLAMIC  BANK TEMPLATE - TRANSACTION EXTRACTION --------------------------------------------
def extract_trxInfo_1(text, id_bnk, pdf_path_global):
    """
    Extract RHB transaction data from coordinate-based JSON (rhb_xy_extraction).
    Converts JSON rows into standardized transaction dictionaries.
    """
    logger.logger.info("[rhb_pdf_extraction][extract_trxInfo()] : Reading transaction info via coordinate JSON extractor")
    # output_rawdata(text)

    transactions = []

    try:
        # Run coordinate-based transaction extraction (returns JSON string)
        json_result = text

        # Parse JSON string → Python list of dictionaries
        data = json.loads(json_result)

        for row in data:
            # Safely extract fields with fallback
            def safe_get(field, default=""):
                val = row.get(field, default)
                if isinstance(val, str):
                    return val.strip()
                return str(val)

            date_val = safe_get("Date")
            cr_raw = safe_get("AmountCR")
            dr_raw = safe_get("AmountDR")
            bal_raw = safe_get("Balance")
            description = safe_get("Description")
            desc_others_parts = [
                re.sub(r"(DISTRIBUTO)([A-Z0-9])", r"\1 \2", safe_get("Sender")),
                safe_get("Ref1"),
                safe_get("Ref2")
            ]
            desc_others = " ".join(p for p in desc_others_parts if p).strip()

            # Convert numeric strings → float (if valid)
            def to_float(val):
                try:
                    return float(val.replace(",", "").replace("+", "").replace("-", ""))
                except Exception:
                    return 0.0

            cr_val = to_float(cr_raw)
            dr_val = to_float(dr_raw)
            bal_val = to_float(bal_raw)

            # Perform simple NER if needed (can enhance later)
            full_desc = f"{description} {desc_others}".strip()
            # ner = NER_extraction(full_desc) or ""
            if safe_get("Sender"):
                ner = safe_get("Sender")
            else:
                ner = " ".join(p for p in [safe_get("Ref1"), safe_get("Ref2")] if p).strip()

            # 🧩 [ SPECIAL hanlde ] Remove everything directly attached after 'DISTRIBUTO'
            ner = re.sub(r"DISTRIBUTO\S*", "DISTRIBUTO", ner)

            # Optional cleanup for multiple spaces
            ner = re.sub(r"\s{2,}", " ", ner).strip()

            transactions.append({
                "trn_pdf_date": date_val,
                "trn_pdf_description": description,
                "trn_pdf_description_others": desc_others,
                "trn_pdf_CR_Amount": cr_val,
                "trn_pdf_DR_Amount": dr_val,
                "trn_pdf_statementBalance": bal_val,
                "trn_pdf_ner": ner
            })

        logger.logger.info(f"[rhb_pdf_extraction][extract_trxInfo()] : Extracted {len(transactions)} transactions via JSON.")

    except Exception as e:
        logger.logger.exception(f"[rhb_pdf_extraction][extract_trxInfo()][ERROR]: {e}")

    return transactions

def extract_trxInfo_2(text, id_bnk, pdf_path_global):
    logger.logger.info("[rhb_pdf_extraction][extract_trxInfo()] : Executing the RHB pdf file extraction operation, for the transaction(s) data only")
    # output_rawdata(text)

    # To store the opening balance, for DR & CR identification later. 
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    first_balance = None
    for i, line in enumerate(lines):
        if "B/F BALANCE" in line.upper():
            # the next numeric line is the balance
            for j in range(i + 1, len(lines)):
                clean_val = lines[j].strip().replace(",", "")
                if clean_val.endswith("-"):
                    clean_val = clean_val[:-1]  # remove trailing minus before matching
                if re.match(r"^\d+\.\d{2}$", clean_val):
                    first_balance = float(clean_val)
                    break
            break
    # To get the year of statement date, as the transaction do not provide the year value
    statement_year = None
    for line in lines:
        if re.search(r"Statement\s+Period|Tempoh\s+Penyata", line, re.IGNORECASE):
            # Example: "Statement Period / Tempoh Penyata : 1 Jul 24 – 31 Jul 24"
            match = re.search(r"(\d{1,2}\s+\w+\s+(\d{2,4}))\s*[–-]\s*(\d{1,2}\s+\w+\s+(\d{2,4}))", line)
            if match:
                # take year from last date
                last_date_str = match.group(3)
                try:
                    parsed = datetime.strptime(last_date_str, "%d %b %y")
                except ValueError:
                    try:
                        parsed = datetime.strptime(last_date_str, "%d %B %y")
                    except ValueError:
                        try:
                            parsed = datetime.strptime(last_date_str, "%d %b %Y")
                        except ValueError:
                            parsed = None
                if parsed:
                    statement_year = parsed.year
            break

    # 1️⃣ Perform pre-cleaning (Step 1) in the text to remove unnecessary text
    lines = text.split("\n")
    cleaned_lines = []

    firstTextinPage = lines[0] if lines else ""
    skip = True
    startInNext = False

    for line in lines:
        upper_line = line.upper().strip()

        if "B/F BALANCE" in upper_line:
            startInNext = True
            continue

        if startInNext == True and skip == True:
            skip = False
            continue

        if not skip:
            cleaned_lines.append(line.strip())

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)
    # output_rawdata(textCleaned)

    # 2️⃣ Perform pre-cleaning (Step 2) in the text to remove unnecessary text
    lines = textCleaned.split("\n")
    cleaned_lines = []
    skip = False

    for i, line in enumerate(lines):
        current = line.strip()
        if not current:
            continue  # ⛔ skip blank lines

        previous = lines[i - 1].strip() if i > 0 else ""

        if current == firstTextinPage:
            skip = True
        elif previous == "Balance" and current == "Baki":
            skip = False
            continue  # optional: skip the "Baki" line itself

        if not skip:
            cleaned_lines.append(current)

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)
    # output_rawdata(textCleaned)

    # 3️⃣ Perform pre-cleaning (Step 3) in the text to remove unnecessary text
    lines = textCleaned.split("\n")
    cleaned_lines = []
    skip = False

    for i, line in enumerate(lines):
        current = line.strip()
        if not current:
            continue  # skip blank lines

        next_line = lines[i + 1].strip().upper() if i + 1 < len(lines) else ""

        # 🔹 If next line contains "C/F BALANCE", skip current & start skipping
        if "C/F BALANCE" in next_line:
            skip = True
            continue

        if skip:
            # You can decide when to stop skipping later if needed
            continue

        cleaned_lines.append(current)

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)
    # output_rawdata(textCleaned)

    # Group transactions by date pattern (e.g., 02 Jul, 05 Jul, etc.)
    lines = textCleaned.split("\n")
    transactions = []
    current_block = []
    date_pattern = re.compile(r"^\d{1,2}\s+[A-Za-z]{3,}$")

    for line in lines:
        if date_pattern.match(line):
            if current_block:
                transactions.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        transactions.append(current_block)

    # Parse each transaction block into structured fields
    structured_trx = []
    prev_balance = first_balance

    for block in transactions:
        date = block[0]
        description = block[1] if len(block) > 1 else ""
        # Extract numeric-like lines (amount + balance)
        numbers = []
        for ln in block:
            if re.match(r"^[\d,]+\.\d{2}-?$", ln.strip()):  # match values like 27,764.33 or 27,764.33-
                clean_val = ln.strip().replace(",", "")
                if clean_val.endswith("-"):
                    clean_val = clean_val[:-1]  # remove trailing minus
                numbers.append(clean_val)

        if len(numbers) >= 2:
            amount = float(numbers[0])
            balance = float(numbers[1])
        else:
            continue

        # Determine CR / DR
        if prev_balance is not None:
            if balance <= prev_balance:
                amount_cr = amount
                amount_dr = 0.0
            else:
                amount_cr = 0.0
                amount_dr = amount
        else:
            amount_cr = 0.0
            amount_dr = 0.0

        # 🔹 Collect description-others (everything between current date and before next date,
        #     excluding description line and numeric lines)
        desc_others_parts = []
        numeric_10digit = None  # store the 10-digit numeric if found

        for ln in block[2:]:  # start after description
            val = ln.strip()
            if not val:
                continue

            # Remove trailing "-" if present
            if val.endswith("-"):
                val = val[:-1].strip()

            # Detect 10-digit numeric (keep for end)
            if re.fullmatch(r"\d{10}", val):
                numeric_10digit = val
                continue

            # Skip pure amount (e.g., 27,764.33)
            if re.match(r"^[\d,]+\.\d{2}$", val):
                continue

            # Skip if same as description
            if val == description.strip():
                continue

            desc_others_parts.append(val)

        # Append the 10-digit numeric value (if found) to the end
        if numeric_10digit:
            desc_others_parts.append(numeric_10digit)

        description_others = " ".join(desc_others_parts).strip()

        # NER extraction
        ner = NER_extraction(description + " " + description_others) or ""

        structured_trx.append({
            "trn_pdf_date": datetime.strptime(f"{date} {statement_year}", "%d %b %Y").strftime("%d/%m/%y") if statement_year else date,
            "trn_pdf_description": description,
            "trn_pdf_description_others": description_others,
            "trn_pdf_CR_Amount": amount_cr,
            "trn_pdf_DR_Amount": amount_dr,
            "trn_pdf_statementBalance": balance,
            "trn_pdf_ner": ner
        })

        prev_balance = balance

    logger.logger.info(f"[rhb_pdf_extraction] : Extracted total records = {len(structured_trx)} transactions")
    return structured_trx
