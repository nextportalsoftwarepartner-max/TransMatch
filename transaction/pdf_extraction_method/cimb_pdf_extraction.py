# flake8: noqa: E501
from datetime import datetime
import re
import logger
import fitz  # type: ignore # PyMuPDF
from transaction.name_extractor import NER_extraction

# ===================== CIMB Bank & ISLAMIC BANK =====================
# CIMB & ISLAMIC TEMPLATE - GENERAL INFO EXTRACTION --------------------------------------------
def extract_docInfo(text, id_bnk):
    logger.logger.info("[cimb_pdf_extraction][extract_docInfo()] : Executing the CIMB BANK pdf file extraction operation, for the general PDF info only")

    # 1️⃣ Bank Name
    if id_bnk == 5:
        bank_name = "CIMB Islamic Bank Berhad"
    else:
        # CIMB Click do not provide bank address, regno. therefore to set default value
        bank_name = "CIMB Bank Berhad"
        bank_reg_no = 'NA'
        bank_address = 'NA'
        customer_address = 'NA'

    # 2️⃣ Bank Registration Number
    clean_text = text.replace("\n", " ")
    clean_text = clean_text.replace("\xa0", " ")
    clean_text = re.sub(r"\s+", " ", clean_text)

    # 4️⃣ Customer Name
    cust_name_match = re.search(
        r"Account\s+Holder\s+([A-Z\s]+?)\s+Account\s+Details",
        clean_text,
        re.IGNORECASE
    )
    customer_name = cust_name_match.group(1).strip(
    ).title() if cust_name_match else "Unknown Customer"

    # 6️⃣ Statement Date
    statement_date_match = re.search(
        r"Account\s+Details\s+as\s+at\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})\s+\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)",
        text,
        re.IGNORECASE
    )
    if statement_date_match:
        raw_date = statement_date_match.group(1)  # e.g. "18 Mar 2025"
        try:
            parsed_date = datetime.strptime(raw_date, "%d %b %Y")
            statement_date = parsed_date.strftime("%d/%m/%y")  # → "18/03/25"
        except ValueError:
            statement_date = "Invalid Date"
    else:
        statement_date = "Invalid Date"

    # 7️⃣ Account Number
    acct_no_match = re.search(
        r"ACCOUNT\s+SAVINGS[^\d]*(\d[\d\s]+)",
        text,
        re.IGNORECASE
    )
    if acct_no_match:
        account_number = acct_no_match.group(1)
        account_number = account_number.replace(
            " ", "").replace("\n", "").strip()
    else:
        account_number = "Unknown"

    return {
        "Bank Name": bank_name,
        "Bank Registration No": bank_reg_no,
        "Bank Address": bank_address,
        "Customer Name": customer_name,
        "Customer Address": customer_address,
        "Statement Date": statement_date,
        "Account Number": account_number
    }


