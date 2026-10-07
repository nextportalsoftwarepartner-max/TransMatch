# flake8: noqa: E501

import tkinter as tk
import logger
import threading
from LoadingPopup import LoadingPopupClass
from tkinter import ttk, messagebox, StringVar, IntVar
from tkcalendar import DateEntry
from db_manager import executionWithRs_query
from datetime import datetime
from transaction.transaction_manager import save_transactions_to_db

logger.logger.info("[transaction_manager_manualInput] : Menu initiation")


def format_currency(value):
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return value


class ManualTransactionInput:
    def __init__(self, root, force_uppercase_callback, login_id):
        self.root = root
        self.force_uppercase = force_uppercase_callback
        self.manual_window = tk.Toplevel(root)
        self.manual_window.title("Manual Data Input")
        # self.manual_window.state('zoomed')
        mnl_screen_width = self.manual_window.winfo_screenwidth()
        mnl_screen_height = self.manual_window.winfo_screenheight()

        window_width = int(mnl_screen_width * 1)
        window_height = int(mnl_screen_height * 0.9)

        x_pos = int((mnl_screen_width - window_width) / 2)
        y_pos = int((mnl_screen_height - window_height) / 5)

        self.manual_window.geometry(
            f"{window_width}x{window_height}+{x_pos}+{y_pos}")

        self.manual_window.transient(self.root)  # Make it modal-like
        self.manual_window.grab_set()  # Prevent interaction with the main window
        self.manual_window.focus_force()  # Bring the focus to this window

        self.manual_static_vars = {}
        self.trans_entry_vars = {}
        self._sort_ascending = {}

        self.setup_ui()
        logger.logger.info("[transaction_manager_manualInput] : Screen establisted completely")

    def setup_ui(self):
        # ===== Layer 1: Static Field Input Layer =====
        logger.logger.info("[transaction_manager_manualInput] : Setup for Layer 1: Static Field Input Layer")
        static_info_frame = tk.LabelFrame(
            self.manual_window, text="Static Info", padx=10, pady=5)
        static_info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.build_static_info_layer(static_info_frame)

        # Reset Button
        ttk.Button(static_info_frame, text="🔄 Reset General Info",
                   command=self.reset_static_info_fields).grid(row=6, column=1, padx=10, pady=5)

        # ===== Layer 2: Transaction Detail Input Layer =====
        logger.logger.info("[transaction_manager_manualInput] : Setup for Layer 2: Transaction Detail Input Layer")
        transaction_frame = tk.LabelFrame(
            self.manual_window, text="Transaction Entry", padx=10, pady=5)
        transaction_frame.pack(fill=tk.X, padx=10, pady=5)

        self.build_transaction_entry_layer(transaction_frame)

        # ===== Layer 3: Grid Table =====
        logger.logger.info("[transaction_manager_manualInput] : Setup for Layer 3: Grid Table")
        table_frame = tk.LabelFrame(
            self.manual_window, text="Transaction Records", padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.build_transaction_table(table_frame)

        # ===== Footer: Save / Reset Data =====
        logger.logger.info("[transaction_manager_manualInput] : Setup for Footer: Save / Reset Data")
        bottom_btns = tk.Frame(self.manual_window, bg="#f0f0f5")
        bottom_btns.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        ttk.Button(
            bottom_btns,
            text="📅 Save",
            command=self.save_tranaction
        ).pack(side=tk.RIGHT, padx=(0, 10))

        ttk.Button(
            bottom_btns,
            text="🔄 Reset All",
            command=self.reset_all
        ).pack(side=tk.RIGHT)

    def build_static_info_layer(self, parent_frame):
        logger.logger.info("[transaction_manager_manualInput] : Begin developing the static info layer content")
        # === Load Bank Dropdown Values ===
        banks_result = executionWithRs_query(
            "SELECT DISTINCT VCH_BANK_NAME FROM TM_MST_BANK WHERE CHR_ACTIVE_IND = 'Y'")
        bank_options = ["Manual Input"] + [b[0]
                                           for b in banks_result] if banks_result else ["Manual Input"]

        self.manual_static_vars = {}

        # === File Name
        tk.Label(parent_frame, text="File Name:").grid(
            row=0, column=0, sticky="e")
        file_var = StringVar()
        file_entry = ttk.Entry(parent_frame, textvariable=file_var, width=40)
        file_entry.grid(row=0, column=1, padx=5, pady=2)
        self.manual_static_vars["File Name"] = file_var

        # === Staff ID (hidden, default = 1)
        staff_var = IntVar(value=1)
        staff_entry = ttk.Entry(
            parent_frame, textvariable=staff_var, width=20, state="readonly")
        staff_label = tk.Label(parent_frame, text="Staff ID:")

        # Hide both label and entry from UI
        staff_label.grid_remove()
        staff_entry.grid_remove()

        # Store in vars dictionary for backend use
        self.manual_static_vars["Staff ID"] = staff_var

        # === Data Entry (hidden, default = "MI")
        data_entry_var = StringVar(value="MI")  # Set backend value
        data_entry_entry = ttk.Entry(
            parent_frame, textvariable=data_entry_var, width=20, state="readonly")
        data_entry_label = tk.Label(parent_frame, text="Data Entry:")

        # Hide both label and field
        data_entry_label.grid_remove()
        data_entry_entry.grid_remove()

        # Store in vars dictionary for backend use
        self.manual_static_vars["Data Entry"] = data_entry_var

        # === Bank Dropdown
        tk.Label(parent_frame, text="Bank:").grid(row=1, column=0, sticky="e")
        bank_dropdown_var = StringVar(value="Manual Input")
        bank_dropdown = ttk.Combobox(
            parent_frame, textvariable=bank_dropdown_var, values=bank_options, state="readonly")
        bank_dropdown.grid(row=1, column=1, padx=5, pady=2)
        self.manual_static_vars["Bank"] = bank_dropdown_var

        # === Bank Name
        tk.Label(parent_frame, text="Bank Name:").grid(
            row=1, column=2, sticky="e")
        bank_name_var = StringVar()
        bank_name_entry = ttk.Entry(
            parent_frame, textvariable=bank_name_var, width=40)
        bank_name_entry.grid(row=1, column=3, padx=5, pady=2)
        self.manual_static_vars["Bank Name"] = bank_name_var

        # === Bank Reg No.
        tk.Label(parent_frame, text="Bank Registration No:").grid(
            row=1, column=4, sticky="e")
        bank_reg_var = StringVar()
        bank_reg_entry = ttk.Entry(
            parent_frame, textvariable=bank_reg_var, width=35)
        bank_reg_entry.grid(row=1, column=5, padx=5, pady=2)
        self.manual_static_vars["Bank Registration No"] = bank_reg_var

        # === Bank Address
        tk.Label(parent_frame, text="Bank Address:").grid(
            row=2, column=0, sticky="e")
        bank_addr_var = StringVar()
        bank_addr_entry = ttk.Entry(
            parent_frame, textvariable=bank_addr_var, width=100)
        bank_addr_entry.grid(row=2, column=1, columnspan=3,
                             padx=5, pady=2, sticky="w")
        self.manual_static_vars["Bank Address"] = bank_addr_var
        bank_addr_entry.bind("<KeyRelease>", lambda e,
                             v=bank_addr_var: self.force_uppercase(v))

        # === Customer Code
        tk.Label(parent_frame, text="Customer Code:").grid(
            row=3, column=0, sticky="e", padx=5, pady=2)
        cust_code_var = StringVar()
        cust_code_entry = ttk.Entry(
            parent_frame, textvariable=cust_code_var, width=20)
        cust_code_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        self.manual_static_vars["Customer Code"] = cust_code_var
        cust_code_entry.bind("<KeyRelease>", lambda e,
                             v=cust_code_var: self.force_uppercase(v))
        cust_code_entry.bind("<FocusOut>", self.on_customer_code_changed)

        # === Customer Name
        tk.Label(parent_frame, text="Customer Name:").grid(
            row=3, column=2, sticky="e", padx=5, pady=2)
        cust_name_var = StringVar()
        cust_name_entry = ttk.Entry(
            parent_frame, textvariable=cust_name_var, width=40)
        cust_name_entry.grid(row=3, column=3, padx=5, pady=2, sticky="w")
        self.manual_static_vars["Customer Name"] = cust_name_var
        cust_name_entry.bind("<KeyRelease>", lambda e,
                             v=cust_name_var: self.force_uppercase(v))

        # === Customer Address
        tk.Label(parent_frame, text="Customer Address:").grid(
            row=4, column=0, sticky="e")
        cust_addr_var = StringVar()
        cust_addr_entry = ttk.Entry(
            parent_frame, textvariable=cust_addr_var, width=100)
        cust_addr_entry.grid(row=4, column=1, columnspan=3,
                             padx=5, pady=2, sticky="w")
        self.manual_static_vars["Customer Address"] = cust_addr_var
        cust_addr_entry.bind("<KeyRelease>", lambda e,
                             v=cust_addr_var: self.force_uppercase(v))

        # === Statement Date (calendar)
        tk.Label(parent_frame, text="Statement Date:").grid(
            row=5, column=0, sticky="e")
        stmt_date = DateEntry(parent_frame, width=20,
                              background='darkblue', foreground='white')
        stmt_date.grid(row=5, column=1, padx=5, pady=2)
        self.manual_static_vars["Statement Date"] = stmt_date

        # === Account Number (numeric only)
        def validate_numeric(P): return P == "" or P.isdigit()
        vcmd = parent_frame.register(validate_numeric)
        tk.Label(parent_frame, text="Account Number:").grid(
            row=5, column=2, sticky="e")
        acct_var = StringVar()
        acct_entry = ttk.Entry(parent_frame, textvariable=acct_var,
                               validate="key", validatecommand=(vcmd, "%P"), width=20)
        acct_entry.grid(row=5, column=3, padx=5, pady=2)
        self.manual_static_vars["Account Number"] = acct_var

        self.manual_static_widgets = {}
        self.manual_static_widgets["Customer Name"] = cust_name_entry
        self.manual_static_widgets["Customer Address"] = cust_addr_entry

        # === Auto-populate logic when Bank is selected
        def on_bank_selected(event=None):
            selected = bank_dropdown_var.get()
            if selected == "Manual Input":
                bank_name_entry.config(state="normal")
                bank_reg_entry.config(state="normal")
                bank_addr_entry.config(state="normal")
                bank_name_var.set("")
                bank_reg_var.set("")
                bank_addr_var.set("")
            else:
                result = executionWithRs_query(
                    """
                    SELECT VCH_BANK_NAME, VCH_BANK_REG_NO, VCH_ADDRESS 
                    FROM TM_MST_BANK 
                    WHERE VCH_BANK_NAME = %s AND CHR_ACTIVE_IND = 'Y'
                    """,
                    (selected,)
                )
                if result:
                    bank_name_var.set(result[0][0])
                    bank_reg_var.set(result[0][1])
                    bank_addr_var.set(result[0][2])
                bank_name_entry.config(state="readonly")
                bank_reg_entry.config(state="readonly")
                bank_addr_entry.config(state="readonly")

        bank_dropdown.bind("<<ComboboxSelected>>", on_bank_selected)

    def build_transaction_entry_layer(self, frame):
        logger.logger.info("[transaction_manager_manualInput] : Begin developing the transaction entry layer content")

        # Create dictionary to hold variables
        self.trans_entry_vars = {}

        # === Row 1 ===
        tk.Label(frame, text="Transaction Date:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2)
        trans_date = DateEntry(frame, width=20,
                               background='darkblue', foreground='white')
        trans_date.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.trans_entry_vars["Transaction Date"] = trans_date

        tk.Label(frame, text="Transaction Description:").grid(
            row=0, column=2, sticky="e", padx=5, pady=2)
        desc1_var = tk.StringVar()
        desc1_entry = ttk.Entry(
            frame, textvariable=desc1_var, width=40)
        desc1_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.trans_entry_vars["Transaction Description"] = desc1_var

        # === Row 2 ===
        tk.Label(frame, text="Transaction Description-Others:").grid(row=1,column=0, sticky="ne", padx=5, pady=2)
        desc_others_text = tk.Text(frame, width=85, height=3)
        desc_others_text.grid(row=1, column=1, columnspan=3,
                              sticky="w", padx=5, pady=2)
        self.trans_entry_vars["Transaction Description-Others"] = desc_others_text

        # === Row 3 ===
        tk.Label(frame, text="Target Audience:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ner_var = tk.StringVar()
        ner_entry = ttk.Entry(frame, textvariable=ner_var, width=40)
        ner_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        self.trans_entry_vars["Target Audience"] = ner_var

        # === Row 4 ===
        def validate_numeric(P):
            return P == "" or P.replace('.', '', 1).isdigit()

        vcmd = (frame.register(validate_numeric), '%P')

        tk.Label(frame, text="Credit Amount:").grid(
            row=3, column=0, sticky="e", padx=5, pady=2)
        cr_amt_var = tk.StringVar()
        cr_amt_entry = ttk.Entry(
            frame, textvariable=cr_amt_var, validate="key", validatecommand=vcmd)
        cr_amt_entry.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        self.trans_entry_vars["Transaction Amount (Credit)"] = cr_amt_var

        tk.Label(frame, text="Debit Amount:").grid(
            row=3, column=2, sticky="e", padx=5, pady=2)
        dr_amt_var = tk.StringVar()
        dr_amt_entry = ttk.Entry(
            frame, textvariable=dr_amt_var, validate="key", validatecommand=vcmd)
        dr_amt_entry.grid(row=3, column=3, sticky="w", padx=5, pady=2)
        self.trans_entry_vars["Transaction Amount (Debit)"] = dr_amt_var

        # === Row 4 ===
        tk.Label(frame, text="Statement Balance:").grid(
            row=4, column=0, sticky="e", padx=5, pady=2)
        stmt_bal_var = tk.StringVar()
        stmt_bal_entry = ttk.Entry(
            frame, textvariable=stmt_bal_var, validate="key", validatecommand=vcmd)
        stmt_bal_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)
        self.trans_entry_vars["Statement Balance"] = stmt_bal_var

        # === Buttons ===
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=5)
        ttk.Button(btn_frame, text="➕ Add", command=self.manual_add_transaction_row).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="✏️ Edit", command=self.manual_edit_transaction_row).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ Delete", command=self.manual_delete_transaction_row).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="🔄 Reset",
                   command=self.clear_manual_transaction_fields).pack(side=tk.LEFT, padx=10)

    def build_transaction_table(self, table_frame):
        logger.logger.info("[transaction_manager_manualInput] : Building for the transaction table")

        columns = [
            "Transaction Date",
            "Transaction Description",
            "Transaction Description-Others",
            "Target Audience",
            "Transaction Amount (Credit)",
            "Transaction Amount (Debit)",
            "Statement Balance"
        ]

        self.manual_data_table = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=5)

        # Sorting toggle state
        self._sort_ascending = {}

        for col in columns:
            self.manual_data_table.heading(
                col,
                text=col,
                command=lambda c=col: self.sort_treeview_column(
                    c, self._sort_ascending.get(c, True))
            )
            self.manual_data_table.column(col, width=180, anchor="center")

        self.manual_data_table.pack(fill=tk.BOTH, expand=True)

        # ─── Bottom Buttons: Save & Reset All ─────────────────────
        bottom_btns = tk.Frame(self.manual_window, bg="#f0f0f5")
        bottom_btns.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # ────────────────────────────────────────────────────────────

    # === Add these methods in your class ===
    # def manual_add_transaction_row(self):
    #     logger.logger.info("[transaction_manager_manualInput] : Executing the ADD operation")
    #     try:
    #         # date = self.trans_entry_vars["Transaction Date"].get_date().strftime("%d/%m")
    #         date = self.trans_entry_vars["Transaction Date"].get_date().strftime(
    #             "%Y-%m-%d")
    #         desc1 = self.trans_entry_vars["Transaction Description"].get()
    #         desc_others = self.trans_entry_vars["Transaction Description-Others"].get(
    #             "1.0", tk.END).strip()
    #         # Clean up newlines and extra spaces
    #         desc_others = " ".join(desc_others.split())
    #         cr_amt = self.trans_entry_vars["Transaction Amount (Credit)"].get()
    #         dr_amt = self.trans_entry_vars["Transaction Amount (Debit)"].get()
    #         stmt_bal = self.trans_entry_vars["Statement Balance"].get()
    #         target_ner = self.trans_entry_vars["Target Audience"].get()

    #         values = [
    #             date, desc1, desc_others, target_ner,
    #             format_currency(cr_amt), format_currency(dr_amt),
    #             format_currency(stmt_bal),
    #         ]

    #         if any(values):
    #             self.manual_data_table.insert("", "end", values=values)
    #             # Clear inputs
    #             self.trans_entry_vars["Transaction Description"].set("")
    #             self.trans_entry_vars["Transaction Description-Others"].delete(
    #                 "1.0", "end")
    #             self.trans_entry_vars["Target Audience"].set("")
    #             self.trans_entry_vars["Transaction Amount (Credit)"].set("")
    #             self.trans_entry_vars["Transaction Amount (Debit)"].set("")
    #             self.trans_entry_vars["Statement Balance"].set("")
    #         else:
    #             messagebox.showwarning(
    #                 "Warning", "Please fill in at least one field before adding.")
    #     except Exception as e:
    #         messagebox.showerror("Error", f"Failed to add row: {str(e)}")

    def manual_add_transaction_row(self):
        logger.logger.info("[transaction_manager_manualInput] : Executing the ADD operation with validation")

        try:
            # Extract and format values
            date = self.trans_entry_vars["Transaction Date"].get_date().strftime("%Y-%m-%d")
            desc1 = self.trans_entry_vars["Transaction Description"].get().strip()
            desc_others = self.trans_entry_vars["Transaction Description-Others"].get("1.0", tk.END).strip()
            desc_others = " ".join(desc_others.split())
            target_ner = self.trans_entry_vars["Target Audience"].get().strip()
            cr_amt = self.trans_entry_vars["Transaction Amount (Credit)"].get().strip()
            dr_amt = self.trans_entry_vars["Transaction Amount (Debit)"].get().strip()
            stmt_bal = self.trans_entry_vars["Statement Balance"].get().strip()

            # === Mandatory Field Validation ===
            if not all([date, desc1, desc_others, target_ner, stmt_bal]):
                messagebox.showwarning("Missing Input", "All fields must be filled in.")
                return

            if not cr_amt and not dr_amt:
                messagebox.showwarning("Amount Required", "Please enter either Credit Amount or Debit Amount.")
                return

            if cr_amt and dr_amt:
                messagebox.showwarning("Invalid Amounts", "You cannot enter both Credit and Debit Amounts.")
                return

            # === Format Values for Insertion ===
            values = [
                date,
                desc1,
                desc_others,
                target_ner,
                format_currency(cr_amt),
                format_currency(dr_amt),
                format_currency(stmt_bal),
            ]

            self.manual_data_table.insert("", "end", values=values)

            # Clear inputs
            self.trans_entry_vars["Transaction Description"].set("")
            self.trans_entry_vars["Transaction Description-Others"].delete("1.0", "end")
            self.trans_entry_vars["Target Audience"].set("")
            self.trans_entry_vars["Transaction Amount (Credit)"].set("")
            self.trans_entry_vars["Transaction Amount (Debit)"].set("")
            self.trans_entry_vars["Statement Balance"].set("")

        except Exception as e:
            logger.logger.error(f"[transaction_manager_manualInput][Exception] : {str(e)}")
            messagebox.showerror("Error", f"Failed to add row: {str(e)}")

    def manual_edit_transaction_row(self):
        logger.logger.info("[transaction_manager_manualInput] : Executing the EDIT operation")

        selected = self.manual_data_table.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a row to edit.")
            return

        values = self.manual_data_table.item(selected[0], 'values')

        # ✅ Transaction Date - use set_date() for DateEntry
        if "Transaction Date" in self.trans_entry_vars:
            self.trans_entry_vars["Transaction Date"].set_date(
                datetime.strptime(values[0], "%Y-%m-%d").date()
            )

        # ✅ Description (StringVar)
        if "Transaction Description" in self.trans_entry_vars:
            self.trans_entry_vars["Transaction Description"].set(values[1])

        # ✅ Description-Others (Text widget)
        if "Transaction Description-Others" in self.trans_entry_vars:
            self.trans_entry_vars["Transaction Description-Others"].delete(
                "1.0", tk.END)
            self.trans_entry_vars["Transaction Description-Others"].insert(
                "1.0", values[2])

        # ✅ Amounts - remove commas before setting values
        self.trans_entry_vars["Target Audience"].set(values[3])
        cr_amt = values[4].replace(",", "") if values[4] else ""
        dr_amt = values[5].replace(",", "") if values[5] else ""
        stmt_bal = values[6].replace(",", "") if values[6] else ""

        self.trans_entry_vars["Transaction Amount (Credit)"].set(cr_amt)
        self.trans_entry_vars["Transaction Amount (Debit)"].set(dr_amt)
        self.trans_entry_vars["Statement Balance"].set(stmt_bal)

        # ✅ Remove the selected row after loading its data
        self.manual_data_table.delete(selected[0])

    def manual_delete_transaction_row(self):
        logger.logger.info("[transaction_manager_manualInput] : Executing the DELETE operation")

        selected = self.manual_data_table.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a row to delete.")
            return

        for row in selected:
            self.manual_data_table.delete(row)

    def reset_all(self):
        logger.logger.info("[transaction_manager_manualInput] : Executing the RESET ALL operation, for entire info and data")

        self.reset_static_info_fields()
        self.clear_manual_transaction_fields()
        for row in self.manual_data_table.get_children():
            self.manual_data_table.delete(row)

    def reset_static_info_fields(self):
        logger.logger.info("[transaction_manager_manualInput] : Executing the RESET ALL operation, for static info layer only")

        for field, var in self.manual_static_vars.items():
            if field in ["Data Entry", "Staff ID"]:
                continue
            if hasattr(var, 'set_date'):
                var.set_date(datetime.today())
            elif hasattr(var, 'set'):
                var.set("")

    def clear_manual_transaction_fields(self):
        logger.logger.info("[transaction_manager_manualInput] : Executing the RESET ALL operation, for transaction detail layer only")

        if "Transaction Date" in self.trans_entry_vars:
            self.trans_entry_vars["Transaction Date"].set_date(
                datetime.today())

        if "Transaction Description" in self.trans_entry_vars:
            self.trans_entry_vars["Transaction Description"].set("")

        if "Transaction Description-Others" in self.trans_entry_vars:
            self.trans_entry_vars["Transaction Description-Others"].delete(
                "1.0", tk.END)

        for field in [
            "Transaction Amount (Credit)",
            "Transaction Amount (Debit)",
                "Statement Balance"]:
            if field in self.trans_entry_vars:
                self.trans_entry_vars[field].set("")

    # def save_tranaction(self):
    #     logger.logger.info("[transaction_manager_manualInput] : Executing the SAVE operation, for all inserted transaction(s) into database")

    #     # ✅ 1. Check if table has any rows
    #     if not self.manual_data_table.get_children():
    #         messagebox.showwarning(
    #             "No Transactions", "No transaction records found in the table.")
    #         return

    #     # ✅ 2. Extract static info
    #     static_info = {k: v.get() if hasattr(v, 'get') else v.get_date().strftime("%d/%m/%y")
    #                    for k, v in self.manual_static_vars.items()}

    #     # ✅ 3. Extract transactions from the table
    #     transactions = []
    #     for row_id in self.manual_data_table.get_children():
    #         values = self.manual_data_table.item(row_id)['values']
    #         transactions.append({
    #             "trn_pdf_date": datetime.strptime(values[0], "%Y-%m-%d").strftime("%d/%m"),
    #             "trn_pdf_description": values[1],
    #             "trn_pdf_description_others": values[2],
    #             "trn_pdf_CR_Amount": float(values[3].replace(",", "")) if values[3] else 0,
    #             "trn_pdf_DR_Amount": float(values[4].replace(",", "")) if values[4] else 0,
    #             "trn_pdf_statementBalance": float(values[5].replace(",", "")) if values[5] else 0,
    #         })

    #     try:
    #         trx_result = save_transactions_to_db(transactions, static_info)
    #         if trx_result:
    #             messagebox.showinfo(
    #                 "Success", "Transactions successfully saved into database.")
    #             logger.logger.info("[transaction_manager_manualInput] : Data saved successfully")
    #             self.reset_all()
    #         else:
    #             messagebox.showerror(
    #                 "Save Failed", "Transactions failed to save. Please check your data and try again.")
    #             logger.logger.info("[transaction_manager_manualInput] : Data failed to save into database")
    #     except Exception as e:
    #         messagebox.showerror(
    #             "Exception", f"An error occurred while saving: {str(e)}")

    def save_tranaction(self):
        logger.logger.info("[transaction_manager_manualInput] : Executing the SAVE operation (with loading)")
        self.loading_popup = LoadingPopupClass(self.root, "Saving transaction...\nPlease wait.")
        self.root.update_idletasks()

        # Start thread for background saving
        thread = threading.Thread(target=self._save_transaction_background)
        thread.start()

    def _save_transaction_background(self):
        try:
            # ✅ 1. Check if table has any rows
            if not self.manual_data_table.get_children():
                self.root.after(0, lambda: [
                    self.loading_popup.close(),
                    messagebox.showwarning("No Transactions", "No transaction records found in the table.")
                ])
                return

            # ✅ 2. Extract static info
            static_info = {
                k: v.get() if hasattr(v, 'get') else v.get_date().strftime("%d/%m/%y")
                for k, v in self.manual_static_vars.items()
            }

            # ✅ 3. Extract transactions from the table
            transactions = []
            for row_id in self.manual_data_table.get_children():
                values = self.manual_data_table.item(row_id)['values']
                transactions.append({
                    "trn_pdf_date": datetime.strptime(values[0], "%Y-%m-%d").strftime("%d/%m"),
                    "trn_pdf_description": values[1],
                    "trn_pdf_description_others": values[2],
                    "trn_pdf_ner": values[3],  # ✅ Add this
                    "trn_pdf_CR_Amount": float(values[4].replace(",", "")) if values[4] else 0,
                    "trn_pdf_DR_Amount": float(values[5].replace(",", "")) if values[5] else 0,
                    "trn_pdf_statementBalance": float(values[6].replace(",", "")) if values[6] else 0,
                })

            trx_result = save_transactions_to_db(transactions, static_info)

            def finish(success):
                self.loading_popup.close()
                if success:
                    messagebox.showinfo("Success", "Transactions successfully saved into database.")
                    self.reset_all()
                    logger.logger.info("[transaction_manager_manualInput] : Data saved successfully")
                else:
                    messagebox.showerror("Save Failed", "Transactions failed to save. Please check your data and try again.")
                    logger.logger.exception("[transaction_manager_manualInput] : Data failed to save")

            self.root.after(0, lambda: finish(trx_result))

        except Exception as e:
            err_msg = str(e)
            logger.logger.exception(f"[transaction_pdf_upload][Exception] : {err_msg}")
            self.root.after(0, lambda: [
                self.loading_popup.close(),
                messagebox.showerror("Exception", f"An error occurred while saving:\n{err_msg}")
            ])

    def on_customer_code_changed(self, event=None):
        cust_code = self.manual_static_vars["Customer Code"].get().strip().upper()
        self.manual_static_vars["Customer Code"].set(cust_code)  # Force uppercase

        if not cust_code:
            return

        # Perform DB query
        query = """
            SELECT VCH_CUST_NAME, VCH_ADDRESS
            FROM TM_MST_CUSTOMER
            WHERE VCH_CUST_CODE = %s AND CHR_ACTIVE_IND = 'Y'
        """
        result = executionWithRs_query(query, (cust_code,))

        cust_name_entry = self.manual_static_widgets["Customer Name"]
        cust_addr_entry = self.manual_static_widgets["Customer Address"]

        if result:
            # Found → auto populate and set readonly
            self.manual_static_vars["Customer Name"].set(result[0][0])
            self.manual_static_vars["Customer Address"].set(result[0][1])
            cust_name_entry.config(state="readonly")
            cust_addr_entry.config(state="readonly")
        else:
            # Not found → allow manual input
            self.manual_static_vars["Customer Name"].set("")
            self.manual_static_vars["Customer Address"].set("")
            cust_name_entry.config(state="normal")
            cust_addr_entry.config(state="normal")
