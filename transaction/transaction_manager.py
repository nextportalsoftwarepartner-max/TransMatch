# flake8: noqa: E501

import logger
import re
from db_manager import (
    execute_query,
    executionWithRs_query,
    commit,
    executionWithRs_queryWithCommit,
    rollback
)
from datetime import datetime
from dateutil import parser

logger.logger.info("[transaction_manager] : Menu initiation")


def get_or_create_bank_id(bank_name, bank_reg_no, bank_address):
    logger.logger.info("[transaction_manager] : Create or Retrieve Bank ID")

    """Check if bank exists; if not, insert it and return NUM_BANK_ID."""
    # ✅ Early exit if bank name is invalid or unknown
    if not bank_name or bank_name.strip().lower() in ("unknown", "unknown bank"):
        logger.logger.info("[transaction_manager] : Bank Name is invalid or unknown")
        return None

    query_check = """
        SELECT NUM_BANK_ID FROM TM_MST_BANK
        WHERE VCH_BANK_NAME = %s AND CHR_ACTIVE_IND = 'Y'
    """
    existing = executionWithRs_query(query_check, (bank_name,))
    if existing:
        logger.logger.info(f"[transaction_manager] : Bank Name exists = {existing[0][0]}")
        return existing[0][0]

    logger.logger.info(f"[transaction_manager] : Bank Name NOT exists, proceed to create and insert new bank ({bank_name}) into database")
    query_insert = """
        INSERT INTO TM_MST_BANK (
            VCH_BANK_NAME, VCH_BANK_DISPLAY_NM, VCH_BANK_REG_NO, VCH_ADDRESS,
            CHR_ACTIVE_IND, NUM_CREATED_BY
        ) VALUES (%s, %s, %s, %s, 'Y', %s)
        RETURNING NUM_BANK_ID
    """
    now = datetime.now()
    result = executionWithRs_queryWithCommit(query_insert, (
        bank_name, bank_name, bank_reg_no, bank_address, 1
    ))
    return result[0][0] if result else None


def get_or_create_customer_id(customer_code, customer_name, customer_address):
    logger.logger.info("[transaction_manager] : Create or Retrieve Customer ID")

    """Check if customer exists; if not, insert and return NUM_CUST_ID."""
    # ✅ Early exit if customer code & name is invalid or unknown
    if not customer_code or customer_code.strip().lower() in ("unknown", "unknown customer code"):
        logger.logger.info("[transaction_manager] : Customer Code is invalid or unknown")
        return None

    if not customer_name or customer_name.strip().lower() in ("unknown", "unknown customer"):
        logger.logger.info("[transaction_manager] : Customer Name is invalid or unknown")
        return None

    query_check = """
        SELECT NUM_CUST_ID FROM TM_MST_CUSTOMER
        WHERE VCH_CUST_CODE = %s AND CHR_ACTIVE_IND = 'Y'
    """
    existing = executionWithRs_query(query_check, (customer_code,))
    if existing:
        logger.logger.info(f"[transaction_manager] : Customer exists, CUST_ID = {existing[0][0]}")
        return existing[0][0]

    logger.logger.info(f"[transaction_manager] : Customer NOT exists, proceed to create and insert new customer ({customer_name}) into database")
    query_insert = """
        INSERT INTO TM_MST_CUSTOMER (
            VCH_CUST_CODE, VCH_CUST_NAME, VCH_ADDRESS, CHR_ACTIVE_IND, NUM_CREATED_BY
        ) VALUES (%s, %s, %s, 'Y', %s)
        RETURNING NUM_CUST_ID
    """
    result = executionWithRs_queryWithCommit(query_insert, (
        customer_code, customer_name, customer_address, 1
    ))
    return result[0][0] if result else None


def get_data_entry_id(data_entry):
    logger.logger.info("[transaction_manager] : Create or Retrieve Data Entry method")

    """Get NUM_DT_ENT_ID for given data entry name."""
    # ✅ Early exit if customer name is invalid or unknown
    if not data_entry or data_entry.strip().lower() in ("unknown", "unknown data entry"):
        logger.logger.info("[transaction_manager] : Data Entry is invalid or unknown")
        return None

    query_check = """
        SELECT NUM_DT_ENT_ID FROM TM_MST_DATA_ENTRY_SOURCE
        WHERE VCH_DT_ENT_CODE = %s AND CHR_ACTIVE_IND = 'Y'
    """
    existing = executionWithRs_query(query_check, (data_entry,))
    if existing:
        logger.logger.info(f"[transaction_manager] : Data Entry Method exists, DT_ENT_ID = {existing[0][0]}")
        return existing[0][0] if existing else None

    logger.logger.info(f"[transaction_manager] : Data Entry ({data_entry}) NOT exists, no further action, please contact IT department for further assistance")


