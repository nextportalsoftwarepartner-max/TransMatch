# flake8: noqa: E501

import tkinter as tk
from tkinter import ttk, messagebox
import logger
from db_manager import executionWithRs_query, execute_query, commit

logger.logger.info("[admin_user_role] : Menu initiation")


class UserRoleManager:
    def __init__(self, root, login_id):
        self.root = root
        self.role_window = tk.Toplevel(root)
        self.role_window.title("User Role Management")

        screen_width = self.role_window.winfo_screenwidth()
        screen_height = self.role_window.winfo_screenheight()
        window_width = int(screen_width * 1)
        window_height = int(screen_height * 0.9)
        x_pos = int((screen_width - window_width) / 2)
        y_pos = int((screen_height - window_height) / 5)

        self.role_window.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.role_window.transient(self.root)
        self.role_window.grab_set()
        self.role_window.focus_force()

        self.role_vars = {}
        self.selected_role_id = None

        self.load_group_options()
        self.create_filter_section()
        self.create_entry_section()
        self.create_role_table()
        self.load_roles()

        logger.logger.info("[admin_user_role] : Screen established completely")

    def load_group_options(self):
        results = executionWithRs_query("SELECT NUM_GROUP_ID, VCH_GROUP_NAME FROM TM_MST_GROUP WHERE CHR_ACTIVE_IND = 'Y' ORDER BY VCH_GROUP_NAME")
        self.group_options = [(str(r[0]), r[1]) for r in results] if results else []

    def create_filter_section(self):
        logger.logger.info("[admin_user_role] : Layer 1 - Deploying searching criteria section")
        frame = tk.LabelFrame(self.role_window, text="Filter Criteria", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=(10, 5))

        self.filter_name_var = tk.StringVar()
        ttk.Label(frame, text="Role Name:").grid(row=0, column=0, padx=5)
        ttk.Entry(frame, textvariable=self.filter_name_var, width=40).grid(row=0, column=1, padx=5)

        ttk.Button(frame, text="🔍 Search", command=self.load_roles).grid(row=0, column=2, padx=5)
        ttk.Button(frame, text="🔄 Reset", command=self.reset_filters).grid(row=0, column=3, padx=5)

    def create_entry_section(self):
        logger.logger.info("[admin_user_role] : Layer 2 - Deploying setup section")
        frame = tk.LabelFrame(self.role_window, text="Data Entry", padx=10, pady=5)
        frame.pack(fill=tk.X, padx=20, pady=5)

        self.group_name_var = tk.StringVar()
        self.role_name_var = tk.StringVar()
        self.role_desc_text = tk.Text(frame, height=3, width=40)  # Multi-line Text widget
        self.group_map = {}  # Mapping of group name to ID

        # Load group list (active only)
        group_rows = executionWithRs_query("SELECT NUM_GROUP_ID, VCH_GROUP_NAME FROM TM_MST_GROUP WHERE CHR_ACTIVE_IND = 'Y'")
        group_names = []
        if group_rows:
            for gid, gname in group_rows:
                group_names.append(gname)
                self.group_map[gname] = gid

        # Group Dropdown
        ttk.Label(frame, text="Group:").grid(row=0, column=0, padx=5, pady=2, sticky='e')
        self.group_dropdown = ttk.Combobox(frame, textvariable=self.group_name_var, values=group_names, state='readonly', width=38)
        self.group_dropdown.grid(row=0, column=1, padx=5, pady=2)

        # Role Name Entry
        ttk.Label(frame, text="Role Name:").grid(row=0, column=2, padx=5, pady=2, sticky='e')
        ttk.Entry(frame, textvariable=self.role_name_var, width=40).grid(row=0, column=3, padx=5, pady=2)

        # Description Text Area
        ttk.Label(frame, text="Description:").grid(row=1, column=0, padx=5, pady=2, sticky='ne')
        self.role_desc_text.grid(row=1, column=1, columnspan=3, padx=5, pady=2, sticky='w')

        # Action Buttons
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=5, pady=5)
        ttk.Button(btn_frame, text="➕ Add", command=self.add_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ Edit", command=self.prepare_edit_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 Delete", command=self.delete_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🟡 Deactivate", command=lambda: self.toggle_active_status('N')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🟢 Activate", command=lambda: self.toggle_active_status('Y')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Reset", command=self.reset_entries).pack(side=tk.LEFT, padx=5)

    def create_role_table(self):
        logger.logger.info("[admin_user_role] : Layer 3 - Deploying setup table section")
        frame = tk.LabelFrame(self.role_window, text="Role Table", padx=10, pady=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = (
            "Group Name", "Role ID", "Role Name", "Description", "Status",
            "Created By", "Created At", "Updated By", "Updated At"
        )
        self.role_tree = ttk.Treeview(frame, columns=columns, show="headings")

        widths = {
            "Group Name": 150, "Role ID": 50, "Role Name": 150, "Description": 300, "Status": 100, 
            "Created By": 100, "Created At": 150, "Updated By": 100, "Updated At": 150
        }

        for col in columns:
            self.role_tree.heading(col, text=col)
            self.role_tree.column(col, anchor="center", width=widths[col], stretch=False)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.role_tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.role_tree.xview)
        self.role_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.role_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

    def load_roles(self):
        keyword = self.filter_name_var.get().strip()
        sql = """
            SELECT G.VCH_GROUP_NAME, R.NUM_ROLE_ID, R.VCH_ROLE_NAME, R.VCH_DESC,
                CASE WHEN R.CHR_ACTIVE_IND = 'Y' THEN 'Active' ELSE 'Deactivated' END AS STATUS,
                R.NUM_CREATED_BY, TO_CHAR(R.DTT_CREATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_CREATED_AT,
                R.NUM_UPDATED_BY, TO_CHAR(R.DTT_UPDATED_AT, 'YYYY-MM-DD HH24:MI:SS') AS DTT_UPDATED_AT
            FROM TM_MST_ROLE R
            JOIN TM_MST_GROUP G ON R.NUM_GROUP_ID = G.NUM_GROUP_ID
        """
        params = []
        if keyword:
            sql += " WHERE R.VCH_ROLE_NAME ILIKE %s"
            params.append(f"%{keyword}%")
        sql += " ORDER BY R.VCH_ROLE_NAME"

        rows = executionWithRs_query(sql, tuple(params))
        self.role_tree.delete(*self.role_tree.get_children())

        if not rows:
            return  # No data or error, just return safely

        for row in rows:
            self.role_tree.insert("", tk.END, values=row)

    def reset_filters(self):
        self.filter_name_var.set("")
        self.load_roles()

    def reset_entries(self):
        self.group_name_var.set("")  # Clear group dropdown
        self.role_name_var.set("")   # Clear role name
        self.role_desc_text.delete("1.0", tk.END)  # Clear description text
        self.selected_role_id = None

    def add_role(self):
        group_entry = self.group_name_var.get().strip()
        role_name = self.role_name_var.get().strip()
        desc = self.role_desc_text.get("1.0", tk.END).strip()

        conn = None

        if not group_entry or not role_name:
            messagebox.showerror("Missing Info", "Group and Role Name are required.")
            return

        group_id = self.group_map.get(group_entry)
        if not group_id:
            messagebox.showerror("Invalid Group", "Selected group is not recognized.")
            return

        role_name_upper = role_name.upper()
        # Check for duplicate Group + Role Name
        dup_sql = """
            SELECT 1 FROM TM_MST_ROLE 
            WHERE UPPER(VCH_ROLE_NAME) = %s AND NUM_GROUP_ID = %s 
            AND NUM_ROLE_ID <> COALESCE(%s, -1)
        """
        if executionWithRs_query(dup_sql, (role_name_upper, group_id, self.selected_role_id)):
            messagebox.showerror("Duplicate", "This role already exists under the selected group.")
            return

        if self.selected_role_id:
            sql = """
                UPDATE TM_MST_ROLE 
                SET VCH_ROLE_NAME = %s, VCH_DESC = %s, NUM_GROUP_ID = %s,
                    NUM_UPDATED_BY = %s, DTT_UPDATED_AT = CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kuala_Lumpur'
                WHERE NUM_ROLE_ID = %s
            """
            conn = execute_query(sql, (role_name, desc, group_id, 1, self.selected_role_id), conn)
            messagebox.showinfo("Success", "Role updated successfully.")
        else:
            sql = """
                INSERT INTO TM_MST_ROLE 
                (VCH_ROLE_NAME, VCH_DESC, NUM_GROUP_ID, CHR_ACTIVE_IND, NUM_CREATED_BY)
                VALUES (%s, %s, %s, 'Y', %s)
            """
            conn = execute_query(sql, (role_name, desc, group_id, 1), conn)
            messagebox.showinfo("Success", "Role added successfully.")

        if conn:
            commit(conn)

        self.reset_entries()
        self.load_roles()

    def prepare_edit_role(self):
        selected = self.role_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a role to edit.")
            return
        values = self.role_tree.item(selected[0])['values']
        self.group_name_var.set(values[0])
        self.selected_role_id = values[1]
        self.role_name_var.set(values[2])
        self.role_desc_text.delete("1.0", tk.END)
        self.role_desc_text.insert(tk.END, values[3])

    def delete_role(self):
        selected = self.role_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a role to delete.")
            return

        confirm = messagebox.askyesno("Confirm", "This will permanently delete the record. Proceed?")
        if not confirm:
            return

        values = self.role_tree.item(selected[0])['values']
        role_id = values[1]

        # Check CHR_NO_DELETE_IND
        check_sql = "SELECT CHR_NO_DELETE_IND FROM TM_MST_ROLE WHERE NUM_ROLE_ID = %s"
        flag = executionWithRs_query(check_sql, (role_id,))
        if flag and flag[0][0] == 'Y':
            logger.logger.info(f"[admin_user_group] : Role ID[{values}] - CHR_NO_DELETE_IND = 'Y', this role is protected and cannot be deleted.")
            messagebox.showwarning("Protected Group", "This group is protected and cannot be deleted.")
            return

        sql = "DELETE FROM TM_MST_ROLE WHERE NUM_ROLE_ID = %s"
        conn = execute_query(sql, (values[1],))
        if conn:
            commit(conn)
        self.load_roles()

    def toggle_active_status(self, status):
        selected = self.role_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a role to update status.")
            return

        values = self.role_tree.item(selected[0])['values']
        current_status = values[4]
        if (status == 'Y' and current_status == 'Active') or (status == 'N' and current_status == 'Deactivated'):
            messagebox.showinfo("Status Check", f"Role is already {current_status.lower()}.")
            return

        sql = "UPDATE TM_MST_ROLE SET CHR_ACTIVE_IND = %s WHERE NUM_ROLE_ID = %s"
        conn = execute_query(sql, (status, values[1]))
        if conn:
            commit(conn)
        self.load_roles()
