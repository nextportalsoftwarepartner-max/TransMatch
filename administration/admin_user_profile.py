# flake8: noqa: E501

# admin_user_profile.py
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import simpledialog
from LoadingPopup import LoadingPopupClass
import logger
from db_manager import commit, execute_query, executionWithRs_query, executionWithRs_queryWithCommit, hash_password

logger.logger.info("[admin_user_profile] : Menu initiation")


class UserProfileManager:
    def __init__(self, root, global_info):
        self.root = root
        self.user_prof_window = tk.Toplevel(root)
        self.user_prof_window.title("User Profile Management")

        screen_width = self.user_prof_window.winfo_screenwidth()
        screen_height = self.user_prof_window.winfo_screenheight()
        window_width = int(screen_width * 1)
        window_height = int(screen_height * 0.9)
        x_pos = int((screen_width - window_width) / 2)
        y_pos = int((screen_height - window_height) / 5)

        self.user_prof_window.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        self.user_prof_window.transient(self.root)
        self.user_prof_window.grab_set()
        self.user_prof_window.focus_force()

        logger.logger.info("[admin_user_profile] : Initializing User Profile Screen")

        self.build_filter_criteria()
        self.build_data_entry_section(global_info)
        self.populate_group_dropdowns()
        self.populate_roles_dropdown()
        self.populate_supervisors()
        self.build_result_grid()

    def build_filter_criteria(self):
        filter_frame = tk.LabelFrame(self.user_prof_window, text="Filter Criteria", font=("Helvetica", 12, "bold"), bg="white", bd=2)
        filter_frame.pack(fill=tk.X, padx=20, pady=10)

        self.filter_group_var = tk.StringVar()
        self.filter_role_var = tk.StringVar()
        self.filter_staff_name_var = tk.StringVar()

        ttk.Label(filter_frame, text="User Group:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filter_group_combo = ttk.Combobox(filter_frame, textvariable=self.filter_group_var, state="readonly")
        self.filter_group_combo.grid(row=0, column=1, padx=5, pady=5)
        self.filter_group_combo.bind("<<ComboboxSelected>>", self.update_filter_roles)

        ttk.Label(filter_frame, text="User Role:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.filter_role_combo = ttk.Combobox(filter_frame, textvariable=self.filter_role_var, state="readonly")
        self.filter_role_combo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filter_frame, text="Staff Name:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.filter_staff_entry = ttk.Entry(filter_frame, textvariable=self.filter_staff_name_var)
        self.filter_staff_entry.grid(row=0, column=5, padx=5, pady=5)

        ttk.Button(filter_frame, text="Search", command=self.search_users).grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(filter_frame, text="Clean", command=self.clean_filters).grid(row=1, column=2, padx=10, pady=10)

        # self.populate_group_dropdowns()

    def build_data_entry_section(self, global_info):
        entry_frame = tk.LabelFrame(self.user_prof_window, text="User Profile Entry", font=("Helvetica", 12, "bold"), bg="white", bd=2)
        entry_frame.pack(fill=tk.X, padx=20, pady=10)

        # Row 1
        self.entry_group_var = tk.StringVar()
        self.entry_role_var = tk.StringVar()
        self.entry_login_id_var = tk.StringVar()
        self.entry_password_var = tk.StringVar()

        ttk.Label(entry_frame, text="User Group:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_group_combo = ttk.Combobox(entry_frame, textvariable=self.entry_group_var, state="readonly")
        self.entry_group_combo.grid(row=0, column=1, padx=5, pady=5)
        self.entry_group_combo.bind("<<ComboboxSelected>>", self.update_filter_roles)

        ttk.Label(entry_frame, text="User Role:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_role_combo = ttk.Combobox(entry_frame, textvariable=self.entry_role_var, state="readonly")
        self.entry_role_combo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(entry_frame, text="Login ID:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.entry_login_entry = ttk.Entry(entry_frame, textvariable=self.entry_login_id_var)
        self.entry_login_entry.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(entry_frame, text="Password:").grid(row=0, column=6, padx=5, pady=5, sticky="w")
        self.entry_password_entry = ttk.Entry(entry_frame, textvariable=self.entry_password_var, show="*")
        self.entry_password_entry.grid(row=0, column=7, padx=5, pady=5)

        # Row 2
        self.entry_supervisor_var = tk.StringVar()
        self.entry_name_var = tk.StringVar()
        self.entry_email_var = tk.StringVar()
        self.entry_contact_var = tk.StringVar()

        ttk.Label(entry_frame, text="Supervisor:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_supervisor_combo = ttk.Combobox(entry_frame, textvariable=self.entry_supervisor_var, state="readonly")
        self.entry_supervisor_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(entry_frame, text="Staff Name:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.entry_name_entry = ttk.Entry(entry_frame, textvariable=self.entry_name_var)
        self.entry_name_entry.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(entry_frame, text="Email:").grid(row=1, column=4, padx=5, pady=5, sticky="w")
        self.entry_email_entry = ttk.Entry(entry_frame, textvariable=self.entry_email_var)
        self.entry_email_entry.grid(row=1, column=5, padx=5, pady=5)

        ttk.Label(entry_frame, text="Contact:").grid(row=1, column=6, padx=5, pady=5, sticky="w")
        self.entry_contact_entry = ttk.Entry(entry_frame, textvariable=self.entry_contact_var)
        self.entry_contact_entry.grid(row=1, column=7, padx=5, pady=5)

        # Row 3
        self.entry_addr1_var = tk.StringVar()
        self.entry_addr2_var = tk.StringVar()
        ttk.Label(entry_frame, text="Address 1:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.entry_addr1_var).grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        ttk.Label(entry_frame, text="Address 2:").grid(row=2, column=4, padx=5, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.entry_addr2_var).grid(row=2, column=5, columnspan=3, padx=5, pady=5, sticky="ew")

        # Row 4
        self.entry_addr3_var = tk.StringVar()
        self.entry_addr4_var = tk.StringVar()
        ttk.Label(entry_frame, text="Address 3:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.entry_addr3_var).grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        ttk.Label(entry_frame, text="Address 4:").grid(row=3, column=4, padx=5, pady=5, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.entry_addr4_var).grid(row=3, column=5, columnspan=3, padx=5, pady=5, sticky="ew")

        # Row 5
        btn_frame = tk.Frame(entry_frame, bg="white")
        btn_frame.grid(row=4, column=0, columnspan=8, pady=10)

        ttk.Button(btn_frame, text="Add", width=15, command=self.layer2_add_user).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Edit", width=15, command=self.layer2_edit_user).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Delete", width=15, command=lambda: self.layer2_delete_user(global_info)).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Clean", width=15, command=self.layer2_clean_entry_fields).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Reset Password", width=15, command=self.reset_password_dialog).pack(side=tk.LEFT, padx=10)

        # self.populate_group_dropdowns()
        # self.populate_supervisors()

    # def populate_filter_groups(self):
    #     query = "SELECT NUM_GROUP_ID, VCH_GROUP_NAME FROM TM_MST_GROUP WHERE CHR_ACTIVE_IND = 'Y' ORDER BY VCH_GROUP_NAME"
    #     rows = executionWithRs_query(query)
    #     self.group_dict = {name: gid for gid, name in rows}
    #     self.filter_group_combo['values'] = list(self.group_dict.keys())

    def populate_group_dropdowns(self):
        query = "SELECT NUM_GROUP_ID, VCH_GROUP_NAME FROM TM_MST_GROUP WHERE CHR_ACTIVE_IND = 'Y' ORDER BY VCH_GROUP_NAME"
        rows = executionWithRs_query(query)
        self.group_dict = {name: gid for gid, name in rows}

        self.filter_group_combo['values'] = list(self.group_dict.keys())
        self.entry_group_combo['values'] = list(self.group_dict.keys())

    def populate_roles_dropdown(self):
        query = "SELECT VCH_ROLE_NAME FROM TM_MST_ROLE WHERE CHR_ACTIVE_IND = 'Y' ORDER BY VCH_ROLE_NAME"
        rows = executionWithRs_query(query)
        role_names = [r[0] for r in rows]
        self.filter_role_combo['values'] = role_names

    def update_filter_roles(self, event=None):
        # Only apply to entry group and role
        if event and event.widget == self.entry_group_combo:
            selected_group = self.entry_group_var.get()
            group_id = self.group_dict.get(selected_group)
            if not group_id:
                self.entry_role_combo['values'] = []
                return

            query = """
                SELECT VCH_ROLE_NAME FROM TM_MST_ROLE
                WHERE NUM_GROUP_ID = %s AND CHR_ACTIVE_IND = 'Y' ORDER BY VCH_ROLE_NAME
            """
            rows = executionWithRs_query(query, (group_id,))
            self.entry_role_combo['values'] = [r[0] for r in rows]

    def populate_supervisors(self):
        query = "SELECT NUM_USER_ID, VCH_USER_NAME FROM TM_MST_USER WHERE CHR_ACTIVE_IND = 'Y' ORDER BY VCH_USER_NAME"
        rows = executionWithRs_query(query)
        self.supervisor_dict = {"None": None}
        self.supervisor_dict.update({name: uid for uid, name in rows})
        self.entry_supervisor_combo['values'] = list(self.supervisor_dict.keys())
        self.entry_supervisor_var.set("None")

    def search_users(self):
        self.loading_popup = LoadingPopupClass(self.user_prof_window, "Searching users... Please wait.")
        self.user_prof_window.update_idletasks()

        thread = threading.Thread(target=self._execute_user_search)
        thread.start()

    def _execute_user_search(self):
        try:
            group = self.filter_group_var.get()
            role = self.filter_role_var.get()
            staff_name = self.filter_staff_name_var.get()

            conditions = []
            params = []

            if group:
                conditions.append("grp.VCH_GROUP_NAME = %s")
                params.append(group)
            if role:
                conditions.append("rol.VCH_ROLE_NAME = %s")
                params.append(role)
            if staff_name:
                conditions.append("usr.VCH_USER_NAME ILIKE %s")
                params.append(f"%{staff_name}%")

            sql = """
                SELECT usr.NUM_USER_ID, usr.VCH_USER_NAME, usr.VCH_LOGIN_ID, grp.VCH_GROUP_NAME, rol.VCH_ROLE_NAME,
                       sup.VCH_USER_NAME AS SUPERVISOR_NAME, usr.DTT_CREATED_AT, usr.NUM_CREATED_BY, usr.DTT_UPDATED_AT, usr.NUM_UPDATED_BY
                FROM TM_MST_USER usr
                LEFT JOIN TM_MST_USER sup ON usr.NUM_SUPERVISOR_ID = sup.NUM_USER_ID
                INNER JOIN TM_MST_USER_ASSIGNMENT ua ON usr.NUM_USER_ID = ua.NUM_USER_ID
                INNER JOIN TM_MST_GROUP grp ON ua.NUM_GROUP_ID = grp.NUM_GROUP_ID
                INNER JOIN TM_MST_ROLE rol ON ua.NUM_ROLE_ID = rol.NUM_ROLE_ID
            """
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY usr.VCH_USER_NAME"
            # logger.logger.info("[admin_user_profile] : sql = " + sql)

            rows = executionWithRs_query(sql, tuple(params))

            def update_ui():
                self.loading_popup.close()
                self.result_table.delete(*self.result_table.get_children())
                if not rows:
                    logger.logger.info(f"[admin_user_profile] : Search process, No matching user found with condition = [{conditions}]|[group={group},role={role},name={staff_name}]")
                    messagebox.showinfo("No Record", "No matching user found.")
                    return
                for row in rows:
                    self.result_table.insert("", tk.END, values=row)

            self.user_prof_window.after(0, update_ui)

        except Exception as e:
            logger.logger.info(f"[admin_user_profile][Search function][Exception] : {str(e)}")
            self.user_prof_window.after(0, lambda: [
                self.loading_popup.close(),
                messagebox.showerror("Error", f"Error occurred during search:\n{str(e)}")
            ])

    def clean_filters(self):
        self.filter_group_var.set("")
        self.filter_role_var.set("")
        self.filter_staff_name_var.set("")
        self.filter_role_combo['values'] = []

    def build_result_grid(self):
        columns = [
            "User ID", "User Name", "Login ID", "User Group", "User Role",
            "Supervisor Name", "Created At", "Created By", "Updated At", "Updated By"
        ]

        result_frame = tk.LabelFrame(self.user_prof_window, text="Search Results", font=("Helvetica", 12, "bold"), bg="white", bd=2)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.result_table = ttk.Treeview(result_frame, columns=columns, show="headings")
        for col in columns:
            self.result_table.heading(col, text=col)
            self.result_table.column(col, anchor="w", width=130)

        self.result_table.pack(fill=tk.BOTH, expand=True)

        y_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_table.yview)
        self.result_table.configure(yscrollcommand=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        x_scroll = ttk.Scrollbar(result_frame, orient="horizontal", command=self.result_table.xview)
        self.result_table.configure(xscrollcommand=x_scroll.set)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.adjust_column_width()
        self.refresh_result_grid()

    def refresh_result_grid(self):
        sql = """
            SELECT usr.NUM_USER_ID, usr.VCH_USER_NAME, usr.VCH_LOGIN_ID, grp.VCH_GROUP_NAME, rol.VCH_ROLE_NAME,
                   sup.VCH_USER_NAME AS SUPERVISOR_NAME, usr.DTT_CREATED_AT, usr.NUM_CREATED_BY, usr.DTT_UPDATED_AT, usr.NUM_UPDATED_BY
            FROM TM_MST_USER usr
            LEFT JOIN TM_MST_USER sup ON usr.NUM_SUPERVISOR_ID = sup.NUM_USER_ID
            INNER JOIN TM_MST_USER_ASSIGNMENT ua ON usr.NUM_USER_ID = ua.NUM_USER_ID
            INNER JOIN TM_MST_GROUP grp ON ua.NUM_GROUP_ID = grp.NUM_GROUP_ID
            INNER JOIN TM_MST_ROLE rol ON ua.NUM_ROLE_ID = rol.NUM_ROLE_ID
            WHERE usr.CHR_ACTIVE_IND = 'Y'
            ORDER BY usr.VCH_USER_NAME
        """
        rows = executionWithRs_query(sql)
        self.result_table.delete(*self.result_table.get_children())
        for row in rows:
            self.result_table.insert("", tk.END, values=row)

    def layer2_add_user(self):
        group = self.entry_group_var.get()
        role = self.entry_role_var.get()
        login_id = self.entry_login_id_var.get()
        password = self.entry_password_var.get()
        supervisor = self.entry_supervisor_var.get()
        name = self.entry_name_var.get()
        email = self.entry_email_var.get()
        contact = self.entry_contact_var.get()
        addr1 = self.entry_addr1_var.get()
        addr2 = self.entry_addr2_var.get()
        addr3 = self.entry_addr3_var.get()
        addr4 = self.entry_addr4_var.get()
        conn = None
        logger.logger.info(f"[admin_user_profile][ADD/EDIT fucntion] New/Amend user for name:{name} & group:{group} & role:{role}.")

        if not (group and role and login_id and password and name):
            messagebox.showerror("Validation Error", "Please fill in all required fields.\n(either group/role/login ID/Password is empty)")
            return

        group_id = self.group_dict.get(group)
        role_query = "SELECT NUM_ROLE_ID FROM TM_MST_ROLE WHERE VCH_ROLE_NAME = %s"
        role_id = executionWithRs_query(role_query, (role,))
        if not role_id:
            logger.logger.info("[admin_user_profile][ADD/EDIT fucntion] Error-Invalid role selection")
            messagebox.showerror("Error", "Invalid role selection.")
            return
        role_id = role_id[0][0]

        supervisor_id = self.supervisor_dict.get(supervisor)
        if supervisor_id is None:
            logger.logger.info("[admin_user_profile][ADD/EDIT fucntion] No supervisor ID tagging")
            supervisor_id = None  # explicit NULL

        # Perform password encryption
        hashed_password = hash_password(password)

        # Insert into TM_MST_USER
        insert_user_sql = """
            INSERT INTO TM_MST_USER (
                VCH_LOGIN_ID, VCH_USER_NAME, VCH_PASSWORD, VCH_EMAIL, VCH_CONTACT,
                VCH_ADDRESS_1, VCH_ADDRESS_2, VCH_ADDRESS_3, VCH_ADDRESS_4,
                NUM_SUPERVISOR_ID, CHR_ACTIVE_IND, NUM_CREATED_BY
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Y', 1)
            RETURNING NUM_USER_ID
        """
        user_values = (login_id, name, hashed_password, email, contact, addr1, addr2, addr3, addr4, supervisor_id)
        user_result = executionWithRs_queryWithCommit(insert_user_sql, user_values)
        if not user_result:
            logger.logger.info("[admin_user_profile][ADD/EDIT fucntion] Insert Failed - Failed to insert user record")
            messagebox.showerror("Insert Failed", "Failed to insert user record.")
            return
        user_id = user_result[0][0]

        # Insert into TM_MST_USER_ASSIGNMENT
        insert_assignment_sql = """
            INSERT INTO TM_MST_USER_ASSIGNMENT (
                NUM_USER_ID, NUM_ROLE_ID, NUM_GROUP_ID, CHR_ACTIVE_IND, NUM_CREATED_BY
            ) VALUES (%s, %s, %s, 'Y', 1)
        """
        conn = execute_query(insert_assignment_sql, (user_id, role_id, group_id), conn)
        if conn:
            commit(conn)
            messagebox.showinfo("Success", "User successfully added.")
            logger.logger.info(f"[admin_user_profile][ADD/EDIT fucntion] Success - User successfully added for name:{name} & group:{group} & role:{role}.")
        self.layer2_clean_entry_fields()
        self.search_users()

    def layer2_edit_user(self):
        selected = self.result_table.selection()
        logger.logger.info(f"[admin_user_profile][EDIT fucntion] record selected for {selected}")

        if not selected:
            messagebox.showwarning("No Selection", "Please select a record to edit.")
            return
        values = self.result_table.item(selected[0], 'values')
        self.entry_name_var.set(values[1])
        self.entry_login_id_var.set(values[2])
        self.entry_group_var.set(values[3])
        self.entry_role_var.set(values[4])
        self.entry_supervisor_var.set(values[5])

        # Password cannot be decrypted — show masked and prompt user to re-enter
        self.entry_password_var.set("")
        self.entry_password_entry.insert(0, "••••••")
        self.entry_password_entry.config(foreground="gray")  # Optional visual cue
        logger.logger.info("[admin_user_profile][EDIT fucntion] Password hidden, user must reset manually")

    def layer2_delete_user(self, global_info):
        conn = None
        selected = self.result_table.selection()
        logger.logger.info(f"[admin_user_profile][DELETE fucntion] record selected for {selected}")

        if not selected:
            messagebox.showwarning("No Selection", "Please select a record to delete.")
            return

        user_id = self.result_table.item(selected[0], 'values')[0]
        login_id = self.result_table.item(selected[0], 'values')[2]

        # Check if attempting to delete current login user
        if login_id == global_info["gb_login_id"]:
            messagebox.showwarning("Invalid Operation", "You cannot delete your own login account.")
            return

        # Check CHR_NO_DELETE_IND before allowing delete
        chk_sql = """
            SELECT CHR_NO_DELETE_IND FROM TM_MST_USER
            WHERE NUM_USER_ID = %s
        """
        result = executionWithRs_query(chk_sql, (user_id,))
        if result and result[0][0] == 'Y':
            messagebox.showwarning("Protected User", "This user belongs to a group that cannot be deleted.")
            return

        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this user?")
        if confirm:
            user_id = self.result_table.item(selected[0], 'values')[0]
            query = "UPDATE TM_MST_USER SET CHR_ACTIVE_IND = 'N' WHERE NUM_USER_ID = %s"
            conn = execute_query(query, (user_id,), conn)
            if conn:
                commit(conn)
                messagebox.showinfo("Deleted", "User has been deactivated.")
                logger.logger.info("[admin_user_profile][DELETE fucntion] Success - User successfully deactivated")
            self.refresh_result_grid()

    def layer2_clean_entry_fields(self):
        self.entry_group_var.set("")
        self.entry_role_var.set("")
        self.entry_login_id_var.set("")
        self.entry_password_var.set("")
        self.entry_supervisor_var.set("None")
        self.entry_name_var.set("")
        self.entry_email_var.set("")
        self.entry_contact_var.set("")
        self.entry_addr1_var.set("")
        self.entry_addr2_var.set("")
        self.entry_addr3_var.set("")
        self.entry_addr4_var.set("")

    def reset_password_dialog(self):
        conn = None
        selected = self.result_table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a user record from the table.")
            return

        selected_item = self.result_table.item(selected[0], 'values')
        user_id = selected_item[0]
        login_id = selected_item[2]
        logger.logger.info(f"[admin_user_profile] : To perform password reset for user_id={user_id}, login_id={login_id}")

        new_password = simpledialog.askstring("Reset Password", f"Enter new password for user '{login_id}':", show='*')
        if not new_password:
            logger.logger.info(f"[admin_user_profile] : Password reset Cancelled for user_id={user_id}, login_id={login_id}")
            return  # Cancelled or empty input

        hashed_pw = hash_password(new_password)
        sql = "UPDATE TM_MST_USER SET VCH_PASSWORD = %s, NUM_UPDATED_BY = 1, DTT_UPDATED_AT = CURRENT_TIMESTAMP WHERE NUM_USER_ID = %s"
        conn = execute_query(sql, (hashed_pw, user_id), conn)
        if conn:
            commit(conn)
            messagebox.showinfo("Success", f"Password for user '{login_id}' has been reset.")
            logger.logger.info(f"[admin_user_profile] : Password reset for user_id={user_id}, login_id={login_id}")

    def adjust_column_width(self):
        for col in self.result_table["columns"]:
            if col == "User ID":
                self.result_table.column(col, width=80, anchor="center")
            elif col == "User Name":
                self.result_table.column(col, width=140, anchor="w")
            elif col == "Login ID":
                self.result_table.column(col, width=120, anchor="center")
            elif col == "User Group":
                self.result_table.column(col, width=120, anchor="center")
            elif col == "User Role":
                self.result_table.column(col, width=120, anchor="center")
            elif col == "Supervisor Name":
                self.result_table.column(col, width=140, anchor="center")
            elif col in ["Created At", "Updated At"]:
                self.result_table.column(col, width=160, anchor="center")
            else:
                self.result_table.column(col, width=100, anchor="center")


if __name__ == '__main__':
    root = tk.Tk()
    app = UserProfileManager(root)
    root.mainloop()
