import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry


class TransMatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TransMatch System - Duplicate Demo")
        self.root.geometry("1920x1080")  # Set window size to 1920x1080

        # Create Notebook for tabs
        self.create_tabs()

    def create_tabs(self):
        # Create a notebook (tabbed interface)
        style = ttk.Style()
        style.configure('TNotebook.Tab', padding=(20, 10), font=("Arial", 12, "bold"))  # Double the tab size

        notebook = ttk.Notebook(self.root, style='TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True)

        # Transaction Tab
        transaction_tab = ttk.Frame(notebook)
        notebook.add(transaction_tab, text="Transaction")
        self.create_transaction_tab(transaction_tab)

        # Administration Tab
        administration_tab = ttk.Frame(notebook)
        notebook.add(administration_tab, text="Administration")
        self.create_administration_tab(administration_tab)

        # Report / Enquiry Tab
        report_tab = ttk.Frame(notebook)
        notebook.add(report_tab, text="Report / Enquiry")
        self.create_report_tab(report_tab)

    def create_transaction_tab(self, parent):
        # Add menus to Transaction tab
        menu_frame = tk.Frame(parent, bg="white", relief=tk.RAISED, borderwidth=2)
        menu_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Arrange buttons in 10 rows and 4 columns
        buttons = [
            ("Docx Upload (.pdf)", self.docx_upload),
            ("Manual Data Input", self.manual_data_input),
            ("Image Upload", self.image_upload),
            ("Data Enrichment", self.data_enrichment)
        ]

        style = ttk.Style()
        style.configure("Custom.TButton", font=("Arial", 13))  # Set font size

        for idx, (text, command) in enumerate(buttons):
            row, col = divmod(idx, 4)  # Calculate row and column position
            button = ttk.Button(menu_frame, text=text, command=command, style="Custom.TButton")
            button.grid(row=row, column=col, padx=10, pady=10, ipadx=50, ipady=20, sticky="ew")

        # Ensure 10 rows and 4 columns for consistent grid structure
        for row in range(10):
            menu_frame.rowconfigure(row, weight=1)
        for col in range(4):
            menu_frame.columnconfigure(col, weight=1)

    def docx_upload(self):
        # Create a new window for PDF upload
        upload_window = tk.Toplevel(self.root)
        upload_window.title("Docx Upload (.pdf)")
        upload_window.geometry("1200x800")

        # Upload field
        upload_frame = tk.Frame(upload_window, bg="white")
        upload_frame.pack(pady=10, padx=10, fill=tk.X)

        tk.Label(upload_frame, text="Select PDF File:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        self.file_path_entry = ttk.Entry(upload_frame, font=("Arial", 12), width=50)
        self.file_path_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(upload_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)

        # Scrollable frame for table
        table_container = tk.Frame(upload_window)
        table_container.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)

        x_scrollbar = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        y_scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.data_table = ttk.Treeview(
            table_container,
            columns=[
                "Bank Name", "Bank Address 1", "Bank Address 2", "Bank Address 3", "Bank Address 4", "Customer Name",
                "Customer Address 1", "Customer Address 2", "Customer Address 3", "Customer Address 4", "Statement Date",
                "Account Number", "Transaction Date", "Transaction Description 1", "Transaction Description 2",
                "Transaction Description 3", "Transaction Description 4", "Transaction Amount (Credit)",
                "Transaction Amount (Debit)", "Statement Balance"
            ],
            show="headings",
            xscrollcommand=x_scrollbar.set,
            yscrollcommand=y_scrollbar.set,
            height=15
        )

        self.data_table.pack(fill=tk.BOTH, expand=True)

        x_scrollbar.config(command=self.data_table.xview)
        y_scrollbar.config(command=self.data_table.yview)

        for col in self.data_table['columns']:
            self.data_table.heading(col, text=col)
            self.data_table.column(col, width=200, anchor="center")

        # Populate dummy data
        self.populate_dummy_data()

        # Buttons
        button_frame = tk.Frame(upload_window, bg="white")
        button_frame.pack(pady=10, padx=10, fill=tk.X)

        ttk.Button(button_frame, text="Save", command=self.save_data).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset", command=self.reset_data).pack(side=tk.LEFT, padx=10)

    def populate_dummy_data(self):
        dummy_data = [
            ["Maybank Islamic Berhad (787435-M)","15th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59000 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 2","BDR PUCHONG JAYA","47100 PUCHONG","SELANGOR","31/10/24","562348562755","10-Jan","TRANSFER TO A/C","ZANHERN BUILDER SDN*","Petty","","1000","","1811.05"],
            ["Maybank Islamic Berhad (787435-M)","16th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59001 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 3","BDR PUCHONG JAYA","47101 PUCHONG","SELANGOR","31/10/25","562348562756","10-Jan","CDM CASH DEPOSIT","","","","1750","","3561.05"],
            ["Maybank Islamic Berhad (787435-M)","17th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59002 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 4","BDR PUCHONG JAYA","47102 PUCHONG","SELANGOR","31/10/26","562348562757","10-Jan","TRANSFER FR A/C","SKT MATERIAL ENTERP*","Fund","","3000","561.05",""],
            ["Maybank Islamic Berhad (787435-M)","18th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59003 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 5","BDR PUCHONG JAYA","47103 PUCHONG","SELANGOR","31/10/27","562348562758","10-Jan","TRANSFER FR A/C","WONG KOK HOE*","Idaman tiles","MBB CT","","550","11.05"],
            ["Maybank Islamic Berhad (787435-M)","19th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59004 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 6","BDR PUCHONG JAYA","47104 PUCHONG","SELANGOR","31/10/28","562348562759","10-Jan","PAYMENT VIA MYDEBIT","PUBLIC BANK BERHAD*","RAWANG"," MYS","","9","2.05"],
            ["Maybank Islamic Berhad (787435-M)","20th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59005 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 7","BDR PUCHONG JAYA","47105 PUCHONG","SELANGOR","31/10/29","562348562760","10-Jan","TRANSFER TO A/C","ZANHERN BUILDER SDN*","Rawang worker","","9500","","9502.05"],
            ["Maybank Islamic Berhad (787435-M)","21st Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59006 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 8","BDR PUCHONG JAYA","47106 PUCHONG","SELANGOR","31/10/30","562348562761","10-Jan","TRANSFER FR A/C","LAW GUAT HEONG*","Return","MBB CT","","8000","1502.05"],
            ["Maybank Islamic Berhad (787435-M)","22nd Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59007 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 9","BDR PUCHONG JAYA","47107 PUCHONG","SELANGOR","31/10/31","562348562762","10-Feb","PAYMENT VIA MYDEBIT","PUBLIC BANK BERHAD*","PETALING JAYA"," MYS","","1500","2.05"],
            ["Maybank Islamic Berhad (787435-M)","23rd Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59008 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 10","BDR PUCHONG JAYA","47108 PUCHONG","SELANGOR","31/10/32","562348562763","10-Feb","TRANSFER TO A/C","AMIR MAHMUD*","Payment","","450","","452.05"],
            ["Maybank Islamic Berhad (787435-M)","24th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59009 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 11","BDR PUCHONG JAYA","47109 PUCHONG","SELANGOR","31/10/33","562348562764","10-Feb","TRANSFER FR A/C","ONG SAN LING*","Fund","MBB CT","","450","2.05"],
            ["Maybank Islamic Berhad (787435-M)","25th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59010 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 12","BDR PUCHONG JAYA","47110 PUCHONG","SELANGOR","31/10/34","562348562765","10-Mar","TRANSFER TO A/C","ZANHERN BUILDER SDN*","Petty","","4000","","4002.05"],
            ["Maybank Islamic Berhad (787435-M)","26th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59011 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 13","BDR PUCHONG JAYA","47111 PUCHONG","SELANGOR","31/10/35","562348562766","10-Mar","PAYMENT FR A/C","","","","","3661","341.05"],
            ["Maybank Islamic Berhad (787435-M)","27th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59012 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 14","BDR PUCHONG JAYA","47112 PUCHONG","SELANGOR","31/10/36","562348562767","10-Mar","PRE-AUTH DEBIT","BHPETROL SERENDAH*","SERENDAH"," MY","","200","141.05"],
            ["Maybank Islamic Berhad (787435-M)","28th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59013 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 15","BDR PUCHONG JAYA","47113 PUCHONG","SELANGOR","31/10/37","562348562768","10-Mar","PRE-AUTH REFUND","BHPETROL SERENDAH*","SERENDAH"," MY","200","","341.05"],
            ["Maybank Islamic Berhad (787435-M)","29th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59014 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 16","BDR PUCHONG JAYA","47114 PUCHONG","SELANGOR","31/10/38","562348562769","10-Mar","SALE DEBIT","BHPETROL SERENDAH*","SERENDAH"," MY","","163.8","177.25"],
            ["Maybank Islamic Berhad (787435-M)","30th Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59015 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 17","BDR PUCHONG JAYA","47115 PUCHONG","SELANGOR","31/10/39","562348562770","10-Mar","TRANSFER TO A/C","ZANHERN BUILDER SDN*","Petty","","2000","","2177.25"],
            ["Maybank Islamic Berhad (787435-M)","31st Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59016 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 18","BDR PUCHONG JAYA","47116 PUCHONG","SELANGOR","31/10/40","562348562771","10-Mar","PAYMENT VIA MYDEBIT","PUBLIC BANK BERHAD*","PETALING JAYA"," MYS","","2000","177.25"],
            ["Maybank Islamic Berhad (787435-M)","32nd Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59017 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 19","BDR PUCHONG JAYA","47117 PUCHONG","SELANGOR","31/10/41","562348562772","10-Mar","PAYMENT VIA MYDEBIT","7-ELEVEN MALAYSIA S*","RAWANG"," MYS","","6.5","170.75"],
            ["Maybank Islamic Berhad (787435-M)","33rd Floor, Tower A","Dataran Maybank, 1, Jalan Maarof","59018 Kuala Lumpur","IBS Puchong Jaya","MR / ENCIK YAP CHEIN PHANG","NO23 JLN TEMPUA 20","BDR PUCHONG JAYA","47118 PUCHONG","SELANGOR","31/10/42","562348562773","10-Apr","PAYMENT VIA MYDEBIT","PUBLIC BANK BERHAD*","KUALA LUMPUR"," MYS","","6.5","164.25"]
        ]

        for row in dummy_data:
            self.data_table.insert("", tk.END, values=row)

    def browse_file(self):
        # Open file dialog to select PDF
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)
            print(f"Selected file: {file_path}")

    def save_data(self):
        # Placeholder for save data logic
        print("Data saved successfully.")

    def reset_data(self):
        # Reset file path and clear table
        self.file_path_entry.delete(0, tk.END)
        for row in self.data_table.get_children():
            self.data_table.delete(row)
        print("Data reset successfully.")

    def manual_data_input(self):
        input_window = tk.Toplevel(self.root)
        input_window.title("Manual Data Input")
        input_window.geometry("1200x800")

        # Input fields
        input_frame = tk.Frame(input_window, bg="white")
        input_frame.pack(pady=20, padx=20, fill=tk.X)

        self.fields = [
            ("Bank Name", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Bank Address 1", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Bank Address 2", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Bank Address 3", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Bank Address 4", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Customer Name", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Customer Address 1", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Customer Address 2", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Customer Address 3", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Customer Address 4", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Statement Date", DateEntry(input_frame, font=("Arial", 12), width=28, background="darkblue", foreground="white", date_pattern="dd/mm/yyyy")),
            ("Account Number", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Transaction Date", DateEntry(input_frame, font=("Arial", 12), width=28, background="darkblue", foreground="white", date_pattern="dd/mm/yyyy")),
            ("Transaction Description 1", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Transaction Description 2", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Transaction Description 3", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Transaction Description 4", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Transaction Amount (Credit)", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Transaction Amount (Debit)", ttk.Entry(input_frame, font=("Arial", 12), width=30)),
            ("Statement Balance", ttk.Entry(input_frame, font=("Arial", 12), width=30))
        ]

        for idx, (label, entry) in enumerate(self.fields):
            row, col = divmod(idx, 2)
            tk.Label(input_frame, text=label, font=("Arial", 12), bg="white").grid(row=row, column=col * 2, padx=10, pady=5, sticky=tk.W)
            entry.grid(row=row, column=col * 2 + 1, padx=10, pady=5)

        # Buttons
        button_frame = tk.Frame(input_window, bg="white")
        button_frame.pack(pady=20, padx=20, fill=tk.X)

        ttk.Button(button_frame, text="Add", command=self.add_to_table).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Edit", command=self.edit_selected_row).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset", command=self.reset_fields).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=10)

        # Scrollable Grid Table
        table_frame = tk.Frame(input_window, bg="white")
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)

        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = [label for label, _ in self.fields]

        self.data_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15,
            xscrollcommand=x_scrollbar.set,
            yscrollcommand=y_scrollbar.set
        )
        self.data_table.pack(fill=tk.BOTH, expand=True)

        x_scrollbar.config(command=self.data_table.xview)
        y_scrollbar.config(command=self.data_table.yview)

        for col in columns:
            self.data_table.heading(col, text=col)
            self.data_table.column(col, width=150, anchor="center")

    def add_to_table(self):
        values = [entry.get() for _, entry in self.fields]
        self.data_table.insert("", tk.END, values=values)
        self.reset_fields()

    def edit_selected_row(self):
        selected_item = self.data_table.selection()
        if selected_item:
            values = self.data_table.item(selected_item, "values")
            for idx, (_, entry) in enumerate(self.fields):
                entry.delete(0, tk.END)
                entry.insert(0, values[idx])

    def reset_fields(self):
        for _, entry in self.fields:
            entry.delete(0, tk.END)

    def clear_all(self):
        # Clear all fields and the grid table
        self.reset_fields()
        for row in self.data_table.get_children():
            self.data_table.delete(row)

    def image_upload(self):
        print("Image Upload clicked")

    def data_enrichment(self):
        print("Data Enrichment clicked")

    def create_administration_tab(self, parent):
        # Add menu to Administration tab
        self.admin_menu_frame = tk.Frame(parent, bg="white", relief=tk.RAISED, borderwidth=2)
        self.admin_menu_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Single button for User Management
        style = ttk.Style()
        style.configure("Admin.TButton", font=("Arial", 13))

        self.user_management_button = ttk.Button(
            self.admin_menu_frame,
            text="User Management",
            command=self.display_user_management_menus,
            style="Admin.TButton"
        )
        self.user_management_button.grid(row=0, column=0, padx=10, pady=10, ipadx=50, ipady=20, sticky="ew")

        # Ensure 10 rows and 4 columns for consistent grid structure
        for row in range(10):
            self.admin_menu_frame.rowconfigure(row, weight=1)
        for col in range(4):
            self.admin_menu_frame.columnconfigure(col, weight=1)

    def create_report_tab(self, parent):
        menu_frame = tk.Frame(parent, bg="white", relief=tk.RAISED, borderwidth=2)
        menu_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # ttk.Button(menu_frame, text="Enquiry / Generate Report", command=self.create_enquiry_tab).pack(pady=20)
        # ttk.Button(menu_frame, text="KPI Review", command=self.dummy_function).pack(pady=20)

        # Arrange buttons in 10 rows and 4 columns
        buttons = [
            ("Enquiry / Generate Report", self.create_enquiry_tab),
            ("KPI Review", self.create_kpi_review_menu)
        ]

        style = ttk.Style()
        style.configure("Custom.TButton", font=("Arial", 13))  # Set font size

        for idx, (text, command) in enumerate(buttons):
            row, col = divmod(idx, 4)  # Calculate row and column position
            button = ttk.Button(menu_frame, text=text, command=command, style="Custom.TButton")
            button.grid(row=row, column=col, padx=10, pady=10, ipadx=50, ipady=20, sticky="ew")

        # Ensure 10 rows and 4 columns for consistent grid structure
        for row in range(10):
            menu_frame.rowconfigure(row, weight=1)
        for col in range(4):
            menu_frame.columnconfigure(col, weight=1)

    def create_enquiry_tab(self, parent=None):
        enquiry_window = tk.Toplevel(self.root)
        enquiry_window.title("Enquiry and Report Generation")
        enquiry_window.geometry("1920x1080")
        enquiry_window.configure(bg="#f0f0f5")

        self.create_enquiry_header(enquiry_window)
        self.create_enquiry_filters(enquiry_window)
        self.create_enquiry_results(enquiry_window)
        self.create_enquiry_footer(enquiry_window)

    def create_enquiry_header(self, window):
        header_frame = tk.Frame(window, bg="#4CAF50", height=60)
        header_frame.pack(fill=tk.X)

        title_label = tk.Label(header_frame, text="Enquiry and Report Generation", font=("Helvetica", 18, "bold"), bg="#4CAF50", fg="white")
        title_label.pack(pady=10)

        breadcrumb_label = tk.Label(window, text="Home > Enquiry", font=("Helvetica", 12), bg="#f0f0f5", fg="#555")
        breadcrumb_label.pack(anchor="w", padx=20, pady=5)

    def create_enquiry_filters(self, window):
        filter_frame = tk.LabelFrame(window, text="Filters", font=("Helvetica", 12, "bold"), bg="#ffffff", fg="#333", bd=2, relief=tk.GROOVE)
        filter_frame.pack(pady=10, fill=tk.X, padx=20)

        def create_label_input(row, col, text, widget):
            tk.Label(filter_frame, text=text, bg="#ffffff", font=("Helvetica", 10)).grid(row=row, column=col, padx=10, pady=5, sticky="w")
            widget.grid(row=row, column=col + 1, padx=10, pady=5, sticky="w")

        self.customer_name_var = tk.StringVar()
        self.trx_date_from_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        self.trx_date_to_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(0, 0, "Customer Name:", ttk.Entry(filter_frame, textvariable=self.customer_name_var))
        create_label_input(1, 0, "Transaction Date From:", self.trx_date_from_var)
        create_label_input(1, 2, "Transaction Date To:", self.trx_date_to_var)

        button_frame = tk.Frame(filter_frame, bg="#ffffff")
        button_frame.grid(row=3, columnspan=4, pady=10)

        ttk.Button(button_frame, text="Search", command=self.search_enquiry).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Clear Filters", command=self.clear_enquiry_filters).pack(side=tk.LEFT, padx=10)

    def create_enquiry_results(self, window):
        results_frame = tk.Frame(window, bg="#ffffff")
        results_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        columns = [
            "Customer Name", "Transaction Description", "Transaction Date", "Credit Amount", "Debit Amount", "Bank",
            "Printed Status", "Agent Name", "Agent Login ID", "Agent Group", "Agent Role", "Data Entry Source", "Date Entry Date"
        ]
        self.results_table = ttk.Treeview(results_frame, columns=columns, show="headings")
        self.results_table.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            self.results_table.heading(col, text=col, anchor="w")
            self.results_table.column(col, anchor="w", width=150)

        y_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_table.yview)
        self.results_table.configure(yscroll=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def create_enquiry_footer(self, window):
        footer_frame = tk.Frame(window, bg="#4CAF50")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        support_label = tk.Label(footer_frame, text="Contact Helpdesk: Email: Euwin@example.com | Phone: +60 16-284 3121", font=("Helvetica", 10), bg="#4CAF50", fg="white")
        support_label.pack()

    def search_enquiry(self):
        messagebox.showinfo("Search", "Search triggered.")

    def clear_enquiry_filters(self):
        self.customer_name_var.set("")
        self.trx_date_from_var.set("")
        self.trx_date_to_var.set("")

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
        filter_frame = tk.LabelFrame(window, text="Filter Criteria", font=("Helvetica", 12, "bold"), bg="#ffffff", fg="#333", bd=2, relief=tk.GROOVE)
        filter_frame.pack(pady=10, fill=tk.X, padx=20)

        def create_label_input(row, col, text, widget):
            tk.Label(filter_frame, text=text, bg="#ffffff", font=("Helvetica", 10)).grid(row=row, column=col, padx=10, pady=5, sticky="w")
            widget.grid(row=row, column=col + 1, padx=10, pady=5, sticky="w")

        self.user_group_var = tk.StringVar()
        create_label_input(0, 0, "User Group:", ttk.Entry(filter_frame, textvariable=self.user_group_var))

        self.user_role_var = tk.StringVar()
        create_label_input(1, 0, "User Role:", ttk.Entry(filter_frame, textvariable=self.user_role_var))

        self.agent_var = tk.StringVar()
        agent_frame = tk.Frame(filter_frame, bg="#ffffff")
        agent_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        agent_entry = ttk.Entry(agent_frame, textvariable=self.agent_var, state="disabled", width=30)
        agent_entry.pack(side=tk.LEFT, padx=5)
        search_icon = ttk.Button(agent_frame, text="🔍", command=self.open_agent_search)
        search_icon.pack(side=tk.LEFT)

        self.data_entry_date_from_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(0, 2, "Data Entry Date From:", self.data_entry_date_from_var)

        self.data_entry_date_to_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(1, 2, "Data Entry Date To:", self.data_entry_date_to_var)

        self.printed_status_var = tk.StringVar()
        create_label_input(2, 2, "Printed Status:", ttk.Entry(filter_frame, textvariable=self.printed_status_var))

        # Buttons
        button_frame = tk.Frame(filter_frame, bg="#ffffff")
        button_frame.grid(row=3, columnspan=4, pady=10)

        ttk.Button(button_frame, text="Search", command=self.search_kpi).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset", command=self.reset_kpi_filters).pack(side=tk.LEFT, padx=10)

    def open_agent_search(self):
        search_window = tk.Toplevel(self.root)
        search_window.title("Agent Search")
        search_window.geometry("800x600")
        search_window.configure(bg="#f0f0f5")

        # Dropdown and Search Field
        filter_frame = tk.Frame(search_window, bg="#ffffff", relief=tk.RAISED, borderwidth=2)
        filter_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(filter_frame, text="Search By:", font=("Helvetica", 12), bg="#ffffff").grid(row=0, column=0, padx=10, pady=5)
        self.search_by_var = tk.StringVar(value="Agent Login ID")
        search_by_dropdown = ttk.Combobox(filter_frame, textvariable=self.search_by_var, values=["Agent Login ID", "Agent Name"], state="readonly")
        search_by_dropdown.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(filter_frame, text="Search Text:", font=("Helvetica", 12), bg="#ffffff").grid(row=0, column=2, padx=10, pady=5)
        self.search_text_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_text_var).grid(row=0, column=3, padx=10, pady=5)

        ttk.Button(filter_frame, text="Search", command=self.perform_agent_search).grid(row=0, column=4, padx=10, pady=5)

        # Results Table
        results_frame = tk.Frame(search_window, bg="#ffffff")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.agent_results_table = ttk.Treeview(results_frame, columns=["Agent ID", "Agent Name"], show="headings")
        self.agent_results_table.heading("Agent ID", text="Agent ID")
        self.agent_results_table.heading("Agent Name", text="Agent Name")
        self.agent_results_table.column("Agent ID", width=200)
        self.agent_results_table.column("Agent Name", width=200)
        self.agent_results_table.pack(fill=tk.BOTH, expand=True)

        ttk.Button(search_window, text="Select", command=lambda: self.select_agent(search_window)).pack(pady=10)

    def perform_agent_search(self):
        dummy_data = [
            {"Agent ID": "A0001", "Agent Name": "John Doe"},
            {"Agent ID": "A0002", "Agent Name": "Jane Smith"},
        ]
        search_results = [item for item in dummy_data if self.search_text_var.get().lower() in item[self.search_by_var.get()].lower()]
        for row in self.agent_results_table.get_children():
            self.agent_results_table.delete(row)
        for result in search_results:
            self.agent_results_table.insert("", tk.END, values=(result["Agent ID"], result["Agent Name"]))

    def select_agent(self, window):
        selected_item = self.agent_results_table.selection()
        if selected_item:
            values = self.agent_results_table.item(selected_item, "values")
            self.agent_var.set(values[0])
            window.destroy()

    def create_kpi_results_section(self, window):
        results_frame = tk.Frame(window, bg="#ffffff")
        results_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        columns = ["Agent ID", "User Group", "User Role", "Printed Status (Count)"]
        self.results_table = ttk.Treeview(results_frame, columns=columns, show="headings")
        self.results_table.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            self.results_table.heading(col, text=col, anchor="w")
            self.results_table.column(col, anchor="w", width=200)

        # Scrollbars
        y_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_table.yview)
        self.results_table.configure(yscroll=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Export Section
        export_frame = tk.Frame(window, bg="#f0f0f5")
        export_frame.pack(fill=tk.X, pady=5, padx=20)

        ttk.Button(export_frame, text="Export to PDF", command=self.export_to_pdf).pack(side=tk.RIGHT, padx=5)
        ttk.Button(export_frame, text="Export to Excel", command=self.export_to_excel).pack(side=tk.RIGHT, padx=5)

    def create_menu_header(self, window, title):
        header_frame = tk.Frame(window, bg="#4CAF50", height=60)
        header_frame.pack(fill=tk.X)

        title_label = tk.Label(header_frame, text=title, font=("Helvetica", 18, "bold"), bg="#4CAF50", fg="white")
        title_label.pack(pady=10)

        breadcrumb_label = tk.Label(window, text="Home > " + title, font=("Helvetica", 12), bg="#f0f0f5", fg="#555")
        breadcrumb_label.pack(anchor="w", padx=20, pady=5)

    def create_menu_footer(self, window):
        footer_frame = tk.Frame(window, bg="#4CAF50")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        support_label = tk.Label(footer_frame, text="Contact Helpdesk: Email: Euwin@example.com | Phone: +60 16-284 3121", font=("Helvetica", 10), bg="#4CAF50", fg="white")
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

    def display_user_management_menus(self):
        # Clear the current menu frame
        for widget in self.admin_menu_frame.winfo_children():
            widget.destroy()

        # Add User Group, User Role, and User Rights menus
        buttons = [
            ("User Group", self.user_group),
            ("User Role", self.user_role),
            ("User Rights", self.user_rights),
        ]
        for idx, (text, command) in enumerate(buttons):
            row, col = divmod(idx, 4)  # Calculate row and column position
            button = ttk.Button(self.admin_menu_frame, text=text, command=command, style="Admin.TButton")
            button.grid(row=row, column=col, padx=10, pady=10, ipadx=50, ipady=20, sticky="ew")

        # Ensure 10 rows and 4 columns for consistent grid structure
        for row in range(10):
            self.admin_menu_frame.rowconfigure(row, weight=1)
        for col in range(4):
            self.admin_menu_frame.columnconfigure(col, weight=1)

    def user_group(self):
        print("User Group clicked")

    def user_role(self):
        print("User Role clicked")

    def user_rights(self):
        print("User Rights clicked")

if __name__ == "__main__":
    root = tk.Tk()
    app = TransMatchApp(root)
    root.mainloop()
