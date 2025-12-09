import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageSequence
import os


class LoadingPopupClass:
    def __init__(self, parent, message="Loading... Please wait."):
        self.top = tk.Toplevel(parent)
        self.top.attributes('-toolwindow', True)  # Removes minimize/maximize buttons
        self.top.geometry("180x180")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)

        # === Load and display the GIF ===
        gif_path = os.path.join(os.path.dirname(__file__), "LoadingIcon.gif")
        self.img = Image.open(gif_path)
        self.frames = [ImageTk.PhotoImage(f.copy().convert('RGBA')) for f in ImageSequence.Iterator(self.img)]
        self.gif_label = tk.Label(self.top, image=self.frames[0])
        self.gif_label.pack(pady=(15, 5))

        # Start animation
        self.frame_index = 0
        self.animate()

        # Display text below GIF
        ttk.Label(self.top, text=message, font=("Segoe UI", 10)).pack()

        # Force geometry update
        self.top.update_idletasks()

        # Center the popup
        w = self.top.winfo_width()
        h = self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f"{w}x{h}+{x}+{y}")

    def animate(self):
        self.gif_label.configure(image=self.frames[self.frame_index])
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self._after_id = self.top.after(100, self.animate)

    def close(self):
        self.top.after_cancel(self._after_id)
        self.top.grab_release()
        self.top.destroy()
