
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry

class EnquiryAndReportScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Enquiry and Report Generation")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f5")  # Light background color

        # Header Section
        self.create_header()
        
        # Filter Section
        self.create_filter_section()

        # Results Section
        self.create_results_section()

        # Footer Section
        self.create_footer()

        # Load Dummy Data
        self.load_dummy_data()

    def create_header(self):
        header_frame = tk.Frame(self.root, bg="#4CAF50", height=60)
        header_frame.pack(fill=tk.X)

        # Title
        title_label = tk.Label(header_frame, text="Enquiry and Report Generation", font=("Helvetica", 18, "bold"), bg="#4CAF50", fg="white")
        title_label.pack(pady=10)

        # Breadcrumb Navigation
        breadcrumb_label = tk.Label(self.root, text="Home > Enquiry", font=("Helvetica", 12), bg="#f0f0f5", fg="#555")
        breadcrumb_label.pack(anchor="w", padx=20, pady=5)

    def create_filter_section(self):
        filter_frame = tk.LabelFrame(self.root, text="Filters", font=("Helvetica", 12, "bold"), bg="#ffffff", fg="#333", bd=2, relief=tk.GROOVE)
        filter_frame.pack(pady=10, fill=tk.X, padx=20)

        def create_label_input(row, col, text, widget):
            tk.Label(filter_frame, text=text, bg="#ffffff", font=("Helvetica", 10)).grid(row=row, column=col, padx=10, pady=5, sticky="w")
            widget.grid(row=row, column=col+1, padx=10, pady=5, sticky="w")

        # 1 Column
        self.agent_login_id_var = tk.StringVar()
        create_label_input(0, 0, "Agent Login ID:", ttk.Entry(filter_frame, textvariable=self.agent_login_id_var))

        self.customer_name_var = tk.StringVar()
        create_label_input(1, 0, "Customer Name:", ttk.Entry(filter_frame, textvariable=self.customer_name_var))

        self.trx_date_from_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(2, 0, "Transaction Date From:", self.trx_date_from_var)

        self.data_entry_source_var = tk.StringVar()
        create_label_input(3, 0, "Data Entry Source:", ttk.Entry(filter_frame, textvariable=self.data_entry_source_var))

        # 2 Column
        self.agent_name_var = tk.StringVar()
        create_label_input(0, 2, "Agent Name:", ttk.Entry(filter_frame, textvariable=self.agent_name_var))

        self.bank_var = tk.StringVar()
        create_label_input(1, 2, "Bank:", ttk.Entry(filter_frame, textvariable=self.bank_var))

        self.trx_date_to_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(2, 2, "Transaction Date To:", self.trx_date_to_var)

        # 3 Column
        self.user_group_var = tk.StringVar()
        create_label_input(0, 4, "User Group:", ttk.Entry(filter_frame, textvariable=self.user_group_var))

        self.transaction_desc_var = tk.StringVar()
        create_label_input(1, 4, "Transaction Description:", ttk.Entry(filter_frame, textvariable=self.transaction_desc_var))

        self.data_entry_date_from_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(2, 4, "Data Entry Date From:", self.data_entry_date_from_var)


        # 4 Column
        self.user_role_var = tk.StringVar()
        create_label_input(0, 6, "User Role:", ttk.Entry(filter_frame, textvariable=self.user_role_var))

        self.printed_status_var = tk.StringVar()
        create_label_input(1, 6, "Printed Status:", ttk.Entry(filter_frame, textvariable=self.printed_status_var))

        self.data_entry_date_to_var = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(2, 6, "Data Entry Date To:", self.data_entry_date_to_var)

        # Radio Buttons
        # self.transaction_mode_var = tk.StringVar(value="Single")
        # radio_frame = tk.Frame(filter_frame, bg="#ffffff")
        # radio_frame.grid(row=6, column=2, columnspan=2, pady=10, sticky="w")
        # tk.Radiobutton(radio_frame, text="Single Transaction", variable=self.transaction_mode_var, value="Single", bg="#ffffff", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=10)
        # tk.Radiobutton(radio_frame, text="Aggregated Transaction", variable=self.transaction_mode_var, value="Aggregated", bg="#ffffff", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=10)

        # Buttons
        button_frame = tk.Frame(filter_frame, bg="#ffffff")
        button_frame.grid(row=4, columnspan=4, pady=10)

        ttk.Button(button_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Clear Filters", command=self.clear_filters).pack(side=tk.LEFT, padx=10)

    def create_results_section(self):
        results_frame = tk.Frame(self.root, bg="#ffffff")
        results_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        # Table
        columns = [
            "Customer Name", "Transaction Description", "Transaction Date", "Credit Amount", "Debit Amount", "Bank",
            "Printed Status", "Agent Name", "Agent Login ID", "Agent Group", "Agent Role", "Data Entry Source", "Date Entry Date"
        ]
        self.results_table = ttk.Treeview(results_frame, columns=columns, show="headings")
        self.results_table.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            self.results_table.heading(col, text=col, anchor="w")
            self.results_table.column(col, anchor="w", width=150)

        # Scrollbars
        y_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_table.yview)
        self.results_table.configure(yscroll=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Pagination and Actions
        pagination_frame = tk.Frame(self.root, bg="#f0f0f5")
        pagination_frame.pack(fill=tk.X, pady=5, padx=20)

        self.page_label = tk.Label(pagination_frame, text="Page 1 of 10", bg="#f0f0f5", font=("Helvetica", 10))
        self.page_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(pagination_frame, text="Export to Excel", command=self.export_to_excel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(pagination_frame, text="Export to PDF", command=self.export_to_pdf).pack(side=tk.RIGHT, padx=5)
        ttk.Button(pagination_frame, text="Export to Plaint Text", command=self.export_to_plainttext).pack(side=tk.RIGHT, padx=5)

    def create_footer(self):
        footer_frame = tk.Frame(self.root, bg="#4CAF50")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        support_label = tk.Label(footer_frame, text="Contact Helpdesk: Email: Euwin@example.com | Phone: +60 16-284 3121", font=("Helvetica", 10), bg="#4CAF50", fg="white")
        support_label.pack()

    def load_dummy_data(self):
        dummy_data = [
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","06-September-2024","","RM -3000","MAYBANK","Printed","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","06-October-2024"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","12-September-2024","RM +2000","","MAYBANK","Printed","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","06-October-2024"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","20-September-2024","","RM -3000","MAYBANK","Printed","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","06-October-2024"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","24-September-2024","RM +2000","","MAYBANK","Printed","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","06-October-2024"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","01-October-2024","","RM -3000",  "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","10-October-2024","RM +5000","",  "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","17-October-2024","","RM -3000",  "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","24-October-2024","","RM -3000",  "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","26-October-2024","RM +2400","",  "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","MANUAL ENTRY","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","26-October-2024","RM +2600","",  "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","02-November-2024","","RM -2500", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","MANUAL ENTRY","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","09-November-2024","","RM -3000", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","20-November-2024","RM +4000","", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","27-November-2024","","RM -2500", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","04-December-2024","RM +1250","", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","06-December-2024","","RM -1500", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","07-December-2024","","RM -1000", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","PDF DOCX UPLOAD","01-January-2025"],
            ["YAP CHEIN PHANG","SKT MATERIAL ENTER(Tele)","11-December-2024","","RM -2500", "MAYBANK","Ready","Max","A0001","GROUP A","DATA ENTRY","IMAGE UPLOAD","01-January-2025"],
            ["SAIFUL NIZAM BIN AHMAD","ANBARASI A/P PUSPAN(Tele)","01-December-2024","RM +1400","","HONG LEONG BANK","Ready","James","A0002","GROUP B","DATA ENTRY","PDF DOCX UPLOAD","25-December-2024"],
            ["SAIFUL NIZAM BIN AHMAD","ANBARASI A/P PUSPAN(Tele)","07-December-2024","","RM -500", "HONG LEONG BANK","Ready","James","A0002","GROUP B","DATA ENTRY","PDF DOCX UPLOAD","25-December-2024"],
            ["SAIFUL NIZAM BIN AHMAD","ANBARASI A/P PUSPAN(Tele)","14-December-2024","","RM -500", "HONG LEONG BANK","Ready","James","A0002","GROUP B","DATA ENTRY","PDF DOCX UPLOAD","25-December-2024"],
            ["SAIFUL NIZAM BIN AHMAD","ANBARASI A/P PUSPAN(Tele)","19-December-2024","","RM -500", "HONG LEONG BANK","Ready","James","A0002","GROUP B","DATA ENTRY","PDF DOCX UPLOAD","25-December-2024"],
            ["SAIFUL NIZAM BIN AHMAD","ANBARASI A/P PUSPAN(Tele)","19-December-2024","RM +900","", "HONG LEONG BANK","Ready","James","A0002","GROUP B","DATA ENTRY","PDF DOCX UPLOAD","25-December-2024"]

        ]

        for record in sorted(dummy_data, key=lambda x: (x[0], x[1], x[2], x[4], x[5], x[6])):
            self.results_table.insert("", tk.END, values=record)

    def search(self):
        # Placeholder for search logic
        messagebox.showinfo("Search", "Search triggered.")

    def clear_filters(self):
        # Clear all filter fields
        self.agent_login_id_var.set("")
        self.user_group_var.set("")
        self.customer_name_var.set("")
        self.transaction_desc_var.set("")
        self.trx_date_from_var.set("")
        self.data_entry_date_from_var.set("")
        self.data_entry_source_var.set("")
        self.agent_name_var.set("")
        self.user_role_var.set("")
        self.bank_var.set("")
        self.printed_status_var.set("")
        self.trx_date_to_var.set("")
        self.data_entry_date_from_var.set("")


    def export_to_excel(self):
        # Placeholder for export logic
        messagebox.showinfo("Export", "Export to Excel triggered.")

    def export_to_pdf(self):
        # Placeholder for view details logic
        messagebox.showinfo("Export", "Export to PDF triggered.")

    def export_to_plainttext(self):
        # Placeholder for export logic
        messagebox.showinfo("Export", "Export to Plaint Text triggered.")

if __name__ == "__main__":
    root = tk.Tk()
    app = EnquiryAndReportScreen(root)
    root.mainloop()
