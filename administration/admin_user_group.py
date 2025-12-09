# flake8: noqa: E501

import tkinter as tk
from tkinter import ttk, messagebox
import logger
from db_manager import executionWithRs_query, execute_query, commit

logger.logger.info("[admin_user_group] : Menu initiation")


class UserGroupManager:
    def __init__(self, root, login_id):
        self.root = root
        self.group_window = tk.Toplevel(root)
        self.group_window.title("User Group Management")

        screen_width = self.group_window.winfo_screenwidth()
        screen_height = self.group_window.winfo_screenheight()
        window_width = int(screen_width * 1)
        window_height = int(screen_height * 0.9)
        x_pos = int((screen_width - window_width) / 2)
        y_pos = int((screen_height - window_height) / 5)

        self.group_window.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.group_window.transient(self.root)
        self.group_window.grab_set()
        self.group_window.focus_force()

        self.group_vars = {}
        self.selected_group_id = None

        self.create_filter_section()
        self.create_entry_section()
        self.create_group_table()
        self.load_groups()

        logger.logger.info("[admin_user_group] : Screen established completely")

    def create_filter_section(self):
        logger.logger.info("[admin_user_group] : Layer 1 - Deploying searching criteria section")

        frame = tk.LabelFrame(self.group_window, text="Filter Criteria", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=(10, 5))

        self.filter_name_var = tk.StringVar()
        ttk.Label(frame, text="Group Name:").grid(row=0, column=0, padx=5)
        ttk.Entry(frame, textvariable=self.filter_name_var, width=40).grid(row=0, column=1, padx=5)

        ttk.Button(frame, text="🔍 Search", command=self.load_groups).grid(row=0, column=2, padx=5)
        ttk.Button(frame, text="🔄 Reset", command=self.reset_filters).grid(row=0, column=3, padx=5)

    def create_entry_section(self):
        logger.logger.info("[admin_user_group] : Layer 2 - Deploying setup section")

        frame = tk.LabelFrame(self.group_window, text="Data Entry", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=5)

        self.group_name_var = tk.StringVar()
        self.group_desc_var = tk.StringVar()

        ttk.Label(frame, text="Group Name:").grid(row=0, column=0, padx=5, pady=2, sticky='e')
        ttk.Entry(frame, textvariable=self.group_name_var, width=40).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(frame, text="Description:").grid(row=0, column=2, padx=5, pady=2, sticky='e')
        ttk.Entry(frame, textvariable=self.group_desc_var, width=40).grid(row=0, column=3, padx=5, pady=2)

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=5, pady=5)
        ttk.Button(btn_frame, text="➕ Add", command=self.add_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ Edit", command=self.prepare_edit_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 Delete", command=self.delete_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🟡 Deactivate", command=lambda: self.toggle_active_status('N')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🟢 Activate", command=lambda: self.toggle_active_status('Y')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Reset", command=self.reset_entries).pack(side=tk.LEFT, padx=5)

    def create_group_table(self):
        logger.logger.info("[admin_user_group] : Layer 3 - Deploying setup table section")

        frame = tk.LabelFrame(self.group_window, text="Group Table", padx=10, pady=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ("Group ID", "Group Name", "Description", "Status", "Created By", "Created At", "Updated By", "Updated At")
        self.group_tree = ttk.Treeview(frame, columns=columns, show="headings")

        widths = {
            "Group ID": 80,
            "Group Name": 200,
            "Description": 300,
            "Status": 100,
            "Created By": 100,
            "Created At": 150,
            "Updated By": 100,
            "Updated At": 150,
        }

        for col in columns:
            self.group_tree.heading(col, text=col)
            anchor = 'w' if col == "Description" else 'center'
            self.group_tree.column(col, anchor=anchor, width=widths[col], stretch=False)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.group_tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.group_tree.xview)
        self.group_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.group_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

    def load_groups(self):
        keyword = self.filter_name_var.get().strip()
        sql = """
            SELECT NUM_GROUP_ID, VCH_GROUP_NAME, VCH_DESC,
                   CASE WHEN CHR_ACTIVE_IND = 'Y' THEN 'Active' ELSE 'Deactivated' END AS STATUS,
                   NUM_CREATED_BY, TO_CHAR(DTT_CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_CREATED_AT,
                   NUM_UPDATED_BY, TO_CHAR(DTT_UPDATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_UPDATED_AT
            FROM TM_MST_GROUP
        """
        params = []
        if keyword:
            sql += " WHERE VCH_GROUP_NAME ILIKE %s"
            params.append(f"%{keyword}%")

        sql += " ORDER BY VCH_GROUP_NAME"

        rows = executionWithRs_query(sql, tuple(params))
        self.group_tree.delete(*self.group_tree.get_children())

        if not rows:
            logger.logger.info("[admin_user_group] : [Search] No matching user group found")
            messagebox.showinfo("No Records", "No matching user group found.")
            return

        for row in rows:
            self.group_tree.insert("", tk.END, values=row)

    def reset_filters(self):
        logger.logger.info("[admin_user_group] : Executing the RESET operation, for filter section only")
        self.filter_name_var.set("")
        self.load_groups()

    def reset_entries(self):
        logger.logger.info("[admin_user_group] : Executing the RESET operation, for data entry section only")
        self.group_name_var.set("")
        self.group_desc_var.set("")
        self.selected_group_id = None

    def add_group(self):
        logger.logger.info("[admin_user_group] : Executing the ADD or UPDATE operation into database")
        name = self.group_name_var.get().strip()
        desc = self.group_desc_var.get().strip()
        conn = None

        if not name:
            messagebox.showerror("Missing Info", "Group Name is required.")
            return

        duplicate_check = executionWithRs_query("SELECT 1 FROM TM_MST_GROUP WHERE VCH_GROUP_NAME = %s AND NUM_GROUP_ID <> COALESCE(%s, -1)", (name, self.selected_group_id))
        if duplicate_check:
            messagebox.showerror("Duplicate", "Group Name already exists.")
            return

        if self.selected_group_id:  # Perform UPDATE
            sql = """
                UPDATE TM_MST_GROUP SET VCH_GROUP_NAME = %s, VCH_DESC = %s, NUM_UPDATED_BY = %s,
                DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur'
                WHERE NUM_GROUP_ID = %s
            """
            conn = execute_query(sql, (name, desc, 1, self.selected_group_id), conn)
            messagebox.showinfo("Success", "Group updated successfully.")
        else:  # Perform INSERT
            sql = """
                INSERT INTO TM_MST_GROUP (VCH_GROUP_NAME, VCH_DESC, CHR_ACTIVE_IND, NUM_CREATED_BY)
                VALUES (%s, %s, 'Y', %s)
            """
            conn = execute_query(sql, (name, desc, 1), conn)
            messagebox.showinfo("Success", "Group added successfully.")

        if conn:
            commit(conn)

        self.reset_entries()
        self.load_groups()

    def prepare_edit_group(self):
        logger.logger.info("[admin_user_group] : Preparing selected data for edit")
        selected = self.group_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a group to edit.")
            return

        values = self.group_tree.item(selected[0])['values']
        self.selected_group_id = values[0]
        self.group_name_var.set(values[1])
        self.group_desc_var.set(values[2])

    def delete_group(self):
        logger.logger.info("[admin_user_group] : Executing the DELETE operation into database")
        selected = self.group_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a group to delete.")
            return

        confirm = messagebox.askyesno("Confirm", "This will permanently delete the record. Proceed?")
        if not confirm:
            return

        values = self.group_tree.item(selected[0])['values']
        group_id = values[0]

        # Check CHR_NO_DELETE_IND
        check_sql = "SELECT CHR_NO_DELETE_IND FROM TM_MST_GROUP WHERE NUM_GROUP_ID = %s"
        flag = executionWithRs_query(check_sql, (group_id,))
        if flag and flag[0][0] == 'Y':
            logger.logger.info(f"[admin_user_group] : Group ID[{group_id}] - CHR_NO_DELETE_IND = 'Y', this group is protected and cannot be deleted.")
            messagebox.showwarning("Protected Group", "This group is protected and cannot be deleted.")
            return

        sql = "DELETE FROM TM_MST_GROUP WHERE NUM_GROUP_ID = %s"
        conn = execute_query(sql, (group_id,), None)
        if conn:
            commit(conn)

        messagebox.showinfo("Success", "Group deleted permanently.")
        logger.logger.info(f"[admin_user_group] : Group ID[{group_id}] has been deleted permanently.")
        self.reset_entries()
        self.load_groups()

    def toggle_active_status(self, status):
        selected = self.group_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a group to update status.")
            return

        values = self.group_tree.item(selected[0])['values']
        group_id = values[0]
        current_status = values[3]

        if (status == 'Y' and current_status == 'Active') or (status == 'N' and current_status == 'Deactivated'):
            messagebox.showinfo("Info", f"Group is already {current_status.lower()}.")
            return

        sql = "UPDATE TM_MST_GROUP SET CHR_ACTIVE_IND = %s, NUM_UPDATED_BY = %s, DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur' WHERE NUM_GROUP_ID = %s"
        conn = execute_query(sql, (status, 1, group_id), None)
        if conn:
            commit(conn)

        action = "activated" if status == 'Y' else "deactivated"
        messagebox.showinfo("Success", f"Group has been {action}.")
        logger.logger.info(f"[admin_user_group] : Group ID[{group_id}] has been {action}.")
        self.reset_entries()
        self.load_groups()
