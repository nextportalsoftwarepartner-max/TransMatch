# flake8: noqa: E501

import tkinter as tk
from tkinter import ttk
import phonenumbers
import pycountry


class CountryCodePhoneEntry(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        # Rebuild map with distinct codes only
        self.country_map = self._build_country_code_map()  # {'+60': '+60', '+65': '+65', ...}
        self.country_options = list(self.country_map.keys())

        # ✅ Set default to '+60'
        self.country_code_var = tk.StringVar(value="+60")
        self.phone_number_var = tk.StringVar()

        # Country code dropdown
        self.country_dropdown = ttk.Combobox(
            self,
            values=self.country_options,
            textvariable=self.country_code_var,
            width=5,
            state="readonly"
        )
        self.country_dropdown.grid(row=0, column=0, padx=(0, 5))

        # Phone number entry
        self.phone_entry = ttk.Entry(self, textvariable=self.phone_number_var, width=20)
        self.phone_entry.grid(row=0, column=1)

        # Validate numeric input
        vcmd = (self.register(self._validate_numeric), '%P')
        self.phone_entry.config(validate="key", validatecommand=vcmd)

    def _build_country_code_map(self):
        code_map = {}
        seen = set()
        for country in pycountry.countries:
            try:
                code = phonenumbers.country_code_for_region(country.alpha_2)
                if code and code not in seen:
                    label = f"+{code}"
                    code_map[label] = label
                    seen.add(code)
            except:
                continue
        return dict(sorted(code_map.items(), key=lambda x: int(x[1].replace('+', ''))))

    def _validate_numeric(self, value):
        return value == "" or value.isdigit()

    def get_full_number(self):
        code = self.country_map.get(self.country_code_var.get(), "")
        number = self.phone_number_var.get().strip()

        # If number already starts with code, return as is
        if number.startswith(code):
            return number

        # If number already starts with '+', assume user typed full number
        if number.startswith('+'):
            return number

        return f"{code}{number}"

    def set_value(self, full_number):
        full_number = str(full_number).strip()

        # Ensure it starts with '+'
        if not full_number.startswith("+"):
            full_number = "+" + full_number

        for label in self.country_map.keys():
            if full_number.startswith(label):
                self.country_code_var.set(label)
                self.phone_number_var.set(full_number[len(label):])
                return

        # Fallback: if no match, just put whole number
        self.phone_number_var.set(full_number)
