# flake8: noqa: E501

import tkinter as tk
import psycopg2
import logger
import threading
from LoadingPopup import LoadingPopupClass
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from db_manager import executionWithRs_query, execute_query, commit

logger.logger.info("[data_enrichment_main] : Menu initiation")


class DataEnrichment:
    def __init__(self, root, login_id):
        self.root = root
        self.dataEnrch_window = tk.Toplevel(root)
        self.dataEnrch_window.title("Data Enrichment")

        # ✅ Set window to 90% width and 90% height, centered
        screen_width = self.dataEnrch_window.winfo_screenwidth()
        screen_height = self.dataEnrch_window.winfo_screenheight()

        window_width = int(screen_width * 1)
        window_height = int(screen_height * 0.9)

        x_pos = int((screen_width - window_width) / 2)
        y_pos = int((screen_height - window_height) / 5)

        self.dataEnrch_window.geometry(
            f"{window_width}x{window_height}+{x_pos}+{y_pos}")

        self.dataEnrch_window.transient(self.root)  # Make it modal-like
        self.dataEnrch_window.grab_set()  # Prevent interaction with the main window
        self.dataEnrch_window.focus_force()  # Bring the focus to this window

        logger.logger.info("[data_enrichment_main] : Data Enrichment Window Opened")

        self.create_filter_section()
        self.create_results_section()

    def create_filter_section(self):
        frame = tk.LabelFrame(
            self.dataEnrch_window, text="Filter Criteria", bg="white", font=("Helvetica", 12))
        frame.pack(fill=tk.X, padx=20, pady=10)

        # Customer Code Dropdown
        tk.Label(frame, text="Customer Code:", bg="white").grid(
            row=0, column=0, padx=10, pady=5, sticky='w')
        self.customer_code_var = tk.StringVar()
        self.customer_code_dropdown = ttk.Combobox(
            frame, textvariable=self.customer_code_var, state="readonly")
        codes = executionWithRs_query(
            "SELECT DISTINCT VCH_CUST_CODE FROM TM_MST_CUSTOMER ORDER BY VCH_CUST_CODE")
        self.customer_code_dropdown['values'] = [
            "All"] + [row[0] for row in codes] if codes else ["All"]
        self.customer_code_var.set("All")
        self.customer_code_dropdown.grid(row=0, column=1, padx=10, pady=5)

        # Customer Name + Match Type
        tk.Label(frame, text="Customer Name:", bg="white").grid(
            row=0, column=2, padx=10, pady=5, sticky='w')
        self.customer_name_var = tk.StringVar()
        self.customer_name_match = tk.StringVar(value="Equal")
        name_frame = tk.Frame(frame, bg="white")
        name_frame.grid(row=0, column=3, padx=10, pady=5)
        ttk.Radiobutton(name_frame, text="Equal",
                        variable=self.customer_name_match, value="Equal").pack(side=tk.LEFT)
        ttk.Radiobutton(name_frame, text="Contain",
                        variable=self.customer_name_match, value="Contain").pack(side=tk.LEFT)
        ttk.Entry(name_frame, textvariable=self.customer_name_var,
                  width=20).pack(side=tk.LEFT)

        # Account Number
        tk.Label(frame, text="Account Number:", bg="white").grid(
            row=0, column=4, padx=10, pady=5, sticky='w')
        self.account_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.account_var, width=20).grid(
            row=0, column=5, padx=10, pady=5)

        # Target Audience
        tk.Label(frame, text="Target Audience:", bg="white").grid(
            row=0, column=6, padx=10, pady=5, sticky='w')
        self.ner_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.ner_var, width=20).grid(
            row=0, column=7, padx=10, pady=5)

        # Filter by (Transaction Date / Data Entry Date)
        tk.Label(frame, text="Filter by:", bg="white").grid(
            row=1, column=0, padx=10, pady=5, sticky='w')
        self.filter_by_var = tk.StringVar(value="Transaction Date")
        filter_frame = tk.Frame(frame, bg="white")
        filter_frame.grid(row=1, column=1, padx=10, pady=5, sticky='w')
        ttk.Radiobutton(filter_frame, text="Transaction Date", variable=self.filter_by_var,
                        value="Transaction Date", command=self.toggle_date_fields).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Data Entry Date", variable=self.filter_by_var,
                        value="Data Entry Date", command=self.toggle_date_fields).pack(side=tk.LEFT)

        # File Name Dropdown
        tk.Label(frame, text="File Name:", bg="white").grid(
            row=1, column=2, padx=10, pady=5, sticky='w')
        self.file_var = tk.StringVar()
        self.file_dropdown = ttk.Combobox(
            frame, textvariable=self.file_var, state="readonly")
        files = executionWithRs_query(
            "SELECT DISTINCT VCH_FILE_NAME FROM TM_TRN_TRANSACTION ORDER BY VCH_FILE_NAME")
        self.file_dropdown['values'] = ["All"] + [row[0]
                                                  for row in files] if files else ["All"]
        self.file_var.set("All")
        self.file_dropdown.grid(row=1, column=3, padx=10, pady=5)

        # Transaction Desc + Match Type
        tk.Label(frame, text="Transaction Desc:", bg="white").grid(
            row=1, column=4, padx=10, pady=5, sticky='w')
        self.trx_var = tk.StringVar()
        self.trx_match = tk.StringVar(value="Equal")
        trx_frame = tk.Frame(frame, bg="white")
        trx_frame.grid(row=1, column=5, padx=10, pady=5)
        ttk.Radiobutton(trx_frame, text="Equal",
                        variable=self.trx_match, value="Equal").pack(side=tk.LEFT)
        ttk.Radiobutton(trx_frame, text="Contain",
                        variable=self.trx_match, value="Contain").pack(side=tk.LEFT)
        ttk.Entry(trx_frame, textvariable=self.trx_var,
                  width=20).pack(side=tk.LEFT)

        # Transaction Date From / To
        self.trx_from_label = tk.Label(
            frame, text="Transaction Date From:", bg="white")
        self.trx_from_label.grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.trx_from = DateEntry(frame)
        self.trx_from.grid(row=2, column=1, padx=10, pady=5)

        self.trx_to_label = tk.Label(
            frame, text="Transaction Date To:", bg="white")
        self.trx_to_label.grid(row=2, column=2, padx=10, pady=5, sticky='w')
        self.trx_to = DateEntry(frame)
        self.trx_to.grid(row=2, column=3, padx=10, pady=5)

        # Data Entry From / To
        self.entry_from_label = tk.Label(
            frame, text="Data Entry From:", bg="white")
        self.entry_from_label.grid(
            row=3, column=0, padx=10, pady=5, sticky='w')
        self.entry_from = DateEntry(frame)
        self.entry_from.grid(row=3, column=1, padx=10, pady=5)

        self.entry_to_label = tk.Label(
            frame, text="Data Entry To:", bg="white")
        self.entry_to_label.grid(row=3, column=2, padx=10, pady=5, sticky='w')
        self.entry_to = DateEntry(frame)
        self.entry_to.grid(row=3, column=3, padx=10, pady=5)

        # Buttons
        btn_frame = tk.Frame(frame, bg="white")
        btn_frame.grid(row=4, column=0, columnspan=4, pady=10)
        ttk.Button(btn_frame, text="🔍 Search", command=self.search).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="🔄 Reset", command=self.reset_filters).pack(
            side=tk.LEFT, padx=10)

        self.toggle_date_fields()

    def create_results_section(self):
        frame = tk.Frame(self.dataEnrch_window, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        cols = ("NO.", "Customer Code", "Customer Name", "Account Number", "Target Audience",
                "File Name", "Transaction Description", "Transaction Date", "Data Entry Date")

        self.tree = ttk.Treeview(
            frame, columns=cols, show="headings", height=25)

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=150)

        # Add vertical scrollbar
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Add horizontal scrollbar (optional)
        hsb = ttk.Scrollbar(frame, orient="horizontal",
                            command=self.tree.xview)
        self.tree.configure(xscroll=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.edit_record)

    # def search(self):
    #     logger.logger.info("[data_enrichment_main] : Search triggered")
    #     self.tree.delete(*self.tree.get_children())

    #     logger.logger.info(
    #         "[data_enrichment_main] : Start SQL building for search")
    #     sql = """
    #         SELECT a.NUM_TRN_ID,b.vch_cust_code, b.vch_cust_name, a.num_account_no, a.vch_ner, 
    #             a.vch_file_name, 
    #             (replace(trim(a.vch_trn_desc_1), '  ', ' ') || ' ' || replace(trim(a.vch_trn_desc_2), '  ', ' ')) AS trx_desc,
    #             a.dtt_transaction_date, TO_CHAR(a.dtt_created_at, 'YYYY-MM-DD HH24:MI:SS') AS dtt_created_at
    #         FROM tm_trn_transaction a
    #         JOIN tm_mst_customer b ON a.num_cust_id = b.num_cust_id
    #         WHERE 1=1
    #     """
    #     params = []

    #     # Customer Code filter
    #     if self.customer_code_var.get() != "All":
    #         sql += " AND b.vch_cust_code = %s"
    #         params.append(self.customer_code_var.get())

    #     # Customer Name filter
    #     if self.customer_name_var.get():
    #         if self.customer_name_match.get() == "Equal":
    #             sql += " AND b.vch_cust_name = %s"
    #             params.append(self.customer_name_var.get())
    #         else:
    #             sql += " AND b.vch_cust_name ILIKE %s"
    #             params.append(f"%{self.customer_name_var.get()}%")

    #     # Account Number filter
    #     if self.account_var.get():
    #         sql += " AND a.num_account_no::text ILIKE %s"
    #         params.append(f"%{self.account_var.get()}%")

    #     # Target Audience filter
    #     if self.ner_var.get():
    #         sql += " AND a.vch_ner ILIKE %s"
    #         params.append(f"%{self.ner_var.get()}%")

    #     # File Name filter
    #     if self.file_var.get() != "All":
    #         sql += " AND a.vch_file_name = %s"
    #         params.append(self.file_var.get())

    #     # Transaction Description filter
    #     if self.trx_var.get():
    #         if self.trx_match.get() == "Equal":
    #             sql += " AND (a.vch_trn_desc_1 = %s OR a.vch_trn_desc_2 = %s)"
    #             params += [self.trx_var.get(), self.trx_var.get()]
    #         else:
    #             sql += " AND (a.vch_trn_desc_1 ILIKE %s OR a.vch_trn_desc_2 ILIKE %s)"
    #             params += [f"%{self.trx_var.get()}%",
    #                        f"%{self.trx_var.get()}%"]

    #     # Date filtering based on selection
    #     if self.filter_by_var.get() == "Transaction Date":
    #         if self.trx_from.get_date():
    #             sql += " AND a.dtt_transaction_date::date >= %s"
    #             params.append(self.trx_from.get_date())
    #         if self.trx_to.get_date():
    #             sql += " AND a.dtt_transaction_date::date <= %s"
    #             params.append(self.trx_to.get_date())
    #     else:
    #         if self.entry_from.get_date():
    #             sql += " AND a.dtt_created_at::date >= %s"
    #             params.append(self.entry_from.get_date())
    #         if self.entry_to.get_date():
    #             sql += " AND a.dtt_created_at::date <= %s"
    #             params.append(self.entry_to.get_date())

    #     sql += " ORDER BY a.num_trn_id"

    #     # Execute query
    #     rows = executionWithRs_query(sql, tuple(params)) or []
    #     for idx, row in enumerate(rows):
    #         self.tree.insert("", "end", values=row)

    #     # ✅ Auto fit columns after populated
    #     self.adjust_column_width()

    def search(self):
        loading = LoadingPopupClass(self.dataEnrch_window, message="Searching... Please wait.")

        def threaded_search():
            self.perform_search_logic(popup=loading)

        threading.Thread(target=threaded_search).start()

    def perform_search_logic(self, popup=None):
        try:
            logger.logger.info("[data_enrichment_main] : Search triggered")
            self.tree.delete(*self.tree.get_children())

            logger.logger.info("[data_enrichment_main] : Start SQL building for search")
            sql = """
                SELECT a.NUM_TRN_ID,b.vch_cust_code, b.vch_cust_name, a.num_account_no, a.vch_ner, 
                    a.vch_file_name, 
                    (replace(trim(a.vch_trn_desc_1), '  ', ' ') || ' ' || replace(trim(a.vch_trn_desc_2), '  ', ' ')) AS trx_desc,
                    a.dtt_transaction_date, TO_CHAR(a.dtt_created_at, 'YYYY-MM-DD HH24:MI:SS') AS dtt_created_at
                FROM tm_trn_transaction a
                JOIN tm_mst_customer b ON a.num_cust_id = b.num_cust_id
                WHERE 1=1
            """

            params = []

            # Customer Code filter
            if self.customer_code_var.get() != "All":
                sql += " AND b.vch_cust_code = %s"
                params.append(self.customer_code_var.get())

            # Customer Name filter
            if self.customer_name_var.get():
                if self.customer_name_match.get() == "Equal":
                    sql += " AND b.vch_cust_name = %s"
                    params.append(self.customer_name_var.get())
                else:
                    sql += " AND b.vch_cust_name ILIKE %s"
                    params.append(f"%{self.customer_name_var.get()}%")

            # Account Number filter
            if self.account_var.get():
                sql += " AND a.num_account_no::text ILIKE %s"
                params.append(f"%{self.account_var.get()}%")

            # Target Audience filter
            if self.ner_var.get():
                sql += " AND a.vch_ner ILIKE %s"
                params.append(f"%{self.ner_var.get()}%")

            # File Name filter
            if self.file_var.get() != "All":
                sql += " AND a.vch_file_name = %s"
                params.append(self.file_var.get())

            # Transaction Description filter
            if self.trx_var.get():
                if self.trx_match.get() == "Equal":
                    sql += " AND (a.vch_trn_desc_1 = %s OR a.vch_trn_desc_2 = %s)"
                    params += [self.trx_var.get(), self.trx_var.get()]
                else:
                    sql += " AND (a.vch_trn_desc_1 ILIKE %s OR a.vch_trn_desc_2 ILIKE %s)"
                    params += [f"%{self.trx_var.get()}%",
                               f"%{self.trx_var.get()}%"]

            # Date filtering based on selection
            if self.filter_by_var.get() == "Transaction Date":
                if self.trx_from.get_date():
                    sql += " AND a.dtt_transaction_date::date >= %s"
                    params.append(self.trx_from.get_date())
                if self.trx_to.get_date():
                    sql += " AND a.dtt_transaction_date::date <= %s"
                    params.append(self.trx_to.get_date())
            else:
                if self.entry_from.get_date():
                    sql += " AND a.dtt_created_at::date >= %s"
                    params.append(self.entry_from.get_date())
                if self.entry_to.get_date():
                    sql += " AND a.dtt_created_at::date <= %s"
                    params.append(self.entry_to.get_date())

            sql += " ORDER BY a.num_trn_id"

            rows = executionWithRs_query(sql, tuple(params)) or []
            for idx, row in enumerate(rows):
                self.tree.insert("", "end", values=row)

            self.adjust_column_width()
            logger.logger.info("[data_enrichment_main] : Search completed.")

        except Exception as e:
            logger.logger.exception(
                f"[data_enrichment_main] : Error during search: {str(e)}")
            messagebox.showerror(
                "Error", f"An error occurred during search:\n{str(e)}")

        finally:
            if popup:
                popup.close()

    def reset_filters(self):
        self.customer_code_var.set("All")
        self.customer_name_var.set("")
        self.account_var.set("")
        self.ner_var.set("")
        self.file_var.set("All")
        self.trx_var.set("")
        self.trx_match.set("Equal")
        self.customer_name_match.set("Equal")
        self.filter_by_var.set("Transaction Date")
        self.toggle_date_fields()

    def edit_record(self, event):
        try:
            selected_item = self.tree.focus()
            if not selected_item:
                messagebox.showwarning(
                    "No Selection", "Please select a record to edit.")
                return

            values = self.tree.item(selected_item)["values"]  # whole tuple
            self.open_edit_window(values)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def open_edit_window(self, data):
        popup = tk.Toplevel(self.root)
        popup.title("Edit Transaction Record")
        popup.geometry("1200x700")
        popup.transient(self.dataEnrch_window)
        popup.grab_set()
        popup.focus_force()

        # === Retrieve NUM_TRN_ID from selected Treeview row ===
        trn_id = data[0]

        # === Query full record from DB ===
        sql = """
            SELECT
                A.NUM_TRN_ID, A.VCH_FILE_NAME, B.VCH_BANK_NAME, B.VCH_ADDRESS, B.VCH_BANK_REG_NO,
                C.VCH_CUST_CODE, C.VCH_CUST_NAME, C.VCH_ADDRESS,
                A.NUM_ACCOUNT_NO, A.DTT_STATEMENT_DATE, A.DTT_TRANSACTION_DATE,
                A.VCH_TRN_DESC_1, A.VCH_TRN_DESC_2,
                A.VCH_NER, A.NUM_AMOUNT_CREDIT, A.NUM_AMOUNT_DEBIT, A.NUM_STATEMENT_BALANCE,
                A.CHR_PRINTED_IND, D.NUM_USER_ID
            FROM TM_TRN_TRANSACTION A
            INNER JOIN TM_MST_BANK B ON A.NUM_BANK_ID = B.NUM_BANK_ID
            INNER JOIN TM_MST_CUSTOMER C ON A.NUM_CUST_ID = C.NUM_CUST_ID
            INNER JOIN TM_MST_USER D ON A.NUM_USER_ID = D.NUM_USER_ID
            WHERE A.NUM_TRN_ID = %s
        """
        result = executionWithRs_query(sql, (trn_id,))

        if not result:
            messagebox.showerror("Error", "No data found for this record")
            popup.destroy()
            return

        record = result[0]

        # === ROW 0: File Name ===
        tk.Label(popup, text="File Name:").grid(
            row=0, column=0, padx=10, pady=5, sticky='e')
        file_var = tk.StringVar()
        ttk.Entry(popup, textvariable=file_var, width=50).grid(
            row=0, column=1, columnspan=3, padx=10, pady=5, sticky='w')

        # === ROW 1: Bank Name (Dropdown), Bank Address, Reg ===
        tk.Label(popup, text="Bank Name:").grid(
            row=1, column=0, padx=10, pady=5, sticky='e')
        bank_var = tk.StringVar()
        bank_dropdown = ttk.Combobox(
            popup, textvariable=bank_var, state="readonly", width=50)
        bank_results = executionWithRs_query(
            "SELECT VCH_BANK_NAME FROM TM_MST_BANK ORDER BY VCH_BANK_NAME")
        bank_dropdown['values'] = [row[0]
                                   for row in bank_results] if bank_results else []
        bank_dropdown.grid(row=1, column=1, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Bank Address:").grid(
            row=1, column=2, padx=10, pady=5, sticky='e')
        bank_addr_var = tk.StringVar()
        ttk.Entry(popup, textvariable=bank_addr_var, width=40, state="readonly").grid(
            row=1, column=3, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Bank Reg No:").grid(
            row=2, column=0, padx=10, pady=5, sticky='e')
        bank_reg_var = tk.StringVar()
        ttk.Entry(popup, textvariable=bank_reg_var, width=50, state="readonly").grid(
            row=2, column=1, padx=10, pady=5, sticky='w')

        def populate_bank_details(event):
            result = executionWithRs_query(
                "SELECT VCH_ADDRESS, VCH_BANK_REG_NO FROM TM_MST_BANK WHERE VCH_BANK_NAME = %s", (bank_var.get(),))
            if result:
                bank_addr_var.set(result[0][0])
                bank_reg_var.set(result[0][1])
            else:
                bank_addr_var.set("")
                bank_reg_var.set("")
        bank_dropdown.bind("<<ComboboxSelected>>", populate_bank_details)

        # === ROW 2: Customer Code ===
        tk.Label(popup, text="Customer Code:").grid(
            row=3, column=0, padx=10, pady=5, sticky='e')
        cust_code_var = tk.StringVar()
        cust_dropdown = ttk.Combobox(
            popup, textvariable=cust_code_var, state="readonly", width=50)
        cust_results = executionWithRs_query(
            "SELECT VCH_CUST_CODE FROM TM_MST_CUSTOMER ORDER BY VCH_CUST_CODE")
        cust_dropdown['values'] = [row[0]
                                   for row in cust_results] if cust_results else []
        cust_dropdown.grid(row=3, column=1, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Customer Name:").grid(
            row=3, column=2, padx=10, pady=5, sticky='e')
        cust_name_var = tk.StringVar()
        ttk.Entry(popup, textvariable=cust_name_var, width=40, state="readonly").grid(
            row=3, column=3, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Customer Address:").grid(
            row=4, column=0, padx=10, pady=5, sticky='e')
        cust_addr_var = tk.StringVar()
        ttk.Entry(popup, textvariable=cust_addr_var, width=50, state="readonly").grid(
            row=4, column=1, padx=10, pady=5, sticky='w')

        def populate_customer_details(event):
            result = executionWithRs_query(
                "SELECT VCH_CUST_NAME, VCH_CUST_ADDRESS FROM TM_MST_CUSTOMER WHERE VCH_CUST_CODE = %s", (cust_code_var.get(),))
            if result:
                cust_name_var.set(result[0][0])
                cust_addr_var.set(result[0][1])
            else:
                cust_name_var.set("")
                cust_addr_var.set("")
        cust_dropdown.bind("<<ComboboxSelected>>", populate_customer_details)

        # === ROW 3: Account No, Statement Date ===
        tk.Label(popup, text="Account No:").grid(
            row=5, column=0, padx=10, pady=5, sticky='e')
        account_var = tk.StringVar()
        ttk.Entry(popup, textvariable=account_var, width=50).grid(
            row=5, column=1, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Statement Date:").grid(
            row=5, column=2, padx=10, pady=5, sticky='e')
        stmt_date_var = DateEntry(popup, width=20)
        stmt_date_var.grid(row=5, column=3, padx=10, pady=5, sticky='w')

        # === ROW 4: Transaction Date, Description ===
        tk.Label(popup, text="Transaction Date:").grid(
            row=6, column=0, padx=10, pady=5, sticky='e')
        trx_date_var = DateEntry(popup, width=20)
        trx_date_var.grid(row=6, column=1, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Transaction Desc:").grid(
            row=6, column=2, padx=10, pady=5, sticky='e')
        trx_desc_var = tk.StringVar()
        ttk.Entry(popup, textvariable=trx_desc_var, width=40).grid(
            row=6, column=3, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Desc Others:").grid(
            row=7, column=0, padx=10, pady=5, sticky='e')
        trx_desc2_var = tk.StringVar()
        ttk.Entry(popup, textvariable=trx_desc2_var, width=50).grid(
            row=7, column=1, columnspan=3, padx=10, pady=5, sticky='w')

        # === ROW 5: Target Audience, Credit, Debit, Balance ===
        tk.Label(popup, text="Target Audience:").grid(
            row=8, column=0, padx=10, pady=5, sticky='e')
        ner_var = tk.StringVar()
        ttk.Entry(popup, textvariable=ner_var, width=50).grid(
            row=8, column=1, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Credit Amount:").grid(
            row=8, column=2, padx=10, pady=5, sticky='e')
        cr_amt_var = tk.StringVar()
        ttk.Entry(popup, textvariable=cr_amt_var, width=20).grid(
            row=8, column=3, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Debit Amount:").grid(
            row=9, column=0, padx=10, pady=5, sticky='e')
        dr_amt_var = tk.StringVar()
        ttk.Entry(popup, textvariable=dr_amt_var, width=20).grid(
            row=9, column=1, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Statement Balance:").grid(
            row=9, column=2, padx=10, pady=5, sticky='e')
        stmt_bal_var = tk.StringVar()
        ttk.Entry(popup, textvariable=stmt_bal_var, width=20).grid(
            row=9, column=3, padx=10, pady=5, sticky='w')

        # === ROW 6: Printed Status + Agent ===
        tk.Label(popup, text="Printed Status:").grid(
            row=10, column=0, padx=10, pady=5, sticky='e')
        printed_var = tk.StringVar()
        ttk.Entry(popup, textvariable=printed_var, width=50).grid(
            row=10, column=1, padx=10, pady=5, sticky='w')

        tk.Label(popup, text="Agent Name:").grid(
            row=10, column=2, padx=10, pady=5, sticky='e')
        agent_var = tk.StringVar()
        agent_dropdown = ttk.Combobox(
            popup, textvariable=agent_var, state="readonly", width=40)
        agent_results = executionWithRs_query(
            "SELECT NUM_USER_ID FROM TM_MST_USER ORDER BY NUM_USER_ID")
        agent_dropdown['values'] = [row[0]
                                    for row in agent_results] if agent_results else []
        agent_dropdown.grid(row=10, column=3, padx=10, pady=5, sticky='w')

        # === Populate values from DB ===
        file_var.set(record[1])
        bank_var.set(record[2])
        bank_addr_var.set(record[3])
        bank_reg_var.set(record[4])
        cust_code_var.set(record[5])
        cust_name_var.set(record[6])
        cust_addr_var.set(record[7])
        account_var.set(record[8])
        stmt_date_var.set_date(record[9])
        trx_date_var.set_date(record[10])
        trx_desc_var.set(record[11])
        trx_desc2_var.set(record[12])
        ner_var.set(record[13])
        cr_amt_var.set(str(record[14]))
        dr_amt_var.set(str(record[15]))
        stmt_bal_var.set(str(record[16]))
        printed_var.set(record[17])
        agent_var.set(str(record[18]))

        # === Save Button ===
        # def save():
        #     print(f"{datetime.now()} - [data_enrichment_main] : Testing")
        #     # Your SQL Update logic goes here
        #     messagebox.showinfo("Saved", "Record updated successfully.")
        #     popup.destroy()
        def save():
            try:
                # 1️⃣ Retrieve Bank ID based on Bank Name
                bank_result = executionWithRs_query(
                    "SELECT NUM_BANK_ID FROM TM_MST_BANK WHERE VCH_BANK_NAME = %s",
                    (bank_var.get(),)
                )
                if not bank_result:
                    messagebox.showerror("Error", "Invalid Bank selected.")
                    return
                num_bank_id = bank_result[0][0]

                # 2️⃣ Retrieve Customer ID based on Customer Code
                cust_result = executionWithRs_query(
                    "SELECT NUM_CUST_ID FROM TM_MST_CUSTOMER WHERE VCH_CUST_CODE = %s",
                    (cust_code_var.get(),)
                )
                if not cust_result:
                    messagebox.showerror("Error", "Invalid Customer selected.")
                    return
                num_cust_id = cust_result[0][0]

                # 3️⃣ Retrieve Staff ID based on Agent Name
                staff_result = executionWithRs_query(
                    "SELECT NUM_USER_ID FROM TM_MST_USER WHERE NUM_USER_ID = %s",
                    (agent_var.get(),)
                )
                if not staff_result:
                    messagebox.showerror("Error", "Invalid Agent selected.")
                    return
                NUM_USER_ID = staff_result[0][0]

                # 4️⃣ Prepare UPDATE SQL
                sql = """
                    UPDATE TM_TRN_TRANSACTION SET 
                        VCH_FILE_NAME = %s,
                        NUM_BANK_ID = %s,
                        NUM_CUST_ID = %s,
                        NUM_ACCOUNT_NO = %s,
                        DTT_STATEMENT_DATE = %s,
                        DTT_TRANSACTION_DATE = %s,
                        VCH_TRN_DESC_1 = %s,
                        VCH_TRN_DESC_2 = %s,
                        VCH_NER = %s,
                        NUM_AMOUNT_CREDIT = %s,
                        NUM_AMOUNT_DEBIT = %s,
                        NUM_STATEMENT_BALANCE = %s,
                        CHR_PRINTED_IND = %s,
                        NUM_USER_ID = %s,
                        NUM_UPDATED_BY = 1,
                        DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur'
                    WHERE NUM_TRN_ID = %s
                """

                params = (
                    file_var.get(),
                    num_bank_id,
                    num_cust_id,
                    account_var.get(),
                    stmt_date_var.get_date(),
                    trx_date_var.get_date(),
                    trx_desc_var.get(),
                    trx_desc2_var.get(),
                    ner_var.get(),
                    float(cr_amt_var.get() or 0),
                    float(dr_amt_var.get() or 0),
                    float(stmt_bal_var.get() or 0),
                    printed_var.get(),
                    NUM_USER_ID,
                    trn_id
                )

                # 5️⃣ Execute the update
                conn = None
                conn = execute_query(sql, params, conn)
                if conn:
                    commit(conn)

                messagebox.showinfo(
                    "Success", "Transaction record updated successfully.")
                popup.destroy()
                self.search()  # refresh search result

            except psycopg2.Error as db_err:
                logger.logger.exception(f"SQL Error: {str(db_err)}")
                messagebox.showerror(
                    "Database Error", f"SQL Error: {db_err.pgerror}")
            except Exception as e:
                logger.logger.exception(
                    f"An unexpected error occurred: {str(e)}")
                messagebox.showerror(
                    "Error", f"An unexpected error occurred: {str(e)}")

        ttk.Button(popup, text="Save", command=save).grid(
            row=11, column=2, padx=10, pady=20)
        ttk.Button(popup, text="Cancel", command=popup.destroy).grid(
            row=11, column=3, padx=10, pady=20)

    def toggle_date_fields(self):
        if self.filter_by_var.get() == "Transaction Date":
            # Show Transaction Date fields
            self.trx_from_label.grid()
            self.trx_from.grid()
            self.trx_to_label.grid()
            self.trx_to.grid()

            # Hide Data Entry Date fields
            self.entry_from_label.grid_remove()
            self.entry_from.grid_remove()
            self.entry_to_label.grid_remove()
            self.entry_to.grid_remove()

        else:
            # Hide Transaction Date fields
            self.trx_from_label.grid_remove()
            self.trx_from.grid_remove()
            self.trx_to_label.grid_remove()
            self.trx_to.grid_remove()

            # Show Data Entry Date fields
            self.entry_from_label.grid()
            self.entry_from.grid()
            self.entry_to_label.grid()
            self.entry_to.grid()

    def adjust_column_width(self):
        for col in self.tree["columns"]:
            if col == "NO.":
                self.tree.column(col, width=2, anchor="center")
            elif col == "Customer Code":
                self.tree.column(col, width=80, anchor="center")
            elif col == "Customer Name":
                self.tree.column(col, width=170, anchor="w")
            elif col == "Account Number":
                self.tree.column(col, width=110, anchor="center")
            elif col == "Target Audience":
                self.tree.column(col, width=150, anchor="w")
            elif col == "File Name":
                self.tree.column(col, width=150, anchor="w")
            elif col == "Transaction Description":
                # ✅ example fixed width, you adjust here
                self.tree.column(col, width=300, anchor="w")
            elif col == "Transaction Date":
                self.tree.column(col, width=130, anchor="center")
            elif col == "Data Entry Date":
                self.tree.column(col, width=130, anchor="center")
            else:
                # default width for unexpected columns
                self.tree.column(col, width=100, anchor="center")