def extract_trxInfo(text, id_bnk):
    logger.logger.info("[cimb_pdf_extraction][extract_trxInfo()] : Executing CIMB extraction with x-coordinate logic")
    all_lines = text.split("\n")
    # ✅ Perform pre-cleaning session ########################

    # ✅ Remove lines with only 1 space
    cleaned_lines = []
    skip = False
    for line in all_lines:
        if "Account Details" in line.upper():
            continue
        if line == " ":
            continue
        cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned = "\n".join(cleaned_lines)
    textCleaned2 = textCleaned.split("\n")

    # ✅ Remove headers
    cleaned_lines = []
    skip = False
    for line in textCleaned2:
        if "ACCOUNT DETAILS AND TRANSACTION HISTORY" in line.upper():
            skip = True  # Start skipping
        elif "BALANCE" == line.upper():
            skip = False  # Stop skipping
            continue  # Optionally skip the marker line too

        if not skip:
            cleaned_lines.append(line)

    # Rejoin cleaned text for further processing
    textCleaned2 = "\n".join(cleaned_lines)
    print(textCleaned2)

    # all_lines = text.split("\n")

    # # Perform pre-cleaning (Step 1) in the text to remove unnecessary text
    # cleaned_lines = []
    # PB_SEQ = all_lines[0].strip()
    # skip = False
    # for i, line in enumerate(all_lines):
    #     # prev_line = all_lines[i - 1].strip().upper() if i - 1 >= 0 else ""

    #     if PB_SEQ == line.upper():
    #         skip = True  # Start skipping
    #     elif "BALANCE FROM LAST STATEMENT" in line.upper():
    #         skip = False  # Stop skipping
    #         # continue  # Optionally skip the marker line too

    #     if not skip:
    #         cleaned_lines.append(line)

    # # Rejoin cleaned text for further processing
    # textCleaned = "\n".join(cleaned_lines)

    # # Perform pre-cleaning (Step 2) in the text to remove unnecessary text
    # cleaned_lines = []
    # textSplit = textCleaned.split("\n")

    # skip = False
    # for i, line in enumerate(textSplit):
    #     next_line = textSplit[i + 1].strip().upper() if i + \
    #         1 < len(textSplit) else ""

    #     if "BALANCE C/F" in line.upper():
    #         skip = True  # Start skipping
    #     elif "BALANCE B/F" in next_line:
    #         skip = False  # Stop skipping

    #     if not skip:
    #         cleaned_lines.append(line)

    # # Rejoin cleaned text for further processing
    # textCleaned2 = "\n".join(cleaned_lines)

    # # Perform pre-cleaning (Step 3) in the text to remove unnecessary text
    # cleaned_lines = []
    # textSplit = textCleaned2.split("\n")

    # skip = False
    # for i, line in enumerate(textSplit):
    #     prev_line = textSplit[i - 1].strip().upper() if i - 1 >= 0 else ""
    #     next_line = textSplit[i + 1].strip().upper() if i + \
    #         1 < len(textSplit) else ""

    #     if "BALANCE B/F" in next_line:
    #         skip = True  # Start skipping
    #     elif "BALANCE B/F" in prev_line:
    #         skip = False  # Stop skipping
    #         continue  # Optionally skip the marker line too

    #     if not skip:
    #         cleaned_lines.append(line)

    # # Rejoin cleaned text for further processing
    # textCleaned3 = "\n".join(cleaned_lines)

    # # Perform pre-cleaning (Step 4) in the text to remove unnecessary text
    # cleaned_lines = []
    # textSplit = textCleaned3.split("\n")

    # skip = False
    # for i, line in enumerate(textSplit):
    #     if "CLOSING BALANCE IN THIS STATEMENT" in line.upper():
    #         skip = True  # Start skipping

    #     if not skip:
    #         cleaned_lines.append(line)

    # # Rejoin cleaned text for further processing
    # textCleaned4 = "\n".join(cleaned_lines)
    # textSplit4 = textCleaned4.split("\n")
    # textAppend = []

    # for seqNum, line in enumerate(textSplit4, start=1):  # Start from 1
    #     # if re.match(r"\d{2}/\d{2}", line):  # Check if "line" starts with a date (DD/MM)
    #     # Check if "line" starts with a date and only exact DD/MM
    #     if re.match(r"^\d{2}/\d{2}$", line.strip()):
    #         # Add re.match(r"^\d{2}/\d{2}$", line.strip())sequence number with %
    #         textAppend.append(f"%% {line}")
    #     else:
    #         # textAppend.append(line)  # Keep line unchanged
    #         # Check previous line (index seqNum - 2 due to start=1)
    #         if seqNum >= 2:
    #             prev_line = textSplit4[seqNum - 2]
    #             if re.match(r"^\d{2}/\d{2}$", prev_line) or (is_two_decimal_numeric(line) and not is_two_decimal_numeric(prev_line)):
    #                 textAppend.append(f"## {line}")
    #             else:
    #                 textAppend.append(f"#@ {line}")

    # textJoin = " ".join(textAppend)  # Joins with a space
    # textSplitTran = textJoin.split("%%")

    # # Parsed result list
    # split_transactions = []
    # compare_balance = None

    # for idx, line in enumerate(textSplitTran):
    #     line = line.strip()
    #     if not line:
    #         continue

    #     if idx == 0:
    #         compare_balance = float(line.replace(
    #             "##", "").replace(",", "").strip())
    #         continue

    #     parts = line.split("##")
    #     date = parts[0].strip().split()[0] if parts[0].strip() else "Unknown"

    #     for trx in parts[1:]:
    #         trx_cleaned = trx.strip()
    #         if trx_cleaned:
    #             fields = [p.strip() for p in trx_cleaned.split("#@")]

    #             amount = float(fields[0].replace(",", "")
    #                            ) if len(fields) > 0 else 0.0
    #             statement_balance = float(fields[1].replace(
    #                 ",", "")) if len(fields) > 1 else 0.0
    #             description = fields[2] if len(fields) > 2 else ""
    #             description_others = " ".join(
    #                 fields[3:]) if len(fields) > 3 else ""

    #             if compare_balance is not None:
    #                 if statement_balance < compare_balance:
    #                     debit = amount
    #                     credit = 0.0
    #                 else:
    #                     credit = amount
    #                     debit = 0.0
    #             else:
    #                 debit = credit = 0.0

    #             full_desc = description + " " + description_others
    #             ner_name = NER_extract_name(full_desc)

    #             split_transactions.append({
    #                 "trn_pdf_date": date,
    #                 "trn_pdf_statementBalance": statement_balance,
    #                 "trn_pdf_DR_Amount": debit,
    #                 "trn_pdf_CR_Amount": credit,
    #                 "trn_pdf_description": description,
    #                 "trn_pdf_description_others": description_others,
    #                 "trn_pdf_ner": ner_name if ner_name else ""
    #             })

    #             compare_balance = statement_balance
    # return split_transactions