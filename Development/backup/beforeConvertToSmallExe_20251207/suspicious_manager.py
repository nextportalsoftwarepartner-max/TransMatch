# flake8: noqa: E501

import tkinter as tk
import shutil
import sys
import os
import openpyxl
import logger
from datetime import datetime
from db_manager import execute_query, commit, executionWithRs_query
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog

logger.logger.info("[suspicious_manager] : Menu initiation")


class SuspiciousManager:
    def __init__(self, root, login_id):
        self.root = root
        self.blacklist_window = tk.Toplevel(root)
        self.blacklist_window.title("Suspicious Management")

        # === Create Canvas + Scrollbar
        self.main_canvas = tk.Canvas(self.blacklist_window,
                                     borderwidth=0, background="#f0f0f5")
        scrollbar = tk.Scrollbar(
            self.blacklist_window, orient="vertical", command=self.main_canvas.yview)
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

        self.blacklist_window.geometry(
            f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.blacklist_window.transient(self.root)  # Make it modal-like
        self.blacklist_window.grab_set()  # Prevent interaction with the main window
        self.blacklist_window.focus_force()  # Bring the focus to this window

        # Layer 1: Filter Criteria
        self.create_filter_section()
        # Layer 2: Data Entry
        self.create_data_entry_section()
        # Layer 3: Suspicious Table
        self.create_suspicious_table()
        logger.logger.info("[suspicious_manager] : Screen establisted completely")

    def create_filter_section(self):
        logger.logger.info("[suspicious_manager] : Layer 1 - Deploying searching criteria section")

        frame = tk.LabelFrame(self.scrollable_frame,
                              text="Filter Criteria",
                              bg="#f0f0f5", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=(10, 5))

        # To filter by the name using ILIKE
        self.bl_filter_var = tk.StringVar()
        tk.Label(frame, text="Suspicious Name:", bg="#f0f0f5")\
            .grid(row=0, column=0, sticky="w", padx=5)
        ttk.Entry(frame, textvariable=self.bl_filter_var, width=30)\
            .grid(row=0, column=1, padx=5)

        # To filter is the transaction exists in blacklisted
        self.exists_in_blacklisted_var = tk.StringVar(value="All")
        tk.Label(frame, text="Exists In Blacklisted?", bg="#f0f5f5")\
            .grid(row=0, column=2, sticky="w", padx=5)
        exists_cb = ttk.Combobox(
            frame,
            textvariable=self.exists_in_blacklisted_var,
            state="readonly",
            values=["All", "Yes", "No"]
        )
        exists_cb.grid(row=0, column=3, padx=5)

        # Buttons
        btns = tk.Frame(frame, bg="#f0f0f5")
        btns.grid(row=0, column=4, padx=5)
        ttk.Button(btns, text="🔍 Search", command=self.search_Suspicious)\
            .pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="🔄 Reset",  command=self.reset_filter)\
            .pack(side=tk.LEFT, padx=5)

    def search_Suspicious(self):
        logger.logger.info("[suspicious_manager] : Executing the SEARCH operation")

        name_filter = self.bl_filter_var.get().strip()
        match_option = self.exists_in_blacklisted_var.get()  # All / Yes / No

        self.bl_tree.delete(*self.bl_tree.get_children())

        # Base SQL
        query = """
            SELECT 
                s.VCH_SUSPICIOUS_NAME,
                TO_CHAR(s.DTT_CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_CREATED_AT,
                s.NUM_CREATED_BY,
                TO_CHAR(s.DTT_UPDATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_UPDATED_AT,
                s.NUM_UPDATED_BY,
                CASE WHEN b.VCH_BLACKLISTED_NAME IS NOT NULL THEN 'Yes' ELSE 'No' END AS exists_in_blacklist
            FROM TM_MST_SUSPICIOUS s
            LEFT JOIN TM_MST_BLACKLISTED b
                ON TRIM(LOWER(s.VCH_SUSPICIOUS_NAME)) = TRIM(LOWER(b.VCH_BLACKLISTED_NAME))
            WHERE s.CHR_ACTIVE_IND = 'Y'
        """

        params = []

        if name_filter:
            query += " AND s.VCH_SUSPICIOUS_NAME ILIKE %s"
            params.append(f"%{name_filter}%")

        if match_option == "Yes":
            query += " AND b.VCH_BLACKLISTED_NAME IS NOT NULL"
        elif match_option == "No":
            query += " AND b.VCH_BLACKLISTED_NAME IS NULL"

        query += " ORDER BY s.VCH_SUSPICIOUS_NAME"

        try:
            rows = executionWithRs_query(query, tuple(params)) or []

            for idx, row in enumerate(rows):
                tag = "evenrow" if idx % 2 == 0 else "oddrow"
                self.bl_tree.insert("", tk.END, values=row, tags=(tag,))
        except Exception as e:
            messagebox.showerror("Search Error", f"An error occurred:\n{e}")

        # Footer to show the total number of record
        self.total_label.config(text=f"Total Records: {len(rows)}")

    def reset_filter(self):
        logger.logger.info("[suspicious_manager] : Executing the RESET operation")

        self.bl_filter_var.set("")
        self.load_suspicious_from_db()  # ✅ Refresh table

    def create_data_entry_section(self):
        logger.logger.info("[suspicious_manager] : Layer 2 - Deploying data entry section")

        frame = tk.LabelFrame(self.scrollable_frame,
                              text="Data Entry",
                              bg="#f0f0f5", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        # Browse and Download Template Buttons
        btn_frame = tk.Frame(frame, bg="#f0f0f5")
        btn_frame.grid(row=0, column=0, padx=5, sticky="w")

        ttk.Button(btn_frame, text="Download Template", command=self.download_template)\
            .pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Import", command=self.import_excel)\
            .pack(side=tk.LEFT, padx=(0, 5))

        # Suspicious Name input
        tk.Label(frame, text="Suspicious Name:", bg="#f0f0f5")\
            .grid(row=0, column=1, sticky="w", padx=5)
        self.bl_name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.bl_name_var, width=30)\
            .grid(row=0, column=2, padx=5)

        # Add / Edit / Delete buttons
        btns = tk.Frame(frame, bg="#f0f0f5")
        btns.grid(row=0, column=3, padx=5)
        ttk.Button(btns, text="➕ Add",    command=self.save_transaction)\
            .pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="✏️ Edit",   command=self.edit_Suspicious)\
            .pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="❌ Delete", command=self.delete_Suspicious)\
            .pack(side=tk.LEFT, padx=3)

    def import_excel(self):
        logger.logger.info("[suspicious_manager] : Executing the excel IMPORT operation")

        fn = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx;*.xls")])
        if not fn:
            return

        try:
            wb = openpyxl.load_workbook(fn)
            ws = wb.active

            today = datetime.now()
            conn = None
            inserted = 0

            for row in ws.iter_rows(min_row=2, values_only=True):
                name = row[0] if row and row[0] else ""
                if not name:
                    continue

                query = """
                    INSERT INTO TM_MST_SUSPICIOUS (
                        VCH_SUSPICIOUS_NAME, VCH_REMARK_1, VCH_REMARK_2,
                        CHR_ACTIVE_IND, NUM_CREATED_BY, DTT_CREATED_AT
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (name.strip(), "", "", "Y", 1, today)
                conn = execute_query(query, params, conn)
                inserted += 1

            if conn:
                commit(conn)

            messagebox.showinfo("Success", f"{inserted} rows imported successfully.")
            self.load_suspicious_from_db()  # ✅ Refresh table

        except Exception as e:
            messagebox.showerror("Error", f"Failed to import Excel:\n{e}")

    def edit_Suspicious(self):
        logger.logger.info("[suspicious_manager] : Executing the EDIT operation")

        sel = self.bl_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a row to edit.")
            return

        # ✅ Extract selected row values
        values = self.bl_tree.item(sel[0], "values")
        self.bl_name_var.set(values[0])          # Set name to input box
        self.selected_edit_id = values[0]         # Store the original name for update reference

    def delete_Suspicious(self):
        logger.logger.info("[suspicious_manager] : Executing the DELETE operation")

        selected_items = self.bl_tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select record(s) to delete.")
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            "Are you sure you want to delete the selected record(s)? This action cannot be undone."
        )

        if not confirm:
            return

        delete_query = """
            DELETE FROM TM_MST_SUSPICIOUS
            WHERE VCH_SUSPICIOUS_NAME = %s AND CHR_ACTIVE_IND = 'Y'
        """

        conn = None
        deleted = 0

        for row_id in selected_items:
            values = self.bl_tree.item(row_id, "values")
            name = values[0]
            try:
                conn = execute_query(delete_query, (name,), conn)
                deleted += 1
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete '{name}': {e}")

        if conn:
            commit(conn)

        messagebox.showinfo("Deleted", f"{deleted} record(s) deleted.")
        self.load_suspicious_from_db()

    def create_suspicious_table(self):
        logger.logger.info("[suspicious_manager] : Layer 3 - Deploying suspicious data extraction table section")

        frame = tk.LabelFrame(self.scrollable_frame,
                              text="Suspicious Table",
                              bg="#f0f0f5", padx=10, pady=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        cols = (
            "Suspicious Name", "Created Date", "Created By",
            "Modified Date", "Modified By",
            "Exists In Blacklisted?"
        )
        self.bl_tree = ttk.Treeview(frame, columns=cols,
                                    show="headings", height=20)
        for c in cols:
            self.bl_tree.heading(c, text=c)
            anchor = "w" if c == "Suspicious Name" else "center"
            self.bl_tree.column(c, anchor=anchor, width=140)
        self.bl_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Zebra striping tags ─────────────────────────
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.bl_tree.tag_configure("evenrow", background="#f5f5f5")
        self.bl_tree.tag_configure("oddrow",  background="#ffffff")
        # ─────────────────────────────────────────────────

        vsb = ttk.Scrollbar(frame, orient="vertical",
                            command=self.bl_tree.yview)
        self.bl_tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Total Count Label ---
        self.total_label = tk.Label(self.scrollable_frame, text="Total Records: 0", anchor="e", font=("Arial", 10), bg="#f0f0f5")
        self.total_label.pack(anchor="e", padx=30, pady=(0, 5))

        # Load all data from database into grid table
        self.load_suspicious_from_db()

    def save_transaction(self):
        logger.logger.info("[suspicious_manager] : Executing the SAVE operation")

        name = self.bl_name_var.get().strip()
        if not name:
            messagebox.showwarning("Empty", "Please enter a Suspicious Name.")
            return

        # Determine whether to insert or update
        now = datetime.now()
        conn = None

        if hasattr(self, 'selected_edit_id') and self.selected_edit_id:
            # ✅ Update existing
            update_query = """
                UPDATE TM_MST_SUSPICIOUS
                SET VCH_SUSPICIOUS_NAME = %s,
                    NUM_UPDATED_BY = %s,
                    DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur'
                WHERE VCH_SUSPICIOUS_NAME = %s AND CHR_ACTIVE_IND = 'Y'
            """
            params = (name, 1, self.selected_edit_id)
            try:
                conn = execute_query(update_query, params, conn)
                commit(conn)
                messagebox.showinfo("Success", f"'{name}' updated successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Update failed: {e}")
            self.selected_edit_id = None  # Clear edit mode
        else:
            # ✅ Insert new
            insert_query = """
                INSERT INTO TM_MST_SUSPICIOUS (
                    VCH_SUSPICIOUS_NAME, VCH_REMARK_1, VCH_REMARK_2,
                    CHR_ACTIVE_IND, NUM_CREATED_BY, DTT_CREATED_AT
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (name, "", "", "Y", 1, now)
            try:
                conn = execute_query(insert_query, params, conn)
                commit(conn)
                messagebox.showinfo("Success", f"'{name}' inserted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Insert failed: {e}")

        self.bl_name_var.set("")               # Clear input box
        self.load_suspicious_from_db()        # Refresh grid

    def download_template(self):
        logger.logger.info("[suspicious_manager] : Executing the template DOWNLOAD operation")

        # source_path = r"D:\CHIANWEILON\Software_Dev\TransMatch\Development\Source_Code\TransMatch\templates\suspicious_template.xlsx"
        if getattr(sys, 'frozen', False):
            # Look for templates next to the executable (external folder)
            base_path = os.path.dirname(sys.executable)
        else:
            # If running as a normal Python script
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to TransMatch root

        source_path = os.path.join(base_path, "templates", "suspicious_template.xlsx")

        dest_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="suspicious_template.xlsx",
            title="Save Template As"
        )
        if dest_path:
            try:
                shutil.copyfile(source_path, dest_path)
                messagebox.showinfo("Success", f"Template downloaded to:\n{dest_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download template:\n{e}")

    def load_suspicious_from_db(self):
        logger.logger.info("[suspicious_manager] : Extract and Load all suspicious data into grid table")

        self.bl_tree.delete(*self.bl_tree.get_children())

        query = """
            SELECT 
                s.VCH_SUSPICIOUS_NAME,
                TO_CHAR(s.DTT_CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_CREATED_AT,
                s.NUM_CREATED_BY,
                TO_CHAR(s.DTT_UPDATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_UPDATED_AT,
                s.NUM_UPDATED_BY,
                CASE WHEN b.VCH_BLACKLISTED_NAME IS NOT NULL THEN 'Yes' ELSE 'No' END AS exists_in_blacklist
            FROM TM_MST_SUSPICIOUS s
            LEFT JOIN TM_MST_BLACKLISTED b
                ON TRIM(LOWER(s.VCH_SUSPICIOUS_NAME)) = TRIM(LOWER(b.VCH_BLACKLISTED_NAME))
            WHERE s.CHR_ACTIVE_IND = 'Y'
            ORDER BY s.DTT_CREATED_AT desc, s.VCH_SUSPICIOUS_NAME
        """

        results = executionWithRs_query(query) or []

        for idx, row in enumerate(results):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.bl_tree.insert("", tk.END, values=row, tags=(tag,))

        # Footer to show the total number of record
        self.total_label.config(text=f"Total Records: {len(results)}")
