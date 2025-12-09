# flake8: noqa: E501
from datetime import datetime
import re
import logger
import fitz  # type: ignore # PyMuPDF
from transaction.name_extractor import NER_extraction

# ===================== HongLeong Bank & ISLAMIC BANK =====================
# Hong Leong & ISLAMIC TEMPLATE - GENERAL INFO EXTRACTION --------------------------------------------
def extract_docInfo(text, identified_bank, pdf_path_global):
    logger.logger.info("[hlb_pdf_extraction][extract_docInfo()] : Executing the HONG LEONG BANK pdf file extraction operation, for the general PDF info only")

    # 1. Extract Bank Name
    # bank_name_match = re.search(r"(Hong\s+Leong\s+Bank(?:\s+Berhad)?(?:\s*\([\d\-Xx]+\))?)", text, re.IGNORECASE)
    # bank_name = bank_name_match.group(1).strip() if bank_name_match else "Unknown Bank"
    if identified_bank == 9:
        bank_name = "Hong Leong Islamic Bank Berhad"
    else:
        bank_name = "Hong Leong Bank Berhad"

    # 2. Extract Bank Registration Number (from within parentheses)
    clean_text = text.replace("\n", " ")
    clean_text = clean_text.replace("\xa0", " ")  # replace non-breaking space
    # collapse multiple spaces into one
    clean_text = re.sub(r"\s+", " ", clean_text)

    if identified_bank == 9:
        bank_reg_match = re.search(
            r"Hong\s+Leong\s+Islamic\s+Bank\s+Berhad\s*\(([\d\-Xx]+)\)\s+", text, re.IGNORECASE)
    else:
        bank_reg_match = re.search(
            r"Hong\s+Leong\s+Bank\s+Berhad\s*\(([\d\-Xx]+)\)", text, re.IGNORECASE)

    bank_reg_no = bank_reg_match.group(1) if bank_reg_match else "Not Found"

    # 3. Extract Bank Address
    branch_match = re.search(r"Branch\s*/\s*Cawangan\s*:\s*(.+)", text)
    tel_match = re.search(r"Tel No\s*/\s*No Tel\s*:\s*(.+)", text)
    bank_address = f"{branch_match.group(1).strip()} ({tel_match.group(1).strip()})" if branch_match and tel_match else "Not Found"

    # 4. Extract Customer Name
    customer_name_match = re.search(
        r"(?<=\n)([A-Z][A-Z\s]+)\nDate\s*/\s*Tarikh", text)
    customer_name = customer_name_match.group(1).strip(
    ).title() if customer_name_match else "Unknown Customer"

    # 5. Extract Customer Address
    address_lines = re.findall(
        r"Date\s*/\s*Tarikh\s*:\s*[^\n]+\n(.+?)\nA/C No", text, re.DOTALL)
    customer_address = " ".join(line.strip() for line in address_lines[0].split(
        "\n") if line.strip()) if address_lines else "Not Found"

    # 6. Extract Statement Date
    statement_date_match = re.search(
        r"Date\s*/\s*Tarikh\s*:\s*(\d{2}-\d{2}-\d{4})", text)
    statement_date = statement_date_match.group(1).replace(
        "-", "/") if statement_date_match else "Unknown"

    # 7. Extract Account Number
    acct_no_match = re.search(r"A/C No\s*/\s*No Akaun\s*:\s*([\d\-]+)", text)
    account_number = acct_no_match.group(1).replace(
        "-", "") if acct_no_match else "Unknown"

    return {
        "Bank Name": bank_name,
        "Bank Registration No": bank_reg_no,
        "Bank Address": bank_address,
        "Customer Name": customer_name,
        "Customer Address": customer_address,
        "Statement Date": statement_date,
        "Account Number": account_number
    }


# HONG LEONG BANK TEMPLATE - TRANSACTION EXTRACTION --------------------------------------------
def extract_trxInfo(noUse, identified_bank, pdf_path_global):
    logger.logger.info("[hlb_pdf_extraction][extract_trxInfo()] : Executing the HONG LEONG BANK PDF file with x-coordinate logic for credit/debit detection")
    if identified_bank == 9:
        setSkipKey = "HONG LEONG ISLAMIC BANK BERHAD"
        setSkipKey2 = "TOTAL WITHDRAWALS"
    else:
        setSkipKey = "HONG LEONG BANK BERHAD"

    setContKey = "BAKI"

    doc = fitz.open(pdf_path_global)

    transactions = []
    current_date = None
    current_block = []
    current_amounts = []

    # Define amount column x-position ranges (tune these as needed)
    CREDIT_X_RANGE = (350, 400)
    DEBIT_X_RANGE = (450, 500)
    BALANCE_X_MIN = 501  # assume statement balance appears to the far right

    def is_date(text):
        return re.match(r"^\d{2}-\d{2}-\d{4}$", text.strip())

    def is_amount(text):
        return re.match(r"^\d{1,3}(,\d{3})*(\.\d{2})$", text.strip())

    # Helper to convert extracted block into a transaction object
    def process_block(date, content_lines, amounts):
        trx_list = []

        cr_amt = dr_amt = balance = 0.0

        for val, x0 in amounts:
            if CREDIT_X_RANGE[0] <= x0 < CREDIT_X_RANGE[1]:
                cr_amt = val
            elif DEBIT_X_RANGE[0] <= x0 < DEBIT_X_RANGE[1]:
                dr_amt = val
            elif x0 >= BALANCE_X_MIN:
                balance = val

        desc = content_lines[0] if content_lines else ""
        desc_others = " ".join(content_lines[1:]) if len(
            content_lines) > 1 else ""

        trx_list.append({
            "trn_pdf_date": date.replace("-", "/"),
            "trn_pdf_description": desc,
            "trn_pdf_description_others": desc_others,
            "trn_pdf_ner": NER_extraction(f"{desc} {desc_others}") or "",
            "trn_pdf_CR_Amount": cr_amt,
            "trn_pdf_DR_Amount": dr_amt,
            "trn_pdf_statementBalance": balance
        })

        return trx_list

    # === Page-level parsing ===
    skipAfterLastTrnInd = False

    for page in doc:
        blocks = page.get_text("dict")["blocks"] # pyright: ignore[reportAttributeAccessIssue]

        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    x0 = span["bbox"][0]

                    if not text:
                        continue

                    # ✅ STOP if bank name appears
                    if identified_bank == 9:
                        if setSkipKey in text.upper() or setSkipKey2 in text.upper():
                            skipAfterLastTrnInd = True
                    else:
                        if setSkipKey in text.upper():
                            skipAfterLastTrnInd = True

                    if setContKey == text.upper():
                        skipAfterLastTrnInd = False
                        break

                    if skipAfterLastTrnInd:
                        break  # or use return transactions if final result ready

                    if is_date(text):
                        if current_date and current_block:
                            transactions.extend(process_block(
                                current_date, current_block, current_amounts))
                        current_date = text
                        current_block = []
                        current_amounts = []
                        continue

                    if is_amount(text):
                        try:
                            amt = float(text.replace(",", ""))
                            current_amounts.append((amt, x0))
                        except Exception:
                            continue
                    else:
                        current_block.append(text)

    # Final block
    if current_date and current_block:
        transactions.extend(process_block(
            current_date, current_block, current_amounts))

    return transactions
# Sub Process - Differentiate the caller by detected bank name ---------------------------------------