def save_transactions_to_db(transactions, static_info):
    logger.logger.info("[transaction_manager] : Executing the transaction SAVE operation")

    """Save transaction records into TM_TRN_TRANSACTION table"""

    # ✅ 1. Get or insert bank
    bank_id = get_or_create_bank_id(
        bank_name=static_info.get("Bank Name", ""),
        bank_reg_no=static_info.get("Bank Registration No", ""),
        bank_address=static_info.get("Bank Address", "")
    )

    # ✅ 2. Get or insert customer
    customer_id = get_or_create_customer_id(
        customer_code=static_info.get("Customer Code", ""),
        customer_name=static_info.get("Customer Name", ""),
        customer_address=static_info.get("Customer Address", "")
    )

    # ✅ 3. Get Data Entry ID by code
    data_entry_id = get_data_entry_id(static_info.get("Data Entry", ""))

    # ✅ 4. Get statement date from extracted data
    statement_date_str = static_info.get("Statement Date", "").strip()

    # Convert "31/12/24" → "2024-12-31 00:00:00"
    try:
        # statement_date = datetime.strptime(statement_date_str, "%d/%m/%y")  # Convert to datetime object
        # statement_date = statement_date.strftime("%Y-%m-%d %H:%M:%S") # Convert to string with timestamp format

        statement_date = parser.parse(statement_date_str)
        statement_date = statement_date.strftime("%Y-%m-%d %H:%M:%S")

    except ValueError:
        statement_date = None  # Handle invalid date gracefully

    insert_query = """
    INSERT INTO TM_TRN_TRANSACTION (
        NUM_BANK_ID, NUM_DT_ENT_ID, NUM_CUST_ID, NUM_USER_ID,
        NUM_ACCOUNT_NO, DTT_STATEMENT_DATE, DTT_TRANSACTION_DATE,
        VCH_TRN_DESC_1, VCH_TRN_DESC_2, VCH_NER, NUM_AMOUNT_CREDIT,
        NUM_AMOUNT_DEBIT, NUM_STATEMENT_BALANCE, VCH_FILE_NAME, NUM_CREATED_BY
    )
    VALUES (
        %(bank_id)s, %(data_entry)s, %(cust_id)s, %(staff_id)s,
        %(account_number)s, %(statement_date)s, %(transaction_date)s,
        %(transaction_description)s, %(transaction_description_others)s,
        %(trn_pdf_ner)s, %(amount_credit)s, %(amount_debit)s, 
        %(statement_balance)s, %(file_name)s, %(creator)s
    )
    """

    tempconn = None

    for trx in transactions:
        try:
            transaction_date_str = trx.get("trn_pdf_date", "").strip()
            
            # ✅ Case 1: "DD/MM" → append statement year
            if re.match(r"^\d{2}/\d{2}$", transaction_date_str):
                trn_statDT = parser.parse(statement_date_str)
                year = trn_statDT.year

                transaction_date_full = f"{transaction_date_str}/{year}"
                transaction_date = datetime.strptime(transaction_date_full, "%d/%m/%Y")

            # ✅ Case 2: "DD/MM/YY" or "DD/MM/YYYY"
            elif re.match(r"^\d{2}/\d{2}/\d{2,4}$", transaction_date_str):
                transaction_date = datetime.strptime(transaction_date_str, "%d/%m/%Y") if len(transaction_date_str.split("/")[2]) == 4 else datetime.strptime(transaction_date_str, "%d/%m/%y")

            # ✅ Case 3: "DD-MM-YYYY"
            elif re.match(r"^\d{2}-\d{2}-\d{4}$", transaction_date_str):
                transaction_date = datetime.strptime(transaction_date_str, "%d-%m-%Y")

            else:
                logger.logger.info(f"[transaction_manager] : Unknown date format → {transaction_date_str}")
                continue  # skip invalid format

            # ✅ Final conversion to standard format
            transaction_date = transaction_date.strftime("%Y-%m-%d %H:%M:%S")

        except Exception as e:
            logger.logger.info(f"[transaction_manager] : Invalid transaction date format → {transaction_date_str} ({str(e)})")
            continue

        params = {
            "bank_id": bank_id,
            "data_entry": data_entry_id,
            "cust_id": customer_id,
            "staff_id": static_info.get("Staff ID", ""),
            "account_number": static_info.get("Account Number", ""),
            "statement_date": statement_date,
            "transaction_date": transaction_date,
            "transaction_description": trx.get("trn_pdf_description", ""),
            "transaction_description_others": trx.get("trn_pdf_description_others", ""),
            "trn_pdf_ner": trx.get("trn_pdf_ner", ""),
            "amount_credit": trx.get("trn_pdf_CR_Amount", 0),
            "amount_debit": trx.get("trn_pdf_DR_Amount", 0),
            "statement_balance": trx.get("trn_pdf_statementBalance", 0),
            "file_name": static_info.get("File Name", ""),
            "creator": 0
        }

        conn = execute_query(insert_query, params, tempconn)
        tempconn = conn

    if not bank_id or not customer_id or not statement_date or not transaction_date:
        rollback(conn)
        logger.logger.exception(f"[transaction_manager] : Error: Missing required information for transaction insertion. Bank ID: {bank_id}, Customer ID: {customer_id}, Statement Date: {statement_date}")
        return None
    else:
        commit(conn)
        logger.logger.info("[transaction_manager] : Transaction data inserted successfully")
        return True
