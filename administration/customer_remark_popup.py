# flake8: noqa: E501

import tkinter as tk
from tkinter import ttk, messagebox
from db_manager import execute_query, commit, rollback
import logger


class RemarkPopup:
    def __init__(self, parent, cust_id, current_remark, refresh_callback):
        self.cust_id = cust_id
        self.refresh_callback = refresh_callback
        self.popup = tk.Toplevel(parent)
        self.popup.title("Edit Customer Remark")
        self.popup.geometry("450x300")
        self.popup.grab_set()
        self.popup.transient(parent)
        self.popup.update_idletasks()  # Force geometry calculation
        w = self.popup.winfo_width()
        h = self.popup.winfo_height()
        x = (self.popup.winfo_screenwidth() // 2) - (w // 2)
        y = (self.popup.winfo_screenheight() // 2) - (h // 2)
        self.popup.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(self.popup, text="Customer Remark:").pack(pady=5)
        self.text = tk.Text(self.popup, height=15, width=60)
        self.text.pack(padx=10, pady=5)

        self.text.insert("1.0", (current_remark or "").replace("\\n", "\n"))

        ttk.Button(self.popup, text="💾 Save", command=self.save_remark).pack(pady=10)

    def save_remark(self):
        raw_text = self.text.get("1.0", tk.END).strip()
        formatted_text = raw_text.replace("\n", "\\n")

        sql = "UPDATE TM_MST_CUSTOMER SET VCH_REMARK = %s WHERE NUM_CUST_ID = %s"
        conn = None
        try:
            conn = execute_query(sql, (formatted_text, self.cust_id))
            if conn:
                commit(conn)
                messagebox.showinfo("Saved", "Remark updated successfully.")
                self.popup.destroy()
                self.refresh_callback()
        except Exception as e:
            if conn:
                rollback(conn)
            logger.logger.error(f"[customer_remark_popup] : Failed to save remark: {str(e)}")
            messagebox.showerror("Error", f"Failed to update remark.\n\n{e}")
