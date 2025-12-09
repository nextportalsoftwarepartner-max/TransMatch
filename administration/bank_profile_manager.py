# flake8: noqa: E501

import tkinter as tk
import logger
from tkinter import ttk, messagebox
from db_manager import commit, execute_query, executionWithRs_query


class BankProfileManager:
    def __init__(self, root, login_id):
        logger.logger.info("[BankProfileManager] Initialized Bank Profile screen")
        self.root = root
        self.bank_profile_window = tk.Toplevel(root)
        self.bank_profile_window.title("Bank Profile Management")

        screen_width = self.bank_profile_window.winfo_screenwidth()
        screen_height = self.bank_profile_window.winfo_screenheight()

        window_width = int(screen_width * 1)
        window_height = int(screen_height * 0.9)
        x_pos = int((screen_width - window_width) / 2)
        y_pos = int((screen_height - window_height) / 5)

        self.bank_profile_window.geometry(
            f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.bank_profile_window.transient(self.root)
        self.bank_profile_window.grab_set()
        self.bank_profile_window.focus_force()

        self.selected_bank_id = None
        self.selected_bank_name = None

        self.create_header()
        self.create_filter_layer()
        self.create_entry_layer()
        self.create_grid_layer()
        self.create_footer()
        self.load_bank_profiles()

    def create_header(self):
        header_frame = tk.Frame(self.bank_profile_window,
                                bg="#4CAF50", height=60)
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="Bank Profile Management", font=("Helvetica", 18, "bold"),
                 bg="#4CAF50", fg="white").pack(pady=10)

    def create_filter_layer(self):
        filter_frame = tk.LabelFrame(
            self.bank_profile_window, text="Filter Criteria", bg="white", font=("Helvetica", 12))
        filter_frame.pack(fill=tk.X, padx=20, pady=10)

        self.search_bank_name_var = tk.StringVar()
        tk.Label(filter_frame, text="Bank Name:", bg="white").grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(filter_frame, textvariable=self.search_bank_name_var, width=40).grid(
            row=0, column=1, padx=10, pady=5, sticky="w")

        btn_frame = tk.Frame(filter_frame, bg="white")
        btn_frame.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        ttk.Button(btn_frame, text="🔍 Search",
                   command=self.load_bank_profiles).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Reset", command=self.reset_filters).pack(
            side=tk.LEFT, padx=5)

    def create_entry_layer(self):
        entry_frame = tk.LabelFrame(
            self.bank_profile_window, text="Bank Entry", bg="white", font=("Helvetica", 12))
        entry_frame.pack(fill=tk.X, padx=20, pady=10)

        self.bank_name_var = tk.StringVar()
        self.bank_display_var = tk.StringVar()
        self.bank_reg_no_var = tk.StringVar()
        self.bank_address_var = tk.StringVar()

        tk.Label(entry_frame, text="Bank Name:", bg="white").grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.bank_name_var, width=40).grid(
            row=0, column=1, padx=10, pady=5, sticky="w")

        tk.Label(entry_frame, text="Display Name:", bg="white").grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.bank_display_var, width=40).grid(
            row=1, column=1, padx=10, pady=5, sticky="w")

        tk.Label(entry_frame, text="Registration No.:", bg="white").grid(
            row=0, column=2, padx=10, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.bank_reg_no_var, width=40).grid(
            row=0, column=3, padx=10, pady=5, sticky="w")

        tk.Label(entry_frame, text="Address:", bg="white").grid(
            row=1, column=2, padx=10, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.bank_address_var, width=60).grid(
            row=1, column=3, padx=10, pady=5, sticky="w")

        btn_frame = tk.Frame(entry_frame, bg="white")
        btn_frame.grid(row=2, columnspan=4, pady=10)
        ttk.Button(btn_frame, text="➕ Add", command=self.save_bank).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="✏️ Edit", command=self.edit_bank).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ Delete", command=self.delete_bank).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="🔄 Reset", command=self.reset_entry_fields).pack(
            side=tk.LEFT, padx=10)

    def create_grid_layer(self):
        grid_frame = tk.LabelFrame(
            self.bank_profile_window, text="Bank List", bg="white", font=("Helvetica", 12))
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ["Bank ID", "Bank Name", "Display Name", "Reg No.", "Address", "Active",
                   "Created By", "Created At", "Updated By", "Updated At"]
        self.grid_table = ttk.Treeview(
            grid_frame, columns=columns, show="headings")

        for col in columns:
            self.grid_table.heading(col, text=col)
            self.grid_table.column(col, anchor="w", width=180)

        self.adjust_column_width()

        y_scroll = ttk.Scrollbar(
            grid_frame, orient="vertical", command=self.grid_table.yview)
        self.grid_table.configure(yscrollcommand=y_scroll.set)
        self.grid_table.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

    def create_footer(self):
        footer_frame = tk.Frame(self.bank_profile_window, bg="#4CAF50")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        tk.Label(footer_frame, text="Contact Helpdesk: Email: Euwin@example.com | Phone: +60 16-284 3121",
                 font=("Helvetica", 10), bg="#4CAF50", fg="white").pack()

    def load_bank_profiles(self):
        logger.logger.info("[BankProfileManager] Loading bank profile records")

        self.grid_table.delete(*self.grid_table.get_children())
        name_filter = self.search_bank_name_var.get().strip()
        sql = """
            SELECT NUM_BANK_ID, VCH_BANK_NAME, VCH_BANK_DISPLAY_NM, VCH_BANK_REG_NO, VCH_ADDRESS,
                CASE WHEN CHR_ACTIVE_IND = 'Y' THEN 'YES' ELSE 'NO' END,
                NUM_CREATED_BY, TO_CHAR(DTT_CREATED_AT, 'YYYY-MM-DD HH24:MI:SS'),
                NUM_UPDATED_BY, TO_CHAR(DTT_UPDATED_AT, 'YYYY-MM-DD HH24:MI:SS')
            FROM TM_MST_BANK
            WHERE (%s = '' OR VCH_BANK_NAME ILIKE %s)
            ORDER BY NUM_BANK_ID
        """
        rows = executionWithRs_query(sql, (name_filter, f"%{name_filter}%"))
        logger.logger.info(f"[BankProfileManager] Loaded {len(rows or [])} records")

        for row in rows or []:
            self.grid_table.insert("", tk.END, values=(
                row[0], row[1], row[2], row[3], row[4], row[5],
                row[6], row[7], row[8], row[9]
            ))

    def reset_filters(self):
        self.search_bank_name_var.set("")
        self.load_bank_profiles()

    def reset_entry_fields(self):
        self.bank_name_var.set("")
        self.bank_display_var.set("")
        self.bank_reg_no_var.set("")
        self.bank_address_var.set("")
        self.selected_bank_id = None
        self.selected_bank_name = None

    def edit_bank(self):
        selected = self.grid_table.selection()
        if not selected:
            messagebox.showwarning(
                "Selection", "Please select a record to edit.")
            return
        values = self.grid_table.item(selected[0], "values")
        self.selected_bank_id = values[0]
        self.bank_name_var.set(values[1])
        self.bank_display_var.set(values[2])
        self.bank_reg_no_var.set(values[3])
        self.bank_address_var.set(values[4])
        self.selected_bank_name = values[1]
        logger.logger.info(f"[BankProfileManager] Editing bank ID: {self.selected_bank_id}")

    def delete_bank(self):
        if not self.selected_bank_id:
            messagebox.showwarning(
                "Delete", "Please select a record to delete.")
            return
        confirm = messagebox.askyesno(
            "Delete Confirmation", "Are you sure you want to delete this bank?")
        if not confirm:
            return

        sql = "DELETE FROM TM_MST_BANK WHERE NUM_BANK_ID = %s"
        try:
            logger.logger.warning(f"[BankProfileManager] Attempting to delete bank ID: {self.selected_bank_id}")
            execute_query(sql, (self.selected_bank_id,))
            messagebox.showinfo("Success", "Bank deleted successfully.")
            self.load_bank_profiles()
            self.reset_entry_fields()
        except Exception as e:
            logger.logger.error(f"[BankProfileManager] Failed to delete bank: {e}")
            messagebox.showerror("Error", str(e))

    def save_bank(self):
        if not self.bank_name_var.get():
            messagebox.showwarning("Validation", "Bank Name cannot be empty.")
            return

        logger.logger.info(f"[BankProfileManager] {'Updating' if self.selected_bank_name else 'Inserting'} bank: {self.bank_name_var.get()}")

        display_name = self.bank_display_var.get(
        ).strip() or self.bank_name_var.get().strip()

        if self.selected_bank_id:
            sql = """
                UPDATE TM_MST_BANK
                SET VCH_BANK_NAME = %s,
                    VCH_BANK_DISPLAY_NM = %s,
                    VCH_BANK_REG_NO = %s,
                    VCH_ADDRESS = %s,
                    CHR_ACTIVE_IND = 'Y',
                    NUM_UPDATED_BY = 1,
                    DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur'
                WHERE NUM_BANK_ID = %s
            """
            data = (
                self.bank_name_var.get().strip(),
                display_name,
                self.bank_reg_no_var.get().strip(),
                self.bank_address_var.get().strip(),
                self.selected_bank_id
            )
        else:
            sql = """
                INSERT INTO TM_MST_BANK (VCH_BANK_NAME, VCH_BANK_DISPLAY_NM, VCH_BANK_REG_NO, VCH_ADDRESS, CHR_ACTIVE_IND, NUM_CREATED_BY)
                VALUES (%s, %s, %s, %s, 'Y', 1)
            """
            data = (
                self.bank_name_var.get().strip(),
                display_name,
                self.bank_reg_no_var.get().strip(),
                self.bank_address_var.get().strip()
            )

        try:
            conn = None
            conn = execute_query(sql, data, conn)
            if conn:
                commit(conn)
            messagebox.showinfo("Success", "Bank saved successfully.")
            self.load_bank_profiles()
            self.reset_entry_fields()
        except Exception as e:
            logger.logger.error(f"[BankProfileManager] Failed to save bank: {e}")
            messagebox.showerror("Error", str(e))

    def adjust_column_width(self):
        for col in self.grid_table["columns"]:
            if col == "Bank ID":
                self.grid_table.column(col, width=5, anchor="center")
            elif col == "Bank Name":
                self.grid_table.column(col, width=100, anchor="w")
            elif col == "Display Name":
                self.grid_table.column(col, width=50, anchor="w")
            elif col == "Reg No.":
                self.grid_table.column(col, width=100, anchor="w")
            elif col == "Address":
                self.grid_table.column(col, width=250, anchor="w")
            elif col == "Active":
                self.grid_table.column(col, width=30, anchor="center")
            elif col == "Created By":
                self.grid_table.column(col, width=100, anchor="center")
            elif col == "Created At":
                self.grid_table.column(col, width=160, anchor="center")
            elif col == "Updated By":
                self.grid_table.column(col, width=100, anchor="center")
            elif col == "Updated At":
                self.grid_table.column(col, width=160, anchor="center")
