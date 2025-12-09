# flake8: noqa: E501

import os
import tkinter as tk
import threading
import logger
from LoadingPopup import LoadingPopupClass
from db_manager import executionWithRs_query
from transaction.pdf_processor import pdf_data_extraction_main
from transaction.transaction_manager import save_transactions_to_db
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox


logger.logger.info("[transaction_pdf_upload] : Menu initiation")


class DocxUploader:
    def __init__(self, root, login_id):
        self.root = root
        self.docx_window = tk.Toplevel(root)
        self.docx_window.title("PDF Upload")
        self.docx_window.resizable(True, True)  # ✅ Ensure it is scalable
        system_bg = self.docx_window.cget("bg")  # get default background color of parent window

        # ✅ Set window to 95% width and 90% height, centered
            # screen_width = self.docx_window.winfo_screenwidth()
            # screen_height = self.docx_window.winfo_screenheight()

            # window_width = int(screen_width * 0.95)
            # window_height = int(screen_height * 0.90)

            # x_pos = int((screen_width - window_width) / 2)
            # y_pos = int((screen_height - window_height) / 5)

            # self.docx_window.geometry(
        #     f"{window_width}x{window_height}+{x_pos}+{y_pos}")

        # ✅ Make window fullscreen (cross-platform)
        try:
            # On Windows, maximize (respects taskbar)
            self.docx_window.state("zoomed")
        except:
            # On Mac/Linux, use fullscreen but reduce height a little
            screen_w = self.docx_window.winfo_screenwidth()
            screen_h = self.docx_window.winfo_screenheight()
            self.docx_window.geometry(f"{screen_w}x{screen_h-50}+0+0")

        # ✅ Allow Esc key to exit fullscreen
        self.docx_window.bind("<Escape>", lambda e: self.docx_window.attributes("-fullscreen", False))

        self.docx_window.transient(self.root)  # Make it modal-like
        self.docx_window.grab_set()  # Prevent interaction with the main window
        self.docx_window.focus_force()  # Bring the focus to this window

        logger.logger.info("[transaction_pdf_upload] : Screen establisted completely")

        # Upload field
        content_frame = tk.Frame(self.docx_window, bg=system_bg)
        content_frame.pack(pady=10, padx=10, fill=tk.X)

        tk.Label(content_frame, text="Select PDF File:",
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        self.file_path_entry = ttk.Entry(
            content_frame, font=("Arial", 12), width=100)
        self.file_path_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(content_frame, text="Browse",
                   command=self.browse_file).pack(side=tk.LEFT, padx=5)

        # ✅ Static document info (Dim Text Fields)
        static_info_frame = tk.Frame(
            self.docx_window, bg="lightgray", relief=tk.SUNKEN, bd=2)
        static_info_frame.pack(pady=5, padx=10, fill=tk.X)

        static_fields = ["Staff ID", "Bank Name", "Bank Registration No", "Bank Address", "Customer Code", "Customer Name",
                         "Customer Address", "Statement Date", "Account Number", "Data Entry", "File Name"]

        # Use grid layout: 2 columns, multiple rows
        fields_per_row = 2
        self.static_info_vars = {}

        for index, field in enumerate(static_fields):
            row = index // fields_per_row
            col = (index % fields_per_row) * 2  # 0, 2, 0, 2...

            # Label
            label = tk.Label(static_info_frame, text=f"{field}:", font=(
                "Arial", 10, "bold"), bg="lightgray")
            label.grid(row=row, column=col, padx=5, pady=3, sticky="e")

            # Entry
            var = tk.StringVar()

            if field == "Customer Code":
                widget = ttk.Entry(static_info_frame, font=("Arial", 10), textvariable=var, width=80, state="normal")
                # Bind key release to auto-uppercase immediately
                widget.bind("<KeyRelease>", lambda event, v=var: self.force_uppercase(v))
            elif field == "Statement Date":
                from tkcalendar import DateEntry        
                widget = DateEntry(static_info_frame, textvariable=var, width=37, date_pattern='yyyy-mm-dd')
            else:
                widget = ttk.Entry(static_info_frame, font=("Arial", 10), textvariable=var, width=80, state="readonly")

            widget.grid(row=row, column=col + 1, padx=5, pady=3, sticky="w")

            # ✅ Hide Data Entry but still create it
            if field in ["Data Entry", "File Name"]:
                label.grid_remove()   # ✅ Hide the label
                widget.grid_remove()  # ✅ Hide the text entry field as well

            self.static_info_vars[field] = var

        # Main vertical container (fills whole window)
        main_container = tk.Frame(self.docx_window, bg=system_bg)
        main_container.pack(fill=tk.BOTH, expand=False)

        # Detect screen height and set table container to 40%
        screen_height = self.docx_window.winfo_screenheight()
        table_height = int(screen_height * 0.6)  # 40% of screen height

        table_container = tk.Frame(main_container, height=table_height, bg=system_bg)
        table_container.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        # 🧩 Bottom: Button Frame anchored to bottom
        button_frame = tk.Frame(main_container, bg=system_bg)
        button_frame.pack(fill=tk.X, pady=10)

        # Prevent table from hogging space
        table_container.pack_propagate(False)

        # ✅ Force layout recalculation after fullscreen
        self.docx_window.after(200, self.docx_window.update_idletasks)

        x_scrollbar = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        y_scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.data_table = ttk.Treeview(
            table_container,
            columns=[
                "Transaction Date", "Transaction Description", "Transaction Description-Others",
                "Target Audience", "Credit Amount", "Debit Amount", "Statement Balance"
            ],
            show="headings",
            xscrollcommand=x_scrollbar.set,
            yscrollcommand=y_scrollbar.set,
            height=15
        )

        # Apply zebra styling
        style = ttk.Style()
        style.configure("Treeview", rowheight=28)

        self.data_table.bind("<Double-1>", self.on_double_click)
        self.data_table.pack(fill=tk.BOTH, expand=True)
        self.data_table.tag_configure("evenrow", background="#f5f5f5")  # light grey
        self.data_table.tag_configure("oddrow", background="#ffffff")   # white

        x_scrollbar.config(command=self.data_table.xview)
        y_scrollbar.config(command=self.data_table.yview)

        for col in self.data_table['columns']:
            self.data_table.heading(col, text=col, anchor="center")
            self.data_table.column(col, width=120)

        style = ttk.Style()
        style.configure("BigBold.TButton", font=("Arial", 10, "bold"))
        ttk.Button(button_frame, text="Save", command=self.save_transaction, style="BigBold.TButton").pack(side=tk.LEFT, padx=10, ipady=5)
        ttk.Button(button_frame, text="Reset", command=self.reset_data_trx, style="BigBold.TButton").pack(side=tk.LEFT, padx=10, ipady=5)

        self.docx_window.after(100, self.adjust_column_widths)

    def adjust_column_widths(self):
        self.docx_window.update_idletasks()
        total_width = self.docx_window.winfo_width() or 1000

        column_widths = {
            "Transaction Date": 0.10,
            "Transaction Description": 0.15,
            "Transaction Description-Others": 0.30,
            "Target Audience": 0.15,
            "Credit Amount": 0.10,
            "Debit Amount": 0.10,
            "Statement Balance": 0.10,
        }

        alignment_map = {
            "Transaction Date": "center",
            "Transaction Description": "w",
            "Transaction Description-Others": "w",
            "Target Audience": "w",
            "Credit Amount": "center",
            "Debit Amount": "center",
            "Statement Balance": "center",
        }

        for col in self.data_table["columns"]:
            pct = column_widths.get(col, 0.10)
            anchor = alignment_map.get(col, "w")
            self.data_table.column(col, width=int(total_width * pct), anchor=anchor)

    def browse_file(self):
        logger.logger.info("[transaction_pdf_upload] : Executing the FILE BROWSE operation")

        # self.loading_popup = LoadingPopupClass(self.root, "Extracting PDF Detail... \nPlease wait.")
        # self.root.update_idletasks()  # Forces update to show the popup

        """Allow staff to select a PDF file, extract transaction data, and save output to a file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf")])

        # ✅ Check File name exists
        file_name = os.path.basename(file_path)

        if not file_path:
            logger.logger.info("[transaction_pdf_upload][ERROR] : No file selected")
            if hasattr(self, 'loading_popup'):
                self.loading_popup.close()
            return  # No file selected
        
        # Reset ML choice flags for new file selection
        import dependency_manager
        dependency_manager.reset_ml_choice_flags()
        # Reset ML warning flag so message can be shown again if needed
        from transaction.name_extractor import reset_ml_warning_flag
        reset_ml_warning_flag()

        # Show loading popup (non-blocking)
        self.loading_popup = LoadingPopupClass(self.root, "Extracting PDF Detail...\nPlease wait.")
        self.root.update_idletasks()

        # Run extraction in background
        thread = threading.Thread(
            target=self.extract_pdf_in_background,
            args=(file_path, file_name)
        )
        thread.start()

        # query_check = """
        #     SELECT COUNT(DISTINCT VCH_FILE_NAME) FROM TM_TRN_TRANSACTION
        #     WHERE VCH_FILE_NAME = %s AND CHR_ACTIVE_IND = 'Y'
        # """
        # existing = executionWithRs_query(query_check, (file_name,))
        # if existing and existing[0][0] > 0:
        #     logger.logger.info("[transaction_pdf_upload] : Duplicated File Name")
        #     self.loading_popup.close()
        #     messagebox.showerror(
        #         "Duplicated File Name",
        #         "The uploaded bank statement already exists in the system.\n"
        #         "Please upload another new PDF docx."
        #     )
        #     return

        # logger.logger.info("[transaction_pdf_upload] : File Name not exists, proceed to file upload activity")

        # self.file_path_entry.delete(0, tk.END)
        # self.file_path_entry.insert(0, file_path)

        # trn_pdf_extracted_data = pdf_data_extraction_main(file_path)
        # logger.logger.info("[transaction_pdf_upload] : Successfully returned from function -> pdf_processor()")

        # self.trn_pdf_pop_gridtbl(
        #     trn_pdf_extracted_data["Document Info"], trn_pdf_extracted_data["Transactions"], file_name)

        # self.loading_popup.close()

    def extract_pdf_in_background(self, file_path, file_name):
        try:
            # 🧠 Do duplication check
            query_check = """
                SELECT COUNT(DISTINCT VCH_FILE_NAME) FROM TM_TRN_TRANSACTION
                WHERE VCH_FILE_NAME = %s AND CHR_ACTIVE_IND = 'Y'
            """
            existing = executionWithRs_query(query_check, (file_name,))
            if existing and existing[0][0] > 0:
                self.root.after(0, lambda: [
                    self.loading_popup.close(),
                    messagebox.showerror("Duplicated File Name",
                                        "The uploaded bank statement already exists in the system.\nPlease upload another new PDF docx.")
                ])
                return

            logger.logger.info("[transaction_pdf_upload] : File Name not exists, proceed to file upload activity")

            trn_pdf_extracted_data = pdf_data_extraction_main(file_path)
            logger.logger.info("[transaction_pdf_upload] : Successfully returned from function -> pdf_processor()")

            # Safely update UI from main thread
            self.root.after(0, lambda: self.after_pdf_extraction(trn_pdf_extracted_data, file_name, file_path))

        except Exception as e:
            error_msg = str(e)
            error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
            logger.logger.error(f"[transaction_pdf_upload][Exception] : {error_msg}")
            if error_code:
                logger.logger.error(f"[transaction_pdf_upload][Exception] : Error code: {error_code}")
            logger.logger.exception("Full exception traceback:")
            
            # Provide more helpful error message for access violation
            if "3221225781" in error_msg or (isinstance(e, OSError) and hasattr(e, 'winerror') and e.winerror == 3221225781):
                detailed_msg = (
                    "Access Violation Error (0xC0000005)\n\n"
                    "This usually means Poppler or Tesseract executables cannot find their required DLLs.\n\n"
                    "Please ensure:\n"
                    "1. All Poppler DLLs are in _internal/poppler/Library/bin/\n"
                    "2. All Tesseract DLLs are accessible\n"
                    "3. Try rebuilding with: python build_and_package.py\n\n"
                    f"Original error: {error_msg}"
                )
                self.root.after(0, lambda: messagebox.showerror("PDF Processing Error", detailed_msg))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, self.loading_popup.close)

    def after_pdf_extraction(self, extracted_data, file_name, file_path):
        self.file_path_entry.delete(0, tk.END)
        self.file_path_entry.insert(0, file_path)

        try:
            self.trn_pdf_pop_gridtbl(extracted_data["Document Info"], extracted_data["Transactions"], file_name)
        except Exception as e:
            logger.logger.exception(f"[after_pdf_extraction][Exception] : trn_pdf_pop_gridtbl() : {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            self.loading_popup.close()

    def trn_pdf_pop_gridtbl(self, pdf_docInfo, pdf_trxInfos, file_name):
        logger.logger.info("[transaction_pdf_upload] : Append all documentation statis info and transcation(s) into grid table")

        """Display extracted document info from PDF into the dim fields"""
        # ✅ Add file name to static_info_vars
        self.static_info_vars["File Name"].set(file_name)  # Store file name
        self.static_info_vars["Staff ID"].set(1)  # Store staff id
        self.static_info_vars["Data Entry"].set("PU")  # Store Data Entry (PU: PDF Upload)

        # ✅ Extract Bank Name, Statement Date, Account Number
        for field in ["Bank Name", "Bank Registration No", "Bank Address", "Customer Code", "Customer Name", "Customer Address", "Statement Date", "Account Number"]:
            if field in self.static_info_vars:
                self.static_info_vars[field].set(pdf_docInfo.get(field, ""))

        customer_code = pdf_docInfo.get("Customer Code", "").strip()
        customer_name = pdf_docInfo.get("Customer Name", "").strip()

        if customer_name:
            query = "SELECT VCH_CUST_CODE FROM TM_MST_CUSTOMER WHERE VCH_CUST_NAME = %s AND CHR_ACTIVE_IND = 'Y'"
            result = executionWithRs_query(query, (customer_name,))
            if result:
                self.static_info_vars["Customer Code"].set(result[0][0])
                # Dim the field
                if customer_code:
                    customer_code.config(state="readonly")
            else:
                # Allow user to key in
                if customer_code:
                    customer_code.config(state="normal")

        """Display extracted transactions from PDF in the table"""
        self.data_table.delete(
            *self.data_table.get_children())  # Clear existing data

        for index, pdf_trxInfo in enumerate(pdf_trxInfos):
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            self.data_table.insert("", "end", values=(
                pdf_trxInfo.get("trn_pdf_date", ""),
                pdf_trxInfo.get("trn_pdf_description", ""),
                pdf_trxInfo.get("trn_pdf_description_others", ""),
                pdf_trxInfo.get("trn_pdf_ner", ""),
                pdf_trxInfo.get("trn_pdf_CR_Amount", ""),
                pdf_trxInfo.get("trn_pdf_DR_Amount", ""),
                pdf_trxInfo.get("trn_pdf_statementBalance", "")
            ), tags=(tag,))

        # ✅ Display transaction count in status label (bottom right)
        if hasattr(self, "transaction_count_label"):
            self.transaction_count_label.config(text=f"Total Transactions: {len(pdf_trxInfos)}")
        else:
            # Create the label once if not exist
            self.transaction_count_label = tk.Label(self.docx_window, text=f"Total Transactions: {len(pdf_trxInfos)}", anchor="e", font=("Arial", 10))
            self.transaction_count_label.pack(side=tk.BOTTOM, anchor="e", padx=50, pady=(0, 5))

    def save_transaction(self):
        logger.logger.info("[transaction_pdf_upload] : Executing the SAVE operation (with loading)")
        self.loading_popup = LoadingPopupClass(self.root, "Saving transaction...\nPlease wait.")
        self.root.update_idletasks()

        thread = threading.Thread(target=self._save_transaction_background)
        thread.start()

    def reset_data_trx(self):
        logger.logger.info("[transaction_pdf_upload] : Executing the RESET operation")

        # Reset file path and clear table
        self.file_path_entry.delete(0, tk.END)
        for row in self.data_table.get_children():
            self.data_table.delete(row)

        # ─── Reset all static info fields ───────────────────
        for var in self.static_info_vars.values():
            var.set("")
        # ─────────────────────────────────────────────────────

        # Reset Total Record Count
        self.transaction_count_label.config(text="Total Transactions: 0")

        print("Data reset successfully.")

    def force_uppercase(self, var):
        current_value = var.get()
        var.set(current_value.upper())

    def on_double_click(self, event):
        # Identify where user clicked
        region = self.data_table.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.data_table.identify_column(event.x)
        row = self.data_table.identify_row(event.y)

        if not row:
            return

        col_num = int(column.replace('#', '')) - 1  # zero-based index

        # Only allow edit on column "Target Audience" (column index 3)
        if col_num != 3:
            return

        # Get cell bbox
        x, y, width, height = self.data_table.bbox(row, column)
        value = self.data_table.set(row, column)

        # Create Entry widget for editing
        self.edit_entry = ttk.Entry(self.data_table, width=30)
        self.edit_entry.place(x=x, y=y, width=width, height=height)
        self.edit_entry.insert(0, value)
        self.edit_entry.focus()

        def save_edit(event=None):
            new_value = self.edit_entry.get()
            self.data_table.set(row, column, new_value)
            self.edit_entry.destroy()

        self.edit_entry.bind("<Return>", save_edit)
        self.edit_entry.bind("<FocusOut>", save_edit)

    def _save_transaction_background(self):
        try:
            entered_cust_code = self.static_info_vars.get("Customer Code", "").get().strip()
            if not entered_cust_code:
                self.root.after(0, lambda: [
                    self.loading_popup.close(),
                    messagebox.showerror("Customer Code is a mandatory field",
                                        "Please enter a valid customer code for this transaction upload.")
                ])
                return

            check_query = "SELECT 1 FROM TM_MST_CUSTOMER WHERE VCH_CUST_CODE = %s"
            check_result = executionWithRs_query(check_query, (entered_cust_code,))
            if check_result:
                entered_cust_name = self.static_info_vars.get("Customer Name", "").get().strip()
                check_query_2 = "SELECT 1 FROM TM_MST_CUSTOMER WHERE VCH_CUST_CODE = %s AND VCH_CUST_NAME = %s"
                check_result_2 = executionWithRs_query(check_query_2, (entered_cust_code, entered_cust_name))

                if not check_result_2:
                    self.root.after(0, lambda: [
                        self.loading_popup.close(),
                        messagebox.showerror("Duplicate Customer Code",
                                            f"The customer code '{entered_cust_code}' already exists for another customer name.\nPlease enter a new unique customer code.")
                    ])
                    return

            static_info = {key: var.get() for key, var in self.static_info_vars.items()}
            transactions = []
            for row_id in self.data_table.get_children():
                values = self.data_table.item(row_id)['values']
                transactions.append({
                    "trn_pdf_date": values[0],
                    "trn_pdf_description": values[1],
                    "trn_pdf_description_others": values[2],
                    "trn_pdf_ner": values[3],
                    "trn_pdf_CR_Amount": values[4],
                    "trn_pdf_DR_Amount": values[5],
                    "trn_pdf_statementBalance": values[6],
                })

            trx_ins_stat = save_transactions_to_db(transactions, static_info)

            def finalize():
                self.loading_popup.close()
                if trx_ins_stat:
                    messagebox.showinfo("Success", "Transactions successfully saved into database.")
                    self.reset_data_trx()
                    logger.logger.info("[transaction_pdf_upload] : Transactions successfully saved into database")
                else:
                    messagebox.showerror("Failure", "Error Code: [1001]\nTransactions failed to save into database.\nFor further assistance, contact the IT department.")
                    logger.logger.info("[transaction_pdf_upload][ERROR] : Error Code: [1001] - Transactions failed to save into database")

            self.root.after(0, finalize)

        except Exception as e:
            self.root.after(0, lambda: [
                self.loading_popup.close(),
                messagebox.showerror("Error", f"Failed to save transactions.\n{str(e)}")
            ])
            logger.logger.info(f"[transaction_pdf_upload][Exception] : {str(e)}")
