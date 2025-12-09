# flake8: noqa: E501
import re
import logger
from transaction.name_extractor import NER_extract_name

# ===================== MAYBANK & ISLAMIC BANK =====================
# MAYBANK & ISLAMIC TEMPLATE - GENERAL INFO EXTRACTION --------------------------------------------
def extract_docInfo(text, identified_bank, pdf_path_global):
    logger.logger.info("[mbb_pdf_extraction] : Executing the MAYBANK pdf file extraction operation, for the general PDF info only")
    # logger.logger.info(f"[mbb_pdf_extraction] : text = {text}")

    # Extract Bank Name & Address
    bank_name_match = re.search(
        r"((?:\b[A-Za-z]+\s+)?(?:Bank|Berhad|Islamic)[A-Za-z\s]*)", text)

    bank_name = bank_name_match.group(
        1).strip() if bank_name_match else "Unknown Bank"

    if bank_name_match:
        start_index = text.find(bank_name_match.group(1))

        # ✅ Split and remove unnecessary spaces
        lines = re.split(r"\n\s*", text[start_index:])

        # ✅ Extract the correct lines (ensure there are enough lines)
        bank_regNo = lines[0].strip() if len(lines) > 0 else "Not Found"
        bank_address = lines[1].strip() if len(lines) > 1 else "Not Found"
    else:
        bank_regNo = "Not Found"
        bank_address = "Not Found"

    # Extract Customer Name & Address
    # 1. Try to extract using "MR / ENCIK"
    customer_match = re.search(r"(MR / ENCIK [^\n]+)", text)
    if customer_match:
        customer_name = customer_match.group(1).strip()
    else:
        # 2. Fallback: get 3rd line after "Maybank Islamic Berhad"
        customer_name = "Unknown Customer"
        for i, line in enumerate(lines):
            if "Maybank Islamic Berhad" in line:
                target_idx = i + 3
                if target_idx < len(lines):
                    candidate = lines[target_idx].strip()
                    if candidate:
                        customer_name = candidate
                break

    # Extract Customer Address - Search from text
    if customer_match:
        # === Case 1: Contains "MR / ENCIK"
        start_index = text.find(customer_match.group(1))
        address_lines = text[start_index:].split("\n")[1:5]
        cust_address_lst = [line.strip()
                            for line in address_lines if line.strip()]
    else:
        # === Case 2: No "MR / ENCIK" – fallback to Maybank-based block
        cust_address_lst = []
        lines = text.split("\n")
        start = end = -1

        # Step 1: Find line containing "Maybank Islamic Berhad"
        for i, line in enumerate(lines):
            if "Maybank Islamic Berhad" in line:
                start = i + 4  # jump to 4th line after
                break

        # Step 2: From start, find the line containing "MUKA"
        for j in range(start, len(lines)):
            if "MUKA" in lines[j].upper():  # ensure case insensitive
                end = j
                break

        # Step 3: Extract lines between start and end
        if 0 <= start < end:
            cust_address_lst = [lines[k].strip()
                                for k in range(start, end) if lines[k].strip()]
        else:
            cust_address_lst = ["Not Found"] * 4

    # Extract Customer Address - Join and Finalize Customer Address
    cust_address = " ".join(cust_address_lst)

    # Extract Statement Date & Account Number
    statement_date_match = re.search(
        r"STATEMENT DATE\s*:\s*(\d{2}/\d{2}/\d{2})", text)
    statement_date = statement_date_match.group(
        1) if statement_date_match else "Unknown"

    # account_number_match = re.search(r"ACCOUNT\s*NUMBER\s*:\s*(\d+)", text)
    account_number_match = re.search(r"ACCOUNT\s*NUMBER\s*:\s*([\d\-]+)", text)
    account_number = account_number_match.group(1).replace(
        "-", "") if account_number_match else "Unknown"

    return {
        "Bank Name": bank_name,
        "Bank Registration No": bank_regNo,
        "Bank Address": bank_address,
        "Customer Name": customer_name,
        "Customer Address": cust_address,
        "Statement Date": statement_date,
        "Account Number": account_number
    }

