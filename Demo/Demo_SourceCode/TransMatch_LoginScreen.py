import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class LoginScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Login - TransMatch Software")
        self.root.geometry("1920x1080")  # Set window size to 1200x800

        # Set background image
        self.set_background()

        # Create login box frame
        self.login_frame = tk.Frame(self.root, bg="white", width=400, height=300, relief=tk.RAISED, borderwidth=2)
        self.login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Add logo
        self.add_logo()

        # Add fields
        self.add_fields()

    def set_background(self):
        # Load and set the background image
        bg_image = Image.open("D:\\CHIANWEILON\\Software_Dev\\TransMatch\\gradient_background.png")
        bg_image = bg_image.resize((1920, 1080), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(bg_image)

        bg_label = tk.Label(self.root, image=self.bg_photo)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    def add_logo(self):
        # Load and display the provided image
        img = Image.open("D:\\CHIANWEILON\\Software_Dev\\TransMatch\\TransMatch.png")
        img = img.resize((250, 99), Image.Resampling.LANCZOS)  # Resize to fit better in login frame
        logo = ImageTk.PhotoImage(img)

        logo_label = tk.Label(self.login_frame, image=logo, bg="white")
        logo_label.image = logo  # Keep a reference to avoid garbage collection
        logo_label.pack(pady=10)

    def add_fields(self):
        # Create grid for field arrangement
        fields_frame = tk.Frame(self.login_frame, bg="white")
        fields_frame.pack(pady=20)

        # Login ID field
        tk.Label(fields_frame, text="Login ID", bg="white", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
        self.login_id_entry = ttk.Entry(fields_frame, font=("Arial", 12))
        self.login_id_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)

        # Password field
        tk.Label(fields_frame, text="Password", bg="white", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.password_entry = ttk.Entry(fields_frame, font=("Arial", 12), show="*")
        self.password_entry.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)

        # Login button
        login_button = ttk.Button(fields_frame, text="Login", command=self.login_action)
        login_button.grid(row=2, column=0, columnspan=2, pady=10)

        # Reset Password button
        reset_button = ttk.Button(fields_frame, text="Reset Password", command=self.reset_password)
        reset_button.grid(row=3, column=0, columnspan=2, pady=5)

    def login_action(self):
        # Handle login action here
        print("Login button clicked")

    def reset_password(self):
        # Handle reset password action here
        print("Reset Password button clicked")

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginScreen(root)
    root.mainloop()
