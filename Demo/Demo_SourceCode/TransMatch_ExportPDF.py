from fpdf import FPDF


class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Arial", size=12)

    def header(self):
        # Add watermark first
        self.watermark()
        # Add a header to the PDF
        self.set_font("Arial", style="B", size=16)
        self.cell(0, 10, "Customer Transactions Report", ln=True, align="C")
        self.ln(10)  # Add space below the header

    def footer(self):
        # Set the y-position closer to the bottom
        self.set_y(-20)  # Reduced from -30 to -20 for less space
        self.set_font("Arial", size=10)
        self.cell(
            0,
            5,
            f"Agent Name: {
                self.agent_name}",
            ln=True,
            align="L")  # Adjusted line height
        self.cell(
            0,
            5,
            f"Agent Login ID: {
                self.agent_login_id}",
            ln=True,
            align="L")  # Adjusted line height

    def add_customer_header(self, customer_name):
        # Add Customer Name header
        self.set_font("Arial", style="B", size=14)
        self.cell(0, 10, f"Customer Name: {customer_name}", ln=True, align="L")
        self.ln(5)

    def add_transaction_section(self, transaction_description, transactions):
        # Ensure enough space before starting a new section
        if self.get_y() > 250:  # Adjust this value for your layout
            self.add_page()
        else:
            self.ln(10)  # Add some space before the section

        # Add Transaction Description header
        self.set_font("Arial", style="B", size=12)
        self.cell(
            0,
            10,
            f"Transaction Description: {transaction_description}",
            ln=True,
            align="L")
        self.ln(5)  # Add space after the header

        # Add table headers
        self.set_font("Arial", style="B", size=11)
        self.cell(40, 10, "Transaction Date", border=1, align="C")
        self.cell(50, 10, "Bank", border=1, align="C")
        self.cell(40, 10, "Credit Amount", border=1, align="C")
        self.cell(40, 10, "Debit Amount", border=1, align="C")
        self.ln()

        # Add transaction rows
        self.set_font("Arial", size=11)
        for transaction in transactions:
            # Check if there's enough space for the next row
            if self.get_y() > 260:  # Adjust this value as needed
                self.add_page()
                self.cell(
                    0,
                    10,
                    f"Transaction Description: {transaction_description}",
                    ln=True,
                    align="L")
                self.ln(5)
                self.cell(40, 10, "Transaction Date", border=1, align="C")
                self.cell(50, 10, "Bank", border=1, align="C")
                self.cell(40, 10, "Credit Amount", border=1, align="C")
                self.cell(40, 10, "Debit Amount", border=1, align="C")
                self.ln()

            self.cell(
                40,
                10,
                transaction["Transaction Date"],
                border=1,
                align="C")
            self.cell(50, 10, transaction["Bank"], border=1, align="C")
            self.cell(
                40,
                10,
                transaction["Credit Amount"],
                border=1,
                align="C")
            self.cell(40, 10, transaction["Debit Amount"], border=1, align="C")
            self.ln()

    def watermark(self):
        self.set_font("Arial", style="B", size=100)
        self.set_text_color(240, 240, 240)  # Light gray as pseudo-transparency
        self.rotate(45, x=self.w / 1.5, y=self.h / 1.5)  # Rotate text
        self.text(
            x=self.w / 4,
            y=self.h / 2,
            txt="TransMatch")  # Add watermark text
        self.rotate(0)  # Reset rotation
        self.set_text_color(0, 0, 0)  # Reset text color


# Dummy data for demonstration
customer_name = "MR/ENCIK YAP CHEIN PHANG"
transactions_by_description = {
    "TJJ BEAUTY AC(Tele)": [
        {"Transaction Date": "30-September-2024", "Bank": "MAYBANK", "Credit Amount": "RM +7000", "Debit Amount": ""},
        {"Transaction Date": "09-October-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -5000"},
        {"Transaction Date": "18-October-2024", "Bank": "MAYBANK", "Credit Amount": "RM +1500", "Debit Amount": ""},
        {"Transaction Date": "01-November-2024", "Bank": "MAYBANK", "Credit Amount": "RM +3000", "Debit Amount": ""},
    ],
    "STYLE CITY TR(Tele)": [
        {"Transaction Date": "30-November-2024", "Bank": "MAYBANK", "Credit Amount": "RM +4000", "Debit Amount": ""},
        {"Transaction Date": "06-December-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1500"},
        {"Transaction Date": "07-December-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1000"},
    ],
    "CHIA YEE TING(Tele)": [
        {"Transaction Date": "25-October-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1500"},
        {"Transaction Date": "25-October-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -1500"},
        {"Transaction Date": "01-November-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -3000"},
        {"Transaction Date": "08-November-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2500"},
    ],
    "SOM TUM TRADING(Tele)": [
        {"Transaction Date": "01-November-2024", "Bank": "MAYBANK", "Credit Amount": "RM +5000", "Debit Amount": ""},
        {"Transaction Date": "08-November-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2000"},
        {"Transaction Date": "15-November-2024", "Bank": "MAYBANK", "Credit Amount": "RM +4000", "Debit Amount": ""},
        {"Transaction Date": "22-November-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2500"},
        {"Transaction Date": "29-November-2024", "Bank": "MAYBANK", "Credit Amount": "", "Debit Amount": "RM -2000"},
    ]
}
agent_name = "Max"
agent_login_id = "A0001"

# Generate PDF
pdf = PDFReport()
pdf.agent_name = agent_name
pdf.agent_login_id = agent_login_id
pdf.add_customer_header(customer_name)

for description, transactions in transactions_by_description.items():
    pdf.add_transaction_section(description, transactions)

pdf.output(
    "D:\\CHIANWEILON\\Software_Dev\\TransMatch\\Demo\\Customer_Transactions_Report.pdf")
print("PDF generated successfully.")