# MAYBANK & ISLAMIC  BANK TEMPLATE - TRANSACTION EXTRACTION --------------------------------------------
def extract_trxInfo(text, identified_bank, pdf_path_global):
    logger.logger.info("[mbb_pdf_extraction] : Executing the MAYBANK pdf file extraction operation, for the transaction(s) data only")

    # Perform pre-cleaning (Step 1) in the text to remove unnecessary text
    lines = text.split("\n")
    cleaned_lines = []

    skip = False
    for line in lines:
        if "MAYBANK ISLAMIC BERHAD" in line.upper():
            skip = True  # Start skipping
        elif "URUSNIAGA AKAUN" in line.upper():
            skip = False  # Stop skipping
            continue  # Optionally skip the marker line too

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)

    # Perform pre-cleaning (Step 2) in the text to remove unnecessary text
    lines = textCleaned.split("\n")
    cleaned_lines = []

    skip = False
    for line in lines:
        if "TARIKH MASUK" in line.upper():
            skip = True  # Start skipping
        elif "STATEMENT BALANCE" in line.upper():
            skip = False  # Stop skipping
            continue  # Optionally skip the marker line too

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned2 = "\n".join(cleaned_lines)

    # Perform pre-cleaning (Step 2) in the text to remove unnecessary text
    lines = textCleaned2.split("\n")
    cleaned_lines = []

    skip = False
    for line in lines:
        if "ENDING BALANCE :" in line.upper():
            skip = True  # Start skipping

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned3 = "\n".join(cleaned_lines)
    textSplit = textCleaned3.split("\n")
    textAppend = []

    # for seqNum, line in enumerate(textSplit, start=1):  # Start from 1
    for seqNum, line in enumerate(textSplit, start=1):  # Start from 1
        # if re.match(r"^\d{2}/\d{2}(/\d{2})?$", line.strip()): # Check if "line" starts with a date (DD/MM) / (DD/MM/YY)
        if re.match(r"\d{2}/\d{2}", line):  # Check if "line" starts with a date (DD/MM)
            textAppend.append(f"%% {line}")  # Add sequence number with %
        else:
            textAppend.append(line)  # Keep line unchanged

    textJoin = " ".join(textAppend)  # Joins with a space
    textSplitTran = textJoin.split("%%")

    # Filter out items that don't start with a valid date (DD/MM)
    filteredText = [
        # Ensures MMYY format with space
        # item for item in textSplitTran if re.match(r"\s*\d{2}/\d{2}\s", item)
        item for item in textSplitTran if re.match(r"\s*\d{2}/\d{2}(/\d{2})?\s", item)
    ]

    # Define storage list
    transactions = []

    for item in filteredText:
        # match = re.match(pattern, item)

        # Attempt to match full 6-part pattern
        # pattern_full = r"\s*(\d{2}/\d{2})\s+(.+?)\s+([\d,]+(?:\.\d{2})?)([-+]?)\s+([\d,]+(?:\.\d{2})?)\s+(.+)"
        pattern_full = r"\s*(\d{2}/\d{2}(?:/\d{2})?)\s+(.+?)\s+([\d,]+(?:\.\d{2})?)([-+]?)\s+([\d,]+(?:\.\d{2})?)\s+(.+)"
        match = re.match(pattern_full, item)

        if not match:
            # Try fallback 5-part pattern (without trailing desc_others)
            # pattern_short = r"\s*(\d{2}/\d{2})\s+(.+?)\s+([\d,]+(?:\.\d{2})?)([-+]?)\s+([\d,]+(?:\.\d{2})?)"
            pattern_short = r"\s*(\d{2}/\d{2}(?:/\d{2})?)\s+(.+?)\s+([\d,]+(?:\.\d{2})?)([-+]?)\s+([\d,]+(?:\.\d{2})?)"
            match = re.match(pattern_short, item)

        if match:
            date = match.group(1)
            description = match.group(2).strip()
            amount = match.group(3)
            amountInd = match.group(4) if match.group(4) else "NULL"
            statementBalance = match.group(5)
            description_others = match.group(
                6).strip() if len(match.groups()) >= 6 else ""

            full_desc = description + " " + description_others
            ner_name = NER_extract_name(full_desc)

            transactions.append({
                "trn_pdf_date": date,
                "trn_pdf_description": description,
                "trn_pdf_CR_Amount": float(amount.replace(",", "")) if amountInd == "+" else 0,
                "trn_pdf_DR_Amount": float(amount.replace(",", "")) if amountInd == "-" else 0,
                "trn_pdf_statementBalance": float(statementBalance.replace(",", "")),
                "trn_pdf_description_others": description_others,
                "trn_pdf_ner": ner_name if ner_name else ""
            })

    return transactions
