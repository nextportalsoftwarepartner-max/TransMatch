# flake8: noqa: E501

import tkinter as tk
import sys
import os
import logger
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from transaction.transaction_manager_manualInput import ManualTransactionInput
from report.enquiryScreen import EnquiryScreen
from transaction.transaction_pdf_upload import DocxUploader
from administration.blacklisted_manager import BlacklistedManager
from administration.suspicious_manager import SuspiciousManager
from administration.customer_manager import CustomerManager
from transaction.data_enrichment_main import DataEnrichment
from administration.admin_user_group import UserGroupManager
from administration.admin_user_role import UserRoleManager
from administration.admin_user_profile import UserProfileManager
from administration.bank_profile_manager import BankProfileManager
# from admin_user_Assignment import UserAssignmentManager

logger.logger.info("[TransMatch_main] : Menu initiation")

# Create a log file in the same directory as the EXE
# if getattr(sys, 'frozen', False):
#     base_dir = sys._MEIPASS
#     output_dir = os.path.dirname(sys.executable)
# else:
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     output_dir = base_dir

# Setup logging directory and file
if getattr(sys, 'frozen', False):
    logger.logger.info("[TransMatch_main] : Running in a PyInstaller bundle")
    output_dir = os.path.dirname(sys.executable)
else:
    logger.logger.info("[TransMatch_main] : Running in a normal Python process")
    output_dir = os.path.dirname(os.path.abspath(__file__))


def format_currency(value):
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return value


