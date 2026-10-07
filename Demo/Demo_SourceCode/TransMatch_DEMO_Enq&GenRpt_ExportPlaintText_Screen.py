import tkinter as tk
from tkinter import ttk, scrolledtext

class EnquiryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enquiry and Report Generation")
        self.root.geometry("800x600")

        # Menu Button
        self.create_menu()

    def create_menu(self):
        menu_frame = tk.Frame(self.root)
        menu_frame.pack(pady=10, padx=10)

        ttk.Button(menu_frame, text="Enquiry", command=self.open_report_screen).pack()

    def open_report_screen(self):
        # Clear the main window
        for widget in self.root.winfo_children():
            widget.destroy()

        # Title
        tk.Label(self.root, text="Report Details", font=("Arial", 16, "bold")).pack(pady=10)

        # ScrolledText for displaying the report
        report_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=80, height=30, font=("Courier", 10))
        report_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Generate the plain text report content
        plaintext_report = self.generate_report()
        report_text.insert(tk.END, plaintext_report)

        # Back Button
        ttk.Button(self.root, text="Back to Menu", command=self.create_menu).pack(pady=10)

    def generate_report(self):
        customer_name = "MR/ENCIK YAP CHEIN PHANG"
        agent_name = "Max"
        agent_login_id = "A0001"

        transactions_by_description = {
            "TJJ BEAUTY AC(Tele)": [
                {"Transaction Date": "30-Sep-24", "Bank": "MBB", "Credit Amount": "RM +7000", "Debit Amount": ""},
                {"Transaction Date": "09-Oct-24", "Bank": "MBB", "Credit Amount": "", "Debit Amount": "RM -5000"},
                {"Transaction Date": "18-Oct-24", "Bank": "MBB", "Credit Amount": "RM +1500", "Debit Amount": ""},
                {"Transaction Date": "01-Nov-24", "Bank": "MBB", "Credit Amount": "RM +3000", "Debit Amount": ""},
            ],
            "STYLE CITY TR(Tele)": [
                {"Transaction Date": "30-Nov-24", "Bank": "MBB", "Credit Amount": "RM +4000", "Debit Amount": ""},
                {"Transaction Date": "06-Dec-24", "Bank": "MBB", "Credit Amount": "", "Debit Amount": "RM -1500"},
                {"Transaction Date": "07-Dec-24", "Bank": "MBB", "Credit Amount": "", "Debit Amount": "RM -1000"},
            ]
        }

        report_content = f"Customer Name: *{customer_name}*\n\n"

        for description, transactions in transactions_by_description.items():
            report_content += f"Transaction Description: *{description}*\n"
            report_content += "Date | Bank | Amount\n"
            report_content += "-----------------------------------\n"
            for transaction in transactions:
                amount = transaction["Credit Amount"] or transaction["Debit Amount"]
                report_content += (
                    f"{transaction['Transaction Date']} | "
                    f"{transaction['Bank']} | "
                    f"{amount}\n"
                )
            report_content += "\n"

        report_content += f"Agent Name: {agent_name}\n"
        report_content += f"Agent Login ID: {agent_login_id}\n"

        return report_content

if __name__ == "__main__":
    root = tk.Tk()
    app = EnquiryApp(root)
    root.mainloop()
