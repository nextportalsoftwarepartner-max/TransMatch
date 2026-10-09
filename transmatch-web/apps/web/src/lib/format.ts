const TIME_ZONE = "Asia/Kuala_Lumpur";

/** ISO timestamp -> "YYYY-MM-DD HH:MM:SS" in Malaysia time. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("sv-SE", { timeZone: TIME_ZONE });
}

export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Today's date in Malaysia as YYYY-MM-DD. */
export function today(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: TIME_ZONE });
}

/** Parses user-typed money ("1,234.50"); null when it is not a number. */
export function parseMoney(text: string): number | null {
  const cleaned = text.replaceAll(",", "").trim();
  if (cleaned === "") return 0;
  return /^-?\d+(\.\d{1,2})?$/.test(cleaned) ? Number(cleaned) : null;
}