class TransMatchApp:
    def __init__(self, root, global_info):
        self.root = root
        self.root.title("TransMatch System")
        self.root.state('zoomed')  # Maximized mode (Windows)

        # Create Notebook for tabs
        self.create_tabs(global_info)
        logger.logger.info("[TransMatch_main] : Screen establisted completely")

    def create_tabs(self, global_info):
        logger.logger.info("[TransMatch_main] : Implement multiple menus in a tabbed interface")

        # Create a notebook (tabbed interface)
        style = ttk.Style()
        style.configure('TNotebook.Tab', padding=(20, 10), font=(
            "Arial", 12, "bold"))  # Double the tab size

        notebook = ttk.Notebook(self.root, style='TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True)

        # Transaction Tab
        transaction_tab = ttk.Frame(notebook)
        notebook.add(transaction_tab, text="Transaction")
        self.create_transaction_tab(transaction_tab, global_info)

        # Administration Tab
        administration_tab = ttk.Frame(notebook)
        notebook.add(administration_tab, text="Administration")
        self.create_administration_tab(administration_tab, global_info)

        # Report / Enquiry Tab
        report_tab = ttk.Frame(notebook)
        notebook.add(report_tab, text="Report / Enquiry")
        self.create_report_tab(report_tab, global_info)

    # ============= TAB Menu =============

    def create_transaction_tab(self, parent, global_info):
        logger.logger.info("[TransMatch_main] : Create multiple menus in TRANSACTION tab")

        # Add menus to Transaction tab  
        menu_frame = tk.Frame(parent, bg="white",
                              relief=tk.RAISED, borderwidth=2)
        menu_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Arrange buttons in 10 rows and 4 columns
        buttons = [
            ("Docx Upload", lambda: DocxUploader(self.root, global_info)),
            ("Manual Data Input", lambda: ManualTransactionInput(self.root, self.force_uppercase, global_info)),
            ("Image Upload", self.image_upload),
            ("Data Enrichment", lambda: DataEnrichment(self.root, global_info))
        ]

        style = ttk.Style()
        style.configure("Custom.TButton", font=("Arial", 13))  # Set font size

        for idx, (text, command) in enumerate(buttons):
            row, col = divmod(idx, 4)  # Calculate row and column position
            button = ttk.Button(menu_frame, text=text,
                                command=command, style="Custom.TButton")
            button.grid(row=row, column=col, padx=10, pady=10,
                        ipadx=50, ipady=20, sticky="ew")

        # Ensure 10 rows and 4 columns for consistent grid structure
        for row in range(10):
            menu_frame.rowconfigure(row, weight=1)
        for col in range(4):
            menu_frame.columnconfigure(col, weight=1)

    def create_administration_tab(self, parent, global_info):
        logger.logger.info("[TransMatch_main] : Create multiple menus in ADMINISTRATION tab")

        # Add menu to Administration tab
        self.admin_menu_frame = tk.Frame(
            parent, bg="white", relief=tk.RAISED, borderwidth=2)
        self.admin_menu_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Single button for User Management
        style = ttk.Style()
        style.configure("Admin.TButton", font=("Arial", 13))

        buttons = [
            ("User Group", lambda: UserGroupManager(self.root, global_info)),
            ("User Role", lambda: UserRoleManager(self.root, global_info)),
            ("User Profile", lambda: UserProfileManager(self.root, global_info)),
            ("User Access", lambda: UserAssignmentManager(self.root, global_info)),
            ("Customer Profile", lambda: CustomerManager(self.root, global_info)),
            ("Bank Profile", lambda: BankProfileManager(self.root, global_info)),
            ("Blacklisted", lambda: BlacklistedManager(self.root, global_info)),
            ("Suspicious", lambda: SuspiciousManager(self.root, global_info))
        ]

        for idx, (text, command) in enumerate(buttons):
            row, col = divmod(idx, 4)
            button = ttk.Button(self.admin_menu_frame, text=text,
                                command=command, style="Admin.TButton")
            button.grid(row=row, column=col, padx=10, pady=10,
                        ipadx=50, ipady=20, sticky="ew")

        for row in range(30):
            self.admin_menu_frame.rowconfigure(row, weight=1)
        for col in range(4):
            self.admin_menu_frame.columnconfigure(col, weight=1)

    def create_report_tab(self, parent, global_info):
        logger.logger.info("[TransMatch_main] : Create multiple menus in REPORT tab")

        menu_frame = tk.Frame(parent, bg="white",
                              relief=tk.RAISED, borderwidth=2)
        menu_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Arrange buttons in 10 rows and 4 columns
        buttons = [
            ("Enquiry / Generate Report", lambda: EnquiryScreen(self.root, global_info)),
            ("KPI Review", self.create_kpi_review_menu)
        ]

        style = ttk.Style()
        style.configure("Custom.TButton", font=("Arial", 13))  # Set font size

        for idx, (text, command) in enumerate(buttons):
            row, col = divmod(idx, 4)  # Calculate row and column position
            button = ttk.Button(menu_frame, text=text,
                                command=command, style="Custom.TButton")
            button.grid(row=row, column=col, padx=10, pady=10,
                        ipadx=50, ipady=20, sticky="ew")

        # Ensure 10 rows and 4 columns for consistent grid structure
        for row in range(10):
            menu_frame.rowconfigure(row, weight=1)
        for col in range(4):
            menu_frame.columnconfigure(col, weight=1)

    def image_upload(self):
        print("Image Upload clicked")

    def create_kpi_review_menu(self):
        kpi_window = tk.Toplevel(self.root)
        kpi_window.title("KPI Review")
        kpi_window.geometry("1920x1080")
        kpi_window.configure(bg="#f0f0f5")

        # Header Section
        self.create_menu_header(kpi_window, "KPI Review")

        # Filter Section
        self.create_kpi_filter_section(kpi_window)

        # Results Section
        self.create_kpi_results_section(kpi_window)

        # Footer Section
        self.create_menu_footer(kpi_window)

    def create_kpi_filter_section(self, window):
        filter_frame = tk.LabelFrame(window, text="Filter Criteria", font=(
            "Helvetica", 12, "bold"), bg="#ffffff", fg="#333", bd=2, relief=tk.GROOVE)
        filter_frame.pack(pady=10, fill=tk.X, padx=20)

        def create_label_input(row, col, text, widget):
            tk.Label(filter_frame, text=text, bg="#ffffff", font=("Helvetica", 10)).grid(
                row=row, column=col, padx=10, pady=5, sticky="w")
            widget.grid(row=row, column=col + 1, padx=10, pady=5, sticky="w")

        self.user_group_var = tk.StringVar()
        create_label_input(0, 0, "User Group:", ttk.Entry(
            filter_frame, textvariable=self.user_group_var))

        self.user_role_var = tk.StringVar()
        create_label_input(1, 0, "User Role:", ttk.Entry(
            filter_frame, textvariable=self.user_role_var))

        self.agent_var = tk.StringVar()
        agent_frame = tk.Frame(filter_frame, bg="#ffffff")
        agent_frame.grid(row=2, column=0, columnspan=2,
                         sticky="w", padx=10, pady=5)
        agent_entry = ttk.Entry(
            agent_frame, textvariable=self.agent_var, state="disabled", width=30)
        agent_entry.pack(side=tk.LEFT, padx=5)
        search_icon = ttk.Button(
            agent_frame, text="🔍", command=self.open_agent_search)
        search_icon.pack(side=tk.LEFT)

        self.data_entry_date_from_var = DateEntry(
            filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(0, 2, "Data Entry Date From:",
                           self.data_entry_date_from_var)

        self.data_entry_date_to_var = DateEntry(
            filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(1, 2, "Data Entry Date To:",
                           self.data_entry_date_to_var)

        self.printed_status_var = tk.StringVar()
        create_label_input(2, 2, "Printed Status:", ttk.Entry(
            filter_frame, textvariable=self.printed_status_var))

        # Buttons
        button_frame = tk.Frame(filter_frame, bg="#ffffff")
        button_frame.grid(row=3, columnspan=4, pady=10)

        ttk.Button(button_frame, text="Search",
                   command=self.search_kpi).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset", command=self.reset_kpi_filters).pack(
            side=tk.LEFT, padx=10)

    def open_agent_search(self):
        search_window = tk.Toplevel(self.root)
        search_window.title("Agent Search")
        search_window.geometry("800x600")
        search_window.configure(bg="#f0f0f5")

        # Dropdown and Search Field
        filter_frame = tk.Frame(
            search_window, bg="#ffffff", relief=tk.RAISED, borderwidth=2)
        filter_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(filter_frame, text="Search By:", font=("Helvetica", 12),
                 bg="#ffffff").grid(row=0, column=0, padx=10, pady=5)
        self.search_by_var = tk.StringVar(value="Agent Login ID")
        search_by_dropdown = ttk.Combobox(filter_frame, textvariable=self.search_by_var, values=[
                                          "Agent Login ID", "Agent Name"], state="readonly")
        search_by_dropdown.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(filter_frame, text="Search Text:", font=(
            "Helvetica", 12), bg="#ffffff").grid(row=0, column=2, padx=10, pady=5)
        self.search_text_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_text_var).grid(
            row=0, column=3, padx=10, pady=5)

        ttk.Button(filter_frame, text="Search", command=self.perform_agent_search).grid(
            row=0, column=4, padx=10, pady=5)

        # Results Table
        results_frame = tk.Frame(search_window, bg="#ffffff")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.agent_results_table = ttk.Treeview(
            results_frame, columns=["Agent ID", "Agent Name"], show="headings")
        self.agent_results_table.heading("Agent ID", text="Agent ID")
        self.agent_results_table.heading("Agent Name", text="Agent Name")
        self.agent_results_table.column("Agent ID", width=200)
        self.agent_results_table.column("Agent Name", width=200)
        self.agent_results_table.pack(fill=tk.BOTH, expand=True)

        ttk.Button(search_window, text="Select", command=lambda: self.select_agent(
            search_window)).pack(pady=10)

    def perform_agent_search(self):
        dummy_data = [
            {"Agent ID": "A0001", "Agent Name": "John Doe"},
            {"Agent ID": "A0002", "Agent Name": "Jane Smith"},
        ]
        search_results = [item for item in dummy_data if self.search_text_var.get(
        ).lower() in item[self.search_by_var.get()].lower()]
        for row in self.agent_results_table.get_children():
            self.agent_results_table.delete(row)
        for result in search_results:
            self.agent_results_table.insert("", tk.END, values=(
                result["Agent ID"], result["Agent Name"]))

    def select_agent(self, window):
        selected_item = self.agent_results_table.selection()
        if selected_item:
            values = self.agent_results_table.item(selected_item, "values")
            self.agent_var.set(values[0])
            window.destroy()

    def create_kpi_results_section(self, window):
        results_frame = tk.Frame(window, bg="#ffffff")
        results_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        columns = ["Agent ID", "User Group",
                   "User Role", "Printed Status (Count)"]
        self.results_table_kpi = ttk.Treeview(
            results_frame, columns=columns, show="headings")
        self.results_table_kpi.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            self.results_table_kpi.heading(col, text=col, anchor="w")
            self.results_table_kpi.column(col, anchor="w", width=200)

        # Scrollbars
        y_scroll = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.results_table_kpi.yview)
        self.results_table_kpi.configure(yscroll=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Export Section
        export_frame = tk.Frame(window, bg="#f0f0f5")
        export_frame.pack(fill=tk.X, pady=5, padx=20)

        ttk.Button(export_frame, text="Export to PDF",
                   command=self.export_to_pdf).pack(side=tk.RIGHT, padx=5)
        ttk.Button(export_frame, text="Export to Excel",
                   command=self.export_to_excel).pack(side=tk.RIGHT, padx=5)

    def create_menu_header(self, window, title):
        header_frame = tk.Frame(window, bg="#4CAF50", height=60)
        header_frame.pack(fill=tk.X)

        title_label = tk.Label(header_frame, text=title, font=(
            "Helvetica", 18, "bold"), bg="#4CAF50", fg="white")
        title_label.pack(pady=10)

        breadcrumb_label = tk.Label(
            window, text="Home > " + title, font=("Helvetica", 12), bg="#f0f0f5", fg="#555")
        breadcrumb_label.pack(anchor="w", padx=20, pady=5)

    def create_menu_footer(self, window):
        footer_frame = tk.Frame(window, bg="#4CAF50")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        support_label = tk.Label(footer_frame, text="Contact Helpdesk: Email: Euwin@example.com | Phone: +60 16-284 3121",
                                 font=("Helvetica", 10), bg="#4CAF50", fg="white")
        support_label.pack()

    def search_kpi(self):
        messagebox.showinfo("Search", "KPI Search triggered.")

    def reset_kpi_filters(self):
        self.user_group_var.set("")
        self.user_role_var.set("")
        self.agent_var.set("")
        self.data_entry_date_from_var.set("")
        self.data_entry_date_to_var.set("")
        self.printed_status_var.set("")

    def export_to_excel(self):
        messagebox.showinfo("Export", "Export to Excel triggered.")

    def export_to_pdf(self):
        messagebox.showinfo("Export", "Export to PDF triggered.")

    def create_user_group_menu(self):
        user_group_window = tk.Toplevel(self.root)
        user_group_window.title("User Group Configuration")
        user_group_window.geometry("1920x1080")
        user_group_window.configure(bg="#f0f0f5")

        # Header Section
        self.create_menu_header(user_group_window, "User Group Configuration")

        # Input Section
        self.create_user_group_input_section(user_group_window)

        # Results Section
        self.create_user_group_results_section(user_group_window)

        # Footer Section
        self.create_menu_footer(user_group_window)

    def create_user_group_input_section(self, window):
        input_frame = tk.LabelFrame(window, text="User Group Details", font=(
            "Helvetica", 12, "bold"), bg="#ffffff", fg="#333", bd=2, relief=tk.GROOVE)
        input_frame.pack(pady=10, fill=tk.X, padx=20)

        def create_label_input(row, col, text, widget):
            tk.Label(input_frame, text=text, bg="#ffffff", font=("Helvetica", 10)).grid(
                row=row, column=col, padx=10, pady=5, sticky="w")
            widget.grid(row=row, column=col + 1, padx=10, pady=5, sticky="w")

        self.user_group_name_var = tk.StringVar()
        create_label_input(0, 0, "User Group Name:", ttk.Entry(
            input_frame, textvariable=self.user_group_name_var))

        self.user_group_desc_var = tk.StringVar()
        create_label_input(1, 0, "User Group Description:", ttk.Entry(
            input_frame, textvariable=self.user_group_desc_var))

        self.effective_date_from_var = DateEntry(
            input_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(2, 0, "Effective Date From:",
                           self.effective_date_from_var)

        self.effective_date_to_var = DateEntry(
            input_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(3, 0, "Effective Date To:",
                           self.effective_date_to_var)

        self.active_flag_var = tk.StringVar(value="YES")
        create_label_input(4, 0, "Active Flag:", ttk.Combobox(
            input_frame, textvariable=self.active_flag_var, values=["YES", "NO"], state="readonly"))

        # Buttons
        button_frame = tk.Frame(input_frame, bg="#ffffff")
        button_frame.grid(row=5, columnspan=4, pady=10)

        ttk.Button(button_frame, text="Add", command=self.add_user_group).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Update",
                   command=self.update_user_group).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset", command=self.reset_user_group_fields).pack(
            side=tk.LEFT, padx=10)

    def create_user_group_results_section(self, window):
        results_frame = tk.Frame(window, bg="#ffffff")
        results_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        columns = ["User Group Name", "Description",
                   "Effective Date From", "Effective Date To", "Active Flag"]
        self.results_table = ttk.Treeview(
            results_frame, columns=columns, show="headings")
        self.results_table.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            self.results_table.heading(col, text=col, anchor="w")
            self.results_table.column(col, anchor="w", width=200)

        # Scrollbars
        y_scroll = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.results_table.yview)
        self.results_table.configure(yscroll=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate Dummy Data
        dummy_data = [
            ["Group A", "Kepong area Agency", "01-01-2025", "10-01-2025", "NO"],
            ["Group A", "Kepong area Agency", "01-01-2025", "", "YES"],
            ["Group B", "Cheras area Agency", "01-01-2025", "", "YES"]
        ]
        for record in sorted(dummy_data, key=lambda x: (x[0], x[4], x[2])):
            self.results_table.insert("", tk.END, values=record)

    def add_user_group(self):
        messagebox.showinfo("Add", "Add User Group triggered.")

    def update_user_group(self):
        messagebox.showinfo("Update", "Update User Group triggered.")

    def reset_user_group_fields(self):
        self.user_group_name_var.set("")
        self.user_group_desc_var.set("")
        self.effective_date_from_var.set_date("")
        self.effective_date_to_var.set_date("")
        self.active_flag_var.set("YES")

    def create_user_role_menu(self):
        user_role_window = tk.Toplevel(self.root)
        user_role_window.title("User Role Configuration")
        user_role_window.geometry("1920x1080")
        user_role_window.configure(bg="#f0f0f5")

        # Header Section
        self.create_menu_header(user_role_window, "User Role Configuration")

        # Input Section
        self.create_user_role_input_section(user_role_window)

        # Results Section
        self.create_user_role_results_section(user_role_window)

        # Footer Section
        self.create_menu_footer(user_role_window)

    def create_user_role_input_section(self, window):
        input_frame = tk.LabelFrame(window, text="User Role Details", font=(
            "Helvetica", 12, "bold"), bg="#ffffff", fg="#333", bd=2, relief=tk.GROOVE)
        input_frame.pack(pady=10, fill=tk.X, padx=20)

        def create_label_input(row, col, text, widget):
            tk.Label(input_frame, text=text, bg="#ffffff", font=("Helvetica", 10)).grid(
                row=row, column=col, padx=10, pady=5, sticky="w")
            widget.grid(row=row, column=col + 1, padx=10, pady=5, sticky="w")

        self.user_group_name_var = tk.StringVar()
        user_group_dropdown = ttk.Combobox(
            input_frame, textvariable=self.user_group_name_var, state="readonly")
        # Placeholder, replace with database fetch
        user_group_dropdown['values'] = ["Group A", "Group B"]
        user_group_dropdown.bind(
            "<<ComboboxSelected>>", self.update_user_group_description)
        create_label_input(0, 0, "User Group Name:", user_group_dropdown)

        self.user_group_desc_var = tk.StringVar()
        create_label_input(1, 0, "User Group Description:", ttk.Entry(
            input_frame, textvariable=self.user_group_desc_var, state="disabled"))

        self.user_role_name_var = tk.StringVar()
        create_label_input(2, 0, "User Role Name:", ttk.Entry(
            input_frame, textvariable=self.user_role_name_var))

        self.user_role_desc_var = tk.StringVar()
        create_label_input(3, 0, "User Role Description:", ttk.Entry(
            input_frame, textvariable=self.user_role_desc_var))

        self.effective_date_from_var = DateEntry(
            input_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(4, 0, "Effective Date From:",
                           self.effective_date_from_var)

        self.effective_date_to_var = DateEntry(
            input_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(5, 0, "Effective Date To:",
                           self.effective_date_to_var)

        self.active_flag_var = tk.StringVar(value="YES")
        create_label_input(6, 0, "Active Flag:", ttk.Combobox(
            input_frame, textvariable=self.active_flag_var, values=["YES", "NO"], state="readonly"))

        # Buttons
        button_frame = tk.Frame(input_frame, bg="#ffffff")
        button_frame.grid(row=7, columnspan=4, pady=10)

        ttk.Button(button_frame, text="Add", command=self.add_user_role).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Update",
                   command=self.update_user_role).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset", command=self.reset_user_role_fields).pack(
            side=tk.LEFT, padx=10)

    def update_user_group_description(self, event):
        selected_group = self.user_group_name_var.get()
        descriptions = {
            "Group A": "Kepong area Agency",
            "Group B": "Cheras area Agency"
        }
        self.user_group_desc_var.set(descriptions.get(selected_group, ""))

    def create_user_role_results_section(self, window):
        results_frame = tk.Frame(window, bg="#ffffff")
        results_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        columns = [
            "User Role Name", "User Role Description", "User Group Name", "User Group Description",
            "Effective Date From", "Effective Date To", "Active Flag"
        ]
        self.results_table = ttk.Treeview(
            results_frame, columns=columns, show="headings")
        self.results_table.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            self.results_table.heading(col, text=col, anchor="w")
            self.results_table.column(col, anchor="w", width=200)

        # Scrollbars
        y_scroll = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.results_table.yview)
        self.results_table.configure(yscroll=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate Dummy Data
        dummy_data = [
            ["Data Entry", "A role-based data entry function that supports uploading/inputting/enriching data.", "Group A",
             "Kepong area Agency", "01-01-2025", "10-01-2025", "NO"],
            ["Data Entry", "A role-based data entry function that supports uploading/inputting/enriching data.", "Group A",
             "Kepong area Agency", "01-01-2025", "", "YES"],
            ["Data Entry", "A role-based data entry function that supports uploading/inputting/enriching data.", "Group B",
             "Cheras area Agency", "01-01-2025", "", "YES"],
            ["Admin", "A role-based administrator responsible for managing system configuration settings.", "Group A",
             "Kepong area Agency", "01-01-2025", "", "YES"],
            ["Admin", "A role-based administrator responsible for managing system configuration settings.", "Group B",
             "Cheras area Agency", "01-01-2025", "", "YES"]
        ]
        for record in sorted(dummy_data, key=lambda x: (x[0], x[6], x[2], x[4])):
            self.results_table.insert("", tk.END, values=record)

    def add_user_role(self):
        messagebox.showinfo("Add", "Add User Role triggered.")

    def update_user_role(self):
        messagebox.showinfo("Update", "Update User Role triggered.")

    def reset_user_role_fields(self):
        self.user_group_name_var.set("")
        self.user_group_desc_var.set("")
        self.user_role_name_var.set("")
        self.user_role_desc_var.set("")
        self.effective_date_from_var.set_date("")
        self.effective_date_to_var.set_date("")
        self.active_flag_var.set("YES")

    def user_rights(self):
        print("User Rights clicked")

    def force_uppercase(self, var):
        current_value = var.get()
        var.set(current_value.upper())

    # def reset_all(self):
    #     """Clear static info, manual transaction entries, and the data table."""
    #     # 1) Static info fields
    #     self.reset_static_info_fields()
    #     # 2) Layer-2 entry fields
    #     self.clear_manual_transaction_fields()
    #     # 3) Layer-3 grid table
    #     for item in self.manual_data_table.get_children():
    #         self.manual_data_table.delete(item)


if __name__ == "__main__":
    root = tk.Tk()
    app = TransMatchApp(root) # pyright: ignore[reportCallIssue]
    root.mainloop()
