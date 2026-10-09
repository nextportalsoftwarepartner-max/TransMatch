"use client";

import {
  useEffect,
  useId,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

// ---- Buttons ----

const BUTTON_VARIANTS = {
  primary: "bg-accent text-white hover:bg-accent-hover",
  secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
  danger: "bg-red-600 text-white hover:bg-red-700",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof BUTTON_VARIANTS;
}

export function Button({ variant = "primary", className = "", type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center rounded-md px-3.5 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

// ---- Form fields ----

const CONTROL =
  "w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:bg-slate-100 disabled:text-slate-500 read-only:bg-slate-100";

interface FieldProps {
  label: string;
  required?: boolean;
  className?: string;
  children: (id: string) => ReactNode;
}

/** Label + control, wired together by id. */
export function Field({ label, required, className = "", children }: FieldProps) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-xs font-semibold text-slate-600">
        {label}
        {required && <span className="text-red-600"> *</span>}
      </label>
      {children(id)}
    </div>
  );
}

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "className"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
  /** Upper-cases what is typed. */
  uppercase?: boolean;
}

export function TextField({ label, value, onChange, className, required, uppercase, ...props }: TextFieldProps) {
  return (
    <Field label={label} required={required} className={className}>
      {(id) => (
        <input
          id={id}
          className={CONTROL}
          value={value}
          required={required}
          onChange={(e) => onChange(uppercase ? e.target.value.toUpperCase() : e.target.value)}
          {...props}
        />
      )}
    </Field>
  );
}

interface TextAreaFieldProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onChange" | "className"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function TextAreaField({ label, value, onChange, className, required, ...props }: TextAreaFieldProps) {
  return (
    <Field label={label} required={required} className={className}>
      {(id) => (
        <textarea id={id} className={CONTROL} value={value} required={required} onChange={(e) => onChange(e.target.value)} {...props} />
      )}
    </Field>
  );
}

export interface Option {
  value: string;
  label: string;
}

interface SelectFieldProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "onChange" | "className"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  /** Label of the empty choice; omit to offer no empty choice. */
  placeholder?: string;
  className?: string;
}

export function SelectField({ label, value, onChange, options, placeholder, className, required, ...props }: SelectFieldProps) {
  return (
    <Field label={label} required={required} className={className}>
      {(id) => (
        <select id={id} className={CONTROL} value={value} required={required} onChange={(e) => onChange(e.target.value)} {...props}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  );
}

interface RadioGroupProps<T extends string> {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: readonly T[];
}

export function RadioGroup<T extends string>({ label, value, onChange, options }: RadioGroupProps<T>) {
  const name = useId();
  return (
    <fieldset className="flex items-center gap-3 text-sm">
      <legend className="sr-only">{label}</legend>
      {options.map((option) => (
        <label key={option} className="flex items-center gap-1 text-slate-700">
          <input type="radio" name={name} checked={value === option} onChange={() => onChange(option)} />
          {option}
        </label>
      ))}
    </fieldset>
  );
}

// ---- Layout ----

export function Card({ title, actions, children, className = "" }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-4 border-b border-slate-200 px-4 py-2.5">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function PageHeader({ title, section }: { title: string; section: string }) {
  return (
    <div className="mb-4">
      <p className="text-xs text-slate-500">
        Home &rsaquo; {section} &rsaquo; {title}
      </p>
      <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
    </div>
  );
}

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Tailwind max-width class */
  width?: string;
}

export function Modal({ title, onClose, children, width = "max-w-3xl" }: ModalProps) {
  const titleId = useId();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 sm:p-10" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`w-full ${width} rounded-lg bg-white shadow-xl`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 id={titleId} className="text-base font-semibold text-slate-900">
            {title}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded p-1 text-slate-500 hover:bg-slate-100">
            ✕
          </button>
        </header>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
