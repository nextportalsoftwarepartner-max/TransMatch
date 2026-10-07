# flake8: noqa: E501
from datetime import datetime
import re
import logger
from transaction.name_extractor import NER_extract_name


def is_two_decimal_numeric(val):
    clean = val.replace(",", "").strip()
    return re.match(r"^\d+\.\d{2}$", clean) is not None

# ===================== Public Bank & ISLAMIC BANK =====================
# PUBLIC BANK TEMPLATE - GENERAL INFO EXTRACTION --------------------------------------------
def extract_docInfo(text, identified_bank, pdf_path_global):
    logger.logger.info("[pbb_pdf_extraction] : Executing the PUBLIC BANK pdf file extraction operation, for the general PDF info only")

    # Define variables
    all_lines = text.split("\n")
    bankAddr_lines_final = []
    cust_lines_final = []
    bankAddr_collect = False

    # Extract Bank Name & Bank Reg & Bank Address
    bank_name = "Public Bank"
    # Registration number not found in the public bank PDF template, default to empty value
    bank_regNo = "N/A"

    for line in all_lines:
        line_upper = line.upper()

        if identified_bank == 1:
            if "CALL 03-2170 8000 OR VISIT OUR WEBSITE" in line_upper:
                bankAddr_collect = True
                continue  # Skip this line, start from next
        elif identified_bank == 2:
            if "T&C APPLY" in line_upper:
                bankAddr_collect = True
                continue  # Skip this line, start from next

        if "TEL:" in line_upper:
            break  # Stop collecting when you reach this line

        if bankAddr_collect:
            bankAddr_lines_final.append(line.strip())

    # Rejoin cleaned text for further processing
    bank_address = " ".join(bankAddr_lines_final)

    # Assign customer name
    customer_name = all_lines[1].strip() if len(
        all_lines) > 1 else "Unknown Customer"

    # Assign customer address
    for i, line in enumerate(all_lines):
        if i < 2:
            continue  # Skip lines before line 2

        line_upper = line.upper()

        if "." in line_upper:
            break  # Stop collecting after this line

        cust_lines_final.append(line.strip())

    # Rejoin cleaned text for final address block
    cust_address = " ".join(cust_lines_final)

    # Assign statement_date
    for i, line in enumerate(all_lines):
        if "STATEMENT DATE" in line.upper():
            statement_date_raw = all_lines[i + 1].strip()
            try:
                parsed_date = datetime.strptime(statement_date_raw, "%d %b %Y")
                statement_date = parsed_date.strftime("%d/%m/%y")  # → 31/08/24
            except ValueError:
                statement_date = "Invalid Date"
            break  # Stop after capturing it

    # Assign account number
    for i, line in enumerate(all_lines):
        if "ACCOUNT NUMBER" in line.upper():
            if i + 1 < len(all_lines):
                account_number = all_lines[i + 1].strip()
                print("account_number = " + account_number)
            break  # Done after first match

    # Final - Return all assigned value back to caller
    return {
        "Bank Name": bank_name,
        "Bank Registration No": bank_regNo,
        "Bank Address": bank_address,
        "Customer Name": customer_name,
        "Customer Address": cust_address,
        "Statement Date": statement_date,
        "Account Number": account_number
    }


