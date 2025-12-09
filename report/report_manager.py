# flake8: noqa: E501

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from db_manager import executionWithRs_query


class ReportManager:
    """
    Encapsulates transaction‐report fetching logic.
    """

    def fetch_transactions(self, filters: dict):
        """
        Given a dict of filter values, build and execute the SQL, and return the list of rows.
        filters keys:
          - customer_code (str or None)
          - customer_name (str or None)
          - customer_name_match ( "Equal" | "Contain" )
          - trx_desc (str or None)
          - trx_desc_match ( "Equal" | "Contain" )
          - bank_name (str or None)
          - trx_date_from (date or None)
          - trx_date_to   (date or None)
          - entry_date_from (date or None)
          - entry_date_to   (date or None)
          - printed_status  ("All"|"Y"|"N")
          - agent_name      (str or None)
          - file_name       (str or None)
        """
        sql = """
        SELECT
          b.vch_cust_code,
          b.vch_cust_name,
          (replace(trim(a.vch_trn_desc_1), '  ', ' ')
           || ' '
           || replace(trim(a.vch_trn_desc_2), '  ', '')) AS vch_trn_desc,
          a.vch_ner               AS ner,
          c.vch_bank_display_nm   AS vch_bank_name,
          a.num_amount_credit     AS amt_credit,
          a.num_amount_debit      AS amt_debit,
          a.dtt_transaction_date  AS trn_date,
          a.dtt_created_at        AS date_entry_date,
          a.chr_printed_ind       AS printed_ind,
          d.VCH_USER_NAME        AS staff_name,
          a.vch_file_name         AS file_name
        FROM tm_trn_transaction a
        INNER JOIN tm_mst_customer b ON a.num_cust_id  = b.num_cust_id
        INNER JOIN tm_mst_bank     c ON a.num_bank_id  = c.num_bank_id
        INNER JOIN TM_MST_USER    d ON a.NUM_USER_ID = d.NUM_USER_ID
        WHERE 1=1
        """
        params = []

        # Apply filters in order
        if (cc := filters.get("customer_code")):
            sql += " AND b.vch_cust_code ILIKE %s"
            params.append(f"%{cc.strip()}%")
        if (cn := filters.get("customer_name")):
            if filters.get("customer_name_match") == "Equal":
                sql += " AND b.vch_cust_name = %s"
                params.append(cn)
            else:
                sql += " AND b.vch_cust_name ILIKE %s"
                params.append(f"%{cn}%")
        if (td := filters.get("trx_desc")):
            if filters.get("trx_desc_match") == "Equal":
                sql += " AND (a.vch_trn_desc_1 = %s OR a.vch_trn_desc_2 = %s)"
                params += [td, td]
            else:
                sql += " AND (a.vch_trn_desc_1 ILIKE %s OR a.vch_trn_desc_2 ILIKE %s)"
                params += [f"%{td}%", f"%{td}%"]
        if (bn := filters.get("bank_name")) and bn != "All":
            sql += " AND c.vch_bank_display_nm = %s"
            params.append(bn)
        if (df := filters.get("trx_date_from")):
            sql += " AND a.dtt_transaction_date >= %s"
            params.append(df)
        if (dt := filters.get("trx_date_to")):
            sql += " AND a.dtt_transaction_date <= %s"
            params.append(dt)
        if (ef := filters.get("entry_date_from")):
            sql += " AND a.dtt_created_at >= %s"
            params.append(ef)
        if (et := filters.get("entry_date_to")):
            sql += " AND a.dtt_created_at <= %s"
            params.append(et)
        if (ps := filters.get("printed_status")) and ps != "All":
            sql += " AND a.chr_printed_ind = %s"
            params.append(ps)
        if (ag := filters.get("agent_name")) and ag != "All":
            sql += " AND d.VCH_USER_NAME = %s"
            params.append(ag)
        if (fn := filters.get("file_name")) and fn != "All":
            sql += " AND a.vch_file_name = %s"
            params.append(fn)

        sql += " ORDER BY a.dtt_transaction_date DESC"
        return executionWithRs_query(sql, tuple(params)) or []
