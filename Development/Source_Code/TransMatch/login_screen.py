# flake8: noqa: E501

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from db_manager import executionWithRs_query, verify_password
import os
import sys
import TransMatch_main
import logger
import dependency_manager

logger.logger.info("[login_screen] : Login Landing Page initiation")


class LoginScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Login - TransMatch System")
        self.root.geometry("330x380")
        self.root.configure(bg="#000000")
        self.root.overrideredirect(True)  # ✅ Remove OS window border/frame

        # === OUTER FRAME ===
        self.outer_frame = tk.Frame(self.root, bg="#00042E", bd=2)
        self.outer_frame.pack(expand=True, fill="both")

        # === HEADER ===
        header_frame = tk.Frame(self.outer_frame, bg="#00042E")
        header_frame.pack(fill="x", pady=(2, 0))

        # Close button
        close_btn = tk.Label(header_frame, text="✖", font=("Segoe UI", 12, "bold"),
                             fg="red", bg="#00042E", cursor="hand2")
        close_btn.pack(side="right", padx=10)
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        # === MAIN CONTENT FRAME ===
        content_frame = tk.Frame(
            self.outer_frame, bg="#00042E", padx=20, pady=20)
        # content_frame.pack(expand=True, padx=15, pady=(0, 15))
        content_frame.pack(expand=True)

        # === Logo ===
        logo_path = os.path.join(os.path.dirname(
            __file__), "TransMatch_Logo.png")
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img = img.resize((200, 80), resample=getattr(
                Image, 'LANCZOS', Image.BICUBIC)) # pyright: ignore[reportAttributeAccessIssue]
            self.logo_img = ImageTk.PhotoImage(img)
            tk.Label(content_frame, image=self.logo_img,
                     bg="#00042E").pack(pady=(5, 20))

        # Title
        tk.Label(content_frame, text="Welcome to TransMatch", font=("Segoe UI", 14, "bold"),
                 bg="#00042E", fg="white").pack(pady=(0, 15))

        # Form Frame
        form_frame = tk.Frame(content_frame, bg="#00042E")
        form_frame.pack()

        # label_font = ("Segoe UI", 11)
        # entry_width = 30

        # # Username
        # tk.Label(form_frame, text="Username:", font=label_font, bg="#00042E", fg="white").grid(row=0, column=0, sticky="e", pady=5)
        # self.username_var = tk.StringVar()
        # self.username_entry = ttk.Entry(form_frame, textvariable=self.username_var, width=entry_width)
        # self.username_entry.grid(row=0, column=1, pady=5)

        # # Password
        # tk.Label(form_frame, text="Password:", font=label_font, bg="#00042E", fg="white").grid(row=1, column=0, sticky="e", pady=5)
        # self.password_var = tk.StringVar()
        # self.password_entry = ttk.Entry(form_frame, textvariable=self.password_var, show="*", width=entry_width)
        # self.password_entry.grid(row=1, column=1, pady=5)

        # Username field with placeholder
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(
            form_frame, textvariable=self.username_var, width=40, font=("Segoe UI", 10))
        self.username_entry.insert(0, "Enter your user name")
        self.username_entry.config(foreground="gray")
        self.username_entry.grid(
            row=0, column=0, columnspan=2, pady=10, ipady=2)

        # Password field with placeholder
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            form_frame, textvariable=self.password_var, width=40, font=("Segoe UI", 10))
        self.password_entry.insert(0, "Enter your password")
        self.password_entry.config(
            foreground="gray", show="")  # Show plain initially
        self.password_entry.grid(
            row=1, column=0, columnspan=2, pady=5, ipady=2)

        # === Placeholder Behavior ===

        def on_username_focus_in(event):
            if self.username_entry.get() == "Enter your user name":
                self.username_entry.delete(0, tk.END)
                self.username_entry.config(foreground="black")

        def on_username_focus_out(event):
            if not self.username_entry.get():
                self.username_entry.insert(0, "Enter your user name")
                self.username_entry.config(foreground="gray")

        def on_password_focus_in(event):
            if self.password_entry.get() == "Enter your password":
                self.password_entry.delete(0, tk.END)
                self.password_entry.config(show="*", foreground="black")

        def on_password_focus_out(event):
            if not self.password_entry.get():
                self.password_entry.insert(0, "Enter your password")
                self.password_entry.config(show="", foreground="gray")

        self.username_entry.bind("<FocusIn>", on_username_focus_in)
        self.username_entry.bind("<FocusOut>", on_username_focus_out)
        self.password_entry.bind("<FocusIn>", on_password_focus_in)
        self.password_entry.bind("<FocusOut>", on_password_focus_out)

        # === Login Button Style ===
        style = ttk.Style()
        style.configure("Custom.TButton",
                        font=("Segoe UI", 10, "bold"),
                        foreground="#0004F5",
                        background="#ADD8E6")
        style.map("Custom.TButton",
                  background=[("active", "#253AF3")])  # Hover color

        # === Login Button ===
        btn_frame = tk.Frame(content_frame, bg="black")
        btn_frame.pack(pady=20)

        login_btn = ttk.Button(btn_frame, text="Login",command=self.authenticate, style="Custom.TButton")
        login_btn.config(width=40)
        login_btn.pack(ipady=84)

        # Bind Enter key
        self.root.bind('<Return>', lambda event: self.authenticate())

        # Set focus on username field
        # self.username_entry.focus()

        # === Center the window ===
        self.center_window()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def authenticate(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        # print(hash_password(password))

        if not username or not password:
            messagebox.showerror(
                "Error", "Please enter both username and password.")
            return

        query = """
            SELECT VCH_PASSWORD, NUM_USER_ID, VCH_LOGIN_ID, VCH_USER_NAME FROM TM_MST_USER
            WHERE VCH_LOGIN_ID = %s AND CHR_ACTIVE_IND = 'Y'
        """
        result = executionWithRs_query(query, (username,))
        if result and verify_password(result[0][0], password):
            logger.logger.info(f"[login_screen] : Username and Password authenticated, Welcome {username}")

            # Create dictionary to store global parameter
            global_info = {
                "gb_user_id": result[0][1],
                "gb_login_id": result[0][2],
                "gb_user_name": result[0][3]
            }
            
            self.root.destroy()
            self.launch_main_app(global_info)
        else:
            messagebox.showerror(
                "Login Failed", "Invalid username or password.")
            logger.logger.info(
                f"[login_screen] : Failed in authentication, either Username ({username}) and/or Password ({password}) ")

    def launch_main_app(self, global_info):
        new_root = tk.Tk()
        TransMatch_main.TransMatchApp(new_root, global_info)
        new_root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    LoginScreen(root)
    root.mainloop()
