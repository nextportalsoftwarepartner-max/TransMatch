class PlainTextReport:
    def __init__(self, customer_name, agent_name, agent_login_id):
        self.customer_name = customer_name
        self.agent_name = agent_name
        self.agent_login_id = agent_login_id
        self.report_content = ""
        self.bank_mapping = {
            "MAYBANK": "MBB",
            "MAYBANK ISLAMIC": "MBIB",
            "PUBLIC BANK": "PBB",
            "PUBLIC BANK ISLAMIC": "PBIB",
            "HONG LEONG BANK": "HLB",
            "HONG LEONG BANK ISLAMIC": "HLIB",
            "AMBANK BANK": "AMB",
            "AMBANK BANK ISLAMIC": "AMIB",
            "RHB": "RHB",
            "RHB ISLAMIC": "RHBI"
        }

    def add_customer_header(self):
        self.report_content += f"Customer Name: *{self.customer_name}*\n\n"

    def add_transaction_section(self, transaction_description, transactions):
        self.report_content += f"Transaction Description: *{transaction_description}*\n"
        self.report_content += "Date | Bank | Amount\n"
        self.report_content += "-----------------------------------\n"
        for transaction in transactions:
            amount = transaction["Credit Amount"] or transaction["Debit Amount"]
            # Shorten the year to YY format
            date_parts = transaction['Transaction Date'].split("-")
            short_date = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2][2:]}"  # DD-MMM-YY
            # Map the bank name to its abbreviation
            bank = self.bank_mapping.get(transaction['Bank'].strip(), transaction['Bank'].strip())
            self.report_content += (
                f"{short_date.strip()} | "
                f"{bank} | "
                f"{amount.strip()}\n"
            )
        self.report_content += "\n"

    def add_footer(self):
        self.report_content += f"Agent Name: {self.agent_name}\n"
        self.report_content += f"Agent Login ID: {self.agent_login_id}\n"

    def generate_report(self):
        return self.report_content


# Dummy data for demonstration
customer_name = "MR/ENCIK YAP CHEIN PHANG"
transactions_by_description = {
    "TJJ BEAUTY AC(Tele)": [
        {"Transaction Date": "30-Sep-2024", "Bank": "MAYBANK", "Credit Amount": "RM +7000", "Debit Amount": ""},
        {"Transaction Date": "09-Oct-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -5000"},
        {"Transaction Date": "18-Oct-2024", "Bank": "MAYBANK", "Credit Amount": "RM +1500", "Debit Amount": ""},
        {"Transaction Date": "01-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "RM +3000", "Debit Amount": ""},
    ],
    "STYLE CITY TR(Tele)": [
        {"Transaction Date": "30-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "RM +4000", "Debit Amount": ""},
        {"Transaction Date": "06-Dec-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1500"},
        {"Transaction Date": "07-Dec-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1000"},
    ],
    "CHIA YEE TING(Tele)": [
        {"Transaction Date": "25-Oct-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1500"},
        {"Transaction Date": "25-Oct-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1500"},
        {"Transaction Date": "01-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -3000"},
        {"Transaction Date": "08-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2500"},
    ],
    "SOM TUM TRADING(Tele)": [
        {"Transaction Date": "01-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "RM +5000", "Debit Amount": ""},
        {"Transaction Date": "08-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2000"},
        {"Transaction Date": "15-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "RM +4000", "Debit Amount": ""},
        {"Transaction Date": "22-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2500"},
        {"Transaction Date": "29-Nov-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2000"},
    ]
}
agent_name = "Max"
agent_login_id = "A0001"

# Generate Plain Text Report
report = PlainTextReport(customer_name, agent_name, agent_login_id)
report.add_customer_header()

for description, transactions in transactions_by_description.items():
    report.add_transaction_section(description, transactions)

report.add_footer()

# Output report content
plaintext_report = report.generate_report()
print(plaintext_report)

# Save to a file (optional)
with open("D:\\CHIANWEILON\\Software_Dev\\TransMatch\\Demo\\Customer_Transactions_Report.txt", "w") as file:
    file.write(plaintext_report)
print("Plain text report generated successfully.")