# PUBLIC BANK TEMPLATE - TRANSACTION EXTRACTION --------------------------------------------
def extract_trxInfo(text, identified_bank, pdf_path_global):
    logger.logger.info("[pbb_pdf_extraction] : Executing the PUBLIC BANK pdf file extraction operation, for the transaction(s) data only")

    all_lines = text.split("\n")

    # Perform pre-cleaning (Step 1) in the text to remove unnecessary text
    cleaned_lines = []
    PB_SEQ = all_lines[0].strip()
    skip = False
    for i, line in enumerate(all_lines):
        # prev_line = all_lines[i - 1].strip().upper() if i - 1 >= 0 else ""

        if PB_SEQ == line.upper():
            skip = True  # Start skipping
        elif "BALANCE FROM LAST STATEMENT" in line.upper():
            skip = False  # Stop skipping
            # continue  # Optionally skip the marker line too

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)

    # Perform pre-cleaning (Step 2) in the text to remove unnecessary text
    cleaned_lines = []
    textSplit = textCleaned.split("\n")

    skip = False
    for i, line in enumerate(textSplit):
        next_line = textSplit[i + 1].strip().upper() if i + \
            1 < len(textSplit) else ""

        if "BALANCE C/F" in line.upper():
            skip = True  # Start skipping
        elif "BALANCE B/F" in next_line:
            skip = False  # Stop skipping

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned2 = "\n".join(cleaned_lines)

    # Perform pre-cleaning (Step 3) in the text to remove unnecessary text
    cleaned_lines = []
    textSplit = textCleaned2.split("\n")

    skip = False
    for i, line in enumerate(textSplit):
        prev_line = textSplit[i - 1].strip().upper() if i - 1 >= 0 else ""
        next_line = textSplit[i + 1].strip().upper() if i + \
            1 < len(textSplit) else ""

        if "BALANCE B/F" in next_line:
            skip = True  # Start skipping
        elif "BALANCE B/F" in prev_line:
            skip = False  # Stop skipping
            continue  # Optionally skip the marker line too

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned3 = "\n".join(cleaned_lines)

    # Perform pre-cleaning (Step 4) in the text to remove unnecessary text
    cleaned_lines = []
    textSplit = textCleaned3.split("\n")

    skip = False
    for i, line in enumerate(textSplit):
        if "CLOSING BALANCE IN THIS STATEMENT" in line.upper():
            skip = True  # Start skipping

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned4 = "\n".join(cleaned_lines)
    textSplit4 = textCleaned4.split("\n")
    textAppend = []

    for seqNum, line in enumerate(textSplit4, start=1):  # Start from 1
        # if re.match(r"\d{2}/\d{2}", line):  # Check if "line" starts with a date (DD/MM)
        # Check if "line" starts with a date and only exact DD/MM
        if re.match(r"^\d{2}/\d{2}$", line.strip()):
            # Add re.match(r"^\d{2}/\d{2}$", line.strip())sequence number with %
            textAppend.append(f"%% {line}")
        else:
            # textAppend.append(line)  # Keep line unchanged
            # Check previous line (index seqNum - 2 due to start=1)
            if seqNum >= 2:
                prev_line = textSplit4[seqNum - 2]
                if re.match(r"^\d{2}/\d{2}$", prev_line) or (is_two_decimal_numeric(line) and not is_two_decimal_numeric(prev_line)):
                    textAppend.append(f"## {line}")
                else:
                    textAppend.append(f"#@ {line}")

    textJoin = " ".join(textAppend)  # Joins with a space
    textSplitTran = textJoin.split("%%")

    # Parsed result list
    split_transactions = []
    compare_balance = None

    for idx, line in enumerate(textSplitTran):
        line = line.strip()
        if not line:
            continue

        if idx == 0:
            compare_balance = float(line.replace(
                "##", "").replace(",", "").strip())
            continue

        parts = line.split("##")
        date = parts[0].strip().split()[0] if parts[0].strip() else "Unknown"

        for trx in parts[1:]:
            trx_cleaned = trx.strip()
            if trx_cleaned:
                fields = [p.strip() for p in trx_cleaned.split("#@")]

                amount = float(fields[0].replace(",", "")
                               ) if len(fields) > 0 else 0.0
                statement_balance = float(fields[1].replace(
                    ",", "")) if len(fields) > 1 else 0.0
                description = fields[2] if len(fields) > 2 else ""
                description_others = " ".join(
                    fields[3:]) if len(fields) > 3 else ""

                if compare_balance is not None:
                    if statement_balance < compare_balance:
                        debit = amount
                        credit = 0.0
                    else:
                        credit = amount
                        debit = 0.0
                else:
                    debit = credit = 0.0

                full_desc = description + " " + description_others
                ner_name = NER_extract_name(full_desc)

                split_transactions.append({
                    "trn_pdf_date": date,
                    "trn_pdf_statementBalance": statement_balance,
                    "trn_pdf_DR_Amount": debit,
                    "trn_pdf_CR_Amount": credit,
                    "trn_pdf_description": description,
                    "trn_pdf_description_others": description_others,
                    "trn_pdf_ner": ner_name if ner_name else ""
                })

                compare_balance = statement_balance
    return split_transactions
# Sub Process - Differentiate the caller by detected bank name ---------------------------------------