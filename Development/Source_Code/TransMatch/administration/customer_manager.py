# flake8: noqa: E501

import tkinter as tk
from tkinter import messagebox
import logger
from tkinter import ttk
from db_manager import commit, rollback, execute_query, executionWithRs_query
from administration.contact_country_code import CountryCodePhoneEntry
from administration.customer_remark_popup import RemarkPopup


logger.logger.info("[customer_manager] : Menu initiation")


class CustomerManager:
    def __init__(self, root, login_id):
        self.root = root
        self.customerprofile_window = tk.Toplevel(root)
        self.customerprofile_window.title("Customer Profile Management")

        # === Create Canvas + Scrollbar
        self.main_canvas = tk.Canvas(self.customerprofile_window,
                                     borderwidth=0, background="#f0f0f5")
        scrollbar = tk.Scrollbar(
            self.customerprofile_window, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = tk.Frame(
            self.main_canvas, background="#f0f0f5")

        # === Configure scrollregion
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            )
        )

        self.main_canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw", tags="window")
        self.main_canvas.configure(yscrollcommand=scrollbar.set)

        def resize_scrollable_frame(event):
            self.main_canvas.itemconfig("window", width=event.width)

        self.main_canvas.bind("<Configure>", resize_scrollable_frame)

        # === Pack Canvas and Scrollbar
        self.main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Optional: mouse wheel scrolling
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units")

        self.main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        screen_width = self.scrollable_frame.winfo_screenwidth()
        screen_height = self.scrollable_frame.winfo_screenheight()

        window_width = int(screen_width * 1)
        window_height = int(screen_height * 0.88)

        x_pos = int((screen_width - window_width) / 2)
        y_pos = int((screen_height - window_height) / 5)

        self.customerprofile_window.geometry(
            f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.customerprofile_window.transient(self.root)  # Make it modal-like
        # Prevent interaction with the main window
        self.customerprofile_window.grab_set()
        self.customerprofile_window.focus_force()  # Bring the focus to this window
        self.selected_customer_id = None

        # ── Layer 1: Filter Criteria ───────────────────────
        self.create_filter_section()
        # ── Layer 2: Data Entry (Add/Edit/Delete) ──────────
        self.create_data_entry_section()
        # ── Layer 3: Customer Table ───────────────────────
        self.create_customer_table()
        # to extract all customer info as default behavior
        self.load_customers()
        logger.logger.info("[customer_manager] : Screen establisted completely")

    def create_filter_section(self):
        logger.logger.info("[customer_manager] : Layer 1 - Deploying searching criteria section")

        frame = tk.LabelFrame(self.scrollable_frame,
                              text="Filter Criteria",
                              bg="#f0f0f5", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=(10, 5))

        self.filter_code_var = tk.StringVar()
        self.filter_name_var = tk.StringVar()

        tk.Label(frame, text="Customer Code:", bg="#f0f0f5")\
            .grid(row=0, column=0, sticky="w", padx=5)
        ttk.Entry(frame, textvariable=self.filter_code_var, width=30)\
            .grid(row=0, column=1, padx=5)

        tk.Label(frame, text="Customer Name:", bg="#f0f0f5")\
            .grid(row=0, column=2, sticky="w", padx=5)
        ttk.Entry(frame, textvariable=self.filter_name_var, width=30)\
            .grid(row=0, column=3, padx=5)

        btns = tk.Frame(frame, bg="#f0f0f5")
        btns.grid(row=0, column=4, padx=5)
        ttk.Button(btns, text="🔍 Search",   command=self.search_customers)\
            .pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="🔄 Reset",    command=self.reset_filters)\
            .pack(side=tk.LEFT, padx=3)

    def create_data_entry_section(self):
        logger.logger.info("[customer_manager] : Layer 2 - Deploying data entry section")

        frame = tk.LabelFrame(self.scrollable_frame,
                              text="Data Entry",
                              bg="#f0f0f5", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        # vars for each field
        self.customer_code_var = tk.StringVar()
        self.customer_name_var = tk.StringVar()
        self.customer_email_var = tk.StringVar()
        self.customer_contact_var = tk.StringVar()
        self.customer_address_var = tk.StringVar()

        # Row 0
        tk.Label(frame, text="Customer Code:",    bg="#f0f0f5")\
            .grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.customer_code_var,    width=30)\
            .grid(row=0, column=1, padx=5, pady=2)

        tk.Label(frame, text="Customer Name:",    bg="#f0f0f5")\
            .grid(row=0, column=2, sticky="w", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.customer_name_var,    width=30)\
            .grid(row=0, column=3, padx=5, pady=2)

        # Row 1
        tk.Label(frame, text="Customer Email:",   bg="#f0f0f5")\
            .grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.customer_email_var,   width=30)\
            .grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(frame, text="Customer Contact:").grid(row=1, column=2, sticky="e")
        self.contact_phone_widget = CountryCodePhoneEntry(frame)
        self.contact_phone_widget.grid(row=1, column=3, columnspan=4, padx=5, pady=2, sticky="e")

        # Row 2
        tk.Label(frame, text="Customer Address:", bg="#f0f0f5")\
            .grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.customer_address_var,    width=81)\
            .grid(row=2, column=1, columnspan=3, padx=5, pady=2, sticky="w")

        # Buttons underneath
        btns = tk.Frame(frame, bg="#f0f0f5")
        btns.grid(row=3, column=0, columnspan=4, pady=5)
        ttk.Button(btns, text="➕ Add",    command=self.save_customer)\
            .pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="✏️ Edit",   command=self.edit_customer)\
            .pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="❌ Delete", command=self.delete_customer)\
            .pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="🔄 Reset",  command=self.reset_data_entry)\
            .pack(side=tk.LEFT, padx=5)

    def create_customer_table(self):
        logger.logger.info("[customer_manager] : Layer 3 - Deploying customer data extraction table section")

        frame = tk.LabelFrame(self.scrollable_frame,
                              text="Customer Table",
                              bg="#f0f0f5", padx=10, pady=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        cols = (
            "ID", "Customer Code", "Customer Name",
            "Customer Email", "Customer Contact", "Customer Address",
            "Created Date", "Created By", "Modified Date", "Modified By"
        )
        self.customer_tree = ttk.Treeview(
            frame, columns=cols, show="headings", height=18)

        self.customer_tree.bind("<Double-1>", self.open_remark_popup)

        # self.adjust_column_width()

        # for c in cols:
        #     anchor = "w" if c.startswith("Customer") else "center"
        #     self.customer_tree.heading(c, text=c)
        #     self.customer_tree.column(c, anchor=anchor, width=140)
        # self.customer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Apply heading text
        for c in cols:
            self.customer_tree.heading(c, text=c)

        # 💡 Fix widths and alignment
        self.adjust_column_width()

        # Scroll and pack
        self.customer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # zebra striping
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.customer_tree.tag_configure("evenrow", background="#f5f5f5")
        self.customer_tree.tag_configure("oddrow",  background="#ffffff")

        vsb = ttk.Scrollbar(frame, orient="vertical",
                            command=self.customer_tree.yview)
        self.customer_tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.load_customers()

    def open_remark_popup(self, event):
        selected = self.customer_tree.selection()
        if not selected:
            return
        item = self.customer_tree.item(selected[0])
        cust_id = item["values"][0]

        # Query remark value from DB
        sql = "SELECT VCH_REMARK FROM TM_MST_CUSTOMER WHERE NUM_CUST_ID = %s"
        result = executionWithRs_query(sql, (cust_id,))
        remark = result[0][0] if result else ""

        RemarkPopup(self.customerprofile_window, cust_id, remark, self.load_customers)

    def load_customers(self, code=None, name=None):
        logger.logger.info("[customer_manager] : Extract and Load all customer data into grid table")

        """
        Populate the customer_tree with:
          • all customers if code/name are None or empty
          • or only those matching the filters otherwise.
        """
        # 1) Read filter inputs if none explicitly passed
        if code is None:
            code = self.filter_code_var.get().strip()
        if name is None:
            name = self.filter_name_var.get().strip()

        # 2) Build base query and params list
        base_sql = """
            SELECT
                NUM_CUST_ID
                ,VCH_CUST_CODE
                ,VCH_CUST_NAME
                ,VCH_EMAIL
                ,VCH_CONTACT
                ,VCH_ADDRESS
                ,TO_CHAR(DTT_CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_CREATED_AT
                ,NUM_CREATED_BY
                ,TO_CHAR(DTT_UPDATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_UPDATED_AT
                ,NUM_UPDATED_BY
            FROM TM_MST_CUSTOMER
            WHERE 1=1
        """
        params = []

        # 3) Add filters if provided
        if code:
            base_sql += " AND VCH_CUST_CODE ILIKE %s"
            params.append(f"%{code}%")
        if name:
            base_sql += " AND VCH_CUST_NAME ILIKE %s"
            params.append(f"%{name}%")

        base_sql += " ORDER BY VCH_CUST_CODE"

        # 4) Execute and refresh tree
        rows = executionWithRs_query(base_sql, tuple(params)) or []
        self.customer_tree.delete(*self.customer_tree.get_children())

        for idx, row in enumerate(rows):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.customer_tree.insert("", tk.END, values=row, tags=(tag,))

    def search_customers(self):
        logger.logger.info("[customer_manager] : Executing the SEARCH operation")

        """Called by the 🔍 Search button in Layer 1."""
        # Just re‐load with whatever’s in the filter boxes
        self.load_customers()

    def reset_filters(self):
        logger.logger.info("[customer_manager] : Executing the RESET operation")

        """Clear the filter fields and reload the full list."""
        self.filter_code_var.set("")
        self.filter_name_var.set("")
        self.load_customers()

    def save_customer(self):
        logger.logger.info("[customer_manager] : Executing INSERT/UPDATE based on selection state")

        cust_code = self.customer_code_var.get().strip().upper()
        cust_name = self.customer_name_var.get().strip().upper()
        email = self.customer_email_var.get().strip()
        contact = self.contact_phone_widget.get_full_number().strip()
        address = self.customer_address_var.get().strip()
        staff_id = 1  # Replace later with logged-in staff

        # 1️⃣ Mandatory check
        if not cust_code or not cust_name:
            messagebox.showerror("Missing Info", "Customer Code and Customer Name are mandatory.")
            return

        # 2️⃣ Duplicate Check (exclude current editing row)
        dup_check_sql = """
            SELECT 1 FROM TM_MST_CUSTOMER 
            WHERE UPPER(VCH_CUST_CODE) = %s
            AND NUM_CUST_ID <> COALESCE(%s, -1)
            AND CHR_ACTIVE_IND = 'Y'
        """
        duplicate = executionWithRs_query(dup_check_sql, (cust_code, self.selected_customer_id))
        if duplicate:
            messagebox.showerror("Duplicate", "Customer Code already exists.")
            return

        # 3️⃣ Decide Insert or Update

        if self.selected_customer_id:  # Perform UPDATE
            update_sql = """
                UPDATE TM_MST_CUSTOMER
                SET VCH_CUST_CODE = %s, VCH_CUST_NAME = %s, VCH_EMAIL = %s,
                    VCH_CONTACT = %s, VCH_ADDRESS = %s,
                    NUM_UPDATED_BY = %s, DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur'
                WHERE NUM_CUST_ID = %s
            """
            conn = execute_query(update_sql, (cust_code, cust_name, email, contact, address, staff_id, self.selected_customer_id))
            if conn:
                commit(conn)
                messagebox.showinfo("Success", "Customer updated successfully.")
        else:  # Perform INSERT
            insert_sql = """
                INSERT INTO TM_MST_CUSTOMER (
                    VCH_CUST_CODE, VCH_CUST_NAME, VCH_EMAIL, VCH_CONTACT, VCH_ADDRESS,
                    CHR_ACTIVE_IND, NUM_CREATED_BY
                )
                VALUES (%s, %s, %s, %s, %s, 'Y', %s)
            """
            conn = execute_query(insert_sql, (cust_code, cust_name, email, contact, address, staff_id))
            if conn:
                commit(conn)
                messagebox.showinfo("Success", "Customer added successfully.")

        self.reset_data_entry()
        self.load_customers()

    def edit_customer(self):
        logger.logger.info("[customer_manager] : Triggering edit_customer()")

        selected = self.customer_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a customer to edit.")
            return

        values = self.customer_tree.item(selected[0])['values']
        self.selected_customer_id = values[0]  # NUM_CUST_ID

        self.customer_code_var.set(values[1])
        self.customer_name_var.set(values[2])
        self.customer_email_var.set(values[3])
        self.contact_phone_widget.set_value(str(values[4]))
        self.customer_address_var.set(values[5])

    def delete_customer(self):
        logger.logger.info("[customer_manager] : Executing DELETE operation")
        conn = None

        selected_items = self.customer_tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select at least one customer to delete.")
            return

        # Prompt confirmation
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {len(selected_items)} customer(s)? \n[Alert] This action cannot be undone."
        )
        if not confirm:
            return

        success = True
        try:
            for item in selected_items:
                values = self.customer_tree.item(item)['values']
                customer_id = values[0]
                delete_sql = "DELETE FROM TM_MST_CUSTOMER WHERE NUM_CUST_ID = %s"
                conn = execute_query(delete_sql, (customer_id,), conn)
        except Exception as e:
            logger.logger.error(f"[customer_manager] : Error deleting customer(s): {str(e)}")
            messagebox.showerror("Error", f"Failed to delete customer(s).\n\nError: {e}")
            success = False
        finally:
            if success:
                if conn:
                    commit(conn)
                    logger.logger.info("[customer_manager] : Deletion comitted successfully.")
                logger.logger.info(f"[customer_manager] : Deleted {len(selected_items)} customer(s) successfully.")
                messagebox.showinfo("Deleted", f"Deleted {len(selected_items)} customer(s) successfully.")
            else:
                logger.logger.exception(f"[customer_manager] : Failed to delete for total selected row of {len(selected_items)} customer(s), perform rollback procedure.")
                if conn:
                    rollback(conn)
                    logger.logger.info("[customer_manager] : Deletion rollback successfully.")

        self.load_customers()
        self.reset_data_entry()

    def reset_data_entry(self):
        logger.logger.info("[customer_manager] : Executing the RESET operation, for data entry layer only")

        self.customer_code_var.set("")
        self.customer_name_var.set("")
        self.customer_email_var.set("")
        self.contact_phone_widget.country_code_var.set("+60")
        self.contact_phone_widget.phone_number_var.set("")  
        self.customer_address_var.set("")

    def adjust_column_width(self):
        for col in self.customer_tree["columns"]:
            if col == "ID":
                self.customer_tree.column(col, width=20, anchor="center")
            elif col == "Customer Code":
                self.customer_tree.column(col, width=120, anchor="center")
            elif col == "Customer Name":
                self.customer_tree.column(col, width=220, anchor="w")
            elif col == "Customer Email":
                self.customer_tree.column(col, width=200, anchor="w")
            elif col == "Customer Contact":
                self.customer_tree.column(col, width=100, anchor="center")
            elif col == "Customer Address":
                self.customer_tree.column(col, width=300, anchor="w")
            elif col == "Created By":
                self.customer_tree.column(col, width=50, anchor="center")
            elif col == "Created Date":
                self.customer_tree.column(col, width=100, anchor="center")
            elif col == "Modified By":
                self.customer_tree.column(col, width=50, anchor="center")
            elif col == "Modified Date":
                self.customer_tree.column(col, width=100, anchor="center")
