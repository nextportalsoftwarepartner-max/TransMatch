import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

class TransMatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TransMatch System - User Group Configuration")
        self.root.geometry("1920x1080")

        # Create Notebook for tabs
        self.create_tabs()

    def create_tabs(self):
        style = ttk.Style()
        style.configure('TNotebook.Tab', padding=(20, 10), font=("Arial", 12, "bold"))

        notebook = ttk.Notebook(self.root, style='TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True)

        # Administration Tab
        admin_tab = ttk.Frame(notebook)
        notebook.add(admin_tab, text="Administration")
        self.create_admin_tab(admin_tab)

    def create_admin_tab(self, parent):
        menu_frame = tk.Frame(parent, bg="white", relief=tk.RAISED, borderwidth=2)
        menu_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        ttk.Button(menu_frame, text="User Group Configuration", command=self.create_user_group_menu).pack(pady=20)

    def create_user_group_menu(self):
        user_group_window = tk.Toplevel(self.root)
        user_group_window.title("User Group Configuration")
        user_group_window.geometry("1200x800")
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
        input_frame = tk.LabelFrame(window, text="User Group Details", font=("Helvetica", 12, "bold"), bg="#ffffff", fg="#333", bd=2, relief=tk.GROOVE)
        input_frame.pack(pady=10, fill=tk.X, padx=20)

        def create_label_input(row, col, text, widget):
            tk.Label(input_frame, text=text, bg="#ffffff", font=("Helvetica", 10)).grid(row=row, column=col, padx=10, pady=5, sticky="w")
            widget.grid(row=row, column=col + 1, padx=10, pady=5, sticky="w")

        self.user_group_name_var = tk.StringVar()
        create_label_input(0, 0, "User Group Name:", ttk.Entry(input_frame, textvariable=self.user_group_name_var))

        self.user_group_desc_var = tk.StringVar()
        create_label_input(1, 0, "User Group Description:", ttk.Entry(input_frame, textvariable=self.user_group_desc_var))

        self.effective_date_from_var = DateEntry(input_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(2, 0, "Effective Date From:", self.effective_date_from_var)

        self.effective_date_to_var = DateEntry(input_frame, width=15, background='darkblue', foreground='white', borderwidth=2)
        create_label_input(3, 0, "Effective Date To:", self.effective_date_to_var)

        self.active_flag_var = tk.StringVar(value="YES")
        create_label_input(4, 0, "Active Flag:", ttk.Combobox(input_frame, textvariable=self.active_flag_var, values=["YES", "NO"], state="readonly"))

        # Buttons
        button_frame = tk.Frame(input_frame, bg="#ffffff")
        button_frame.grid(row=5, columnspan=4, pady=10)

        ttk.Button(button_frame, text="Add", command=self.add_user_group).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Update", command=self.update_user_group).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset", command=self.reset_user_group_fields).pack(side=tk.LEFT, padx=10)

    def create_user_group_results_section(self, window):
        results_frame = tk.Frame(window, bg="#ffffff")
        results_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        columns = ["User Group Name", "Description", "Effective Date From", "Effective Date To", "Active Flag"]
        self.results_table = ttk.Treeview(results_frame, columns=columns, show="headings")
        self.results_table.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            self.results_table.heading(col, text=col, anchor="w")
            self.results_table.column(col, anchor="w", width=200)

        # Scrollbars
        y_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_table.yview)
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


if __name__ == "__main__":
    root = tk.Tk()
    app = TransMatchApp(root)
    root.mainloop()
