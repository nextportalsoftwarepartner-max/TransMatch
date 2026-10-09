"use client";

import { RadioGroup, TextField } from "./ui";

export type DateType = "transaction" | "entry";

interface DateRangeFilterProps {
  dateType: DateType;
  dateFrom: string;
  dateTo: string;
  onChange: (patch: { dateType?: DateType; dateFrom?: string; dateTo?: string }) => void;
}

const LABELS: Record<DateType, string> = { transaction: "Transaction Date", entry: "Data Entry Date" };

/** "Filter by" transaction date or data entry date, with a from/to range. */
export function DateRangeFilter({ dateType, dateFrom, dateTo, onChange }: DateRangeFilterProps) {
  return (
    <>
      <div>
        <p className="mb-1 text-xs font-semibold text-slate-600">Filter by</p>
        <div className="py-1.5">
          <RadioGroup
            label="Filter by"
            value={LABELS[dateType]}
            options={[LABELS.transaction, LABELS.entry] as const}
            onChange={(label) => onChange({ dateType: label === LABELS.entry ? "entry" : "transaction" })}
          />
        </div>
      </div>
      <TextField label={`${LABELS[dateType]} From`} type="date" value={dateFrom} onChange={(value) => onChange({ dateFrom: value })} />
      <TextField label={`${LABELS[dateType]} To`} type="date" value={dateTo} onChange={(value) => onChange({ dateTo: value })} />
    </>
  );
}

interface MatchTextFilterProps {
  label: string;
  value: string;
  match: "Equal" | "Contain";
  onChange: (patch: { value?: string; match?: "Equal" | "Contain" }) => void;
}

/** Text filter with an Equal / Contain choice. */
export function MatchTextFilter({ label, value, match, onChange }: MatchTextFilterProps) {
  return (
    <div>
      <TextField label={label} value={value} onChange={(v) => onChange({ value: v })} />
      <div className="mt-1">
        <RadioGroup label={`${label} match`} value={match} options={["Equal", "Contain"] as const} onChange={(m) => onChange({ match: m })} />
      </div>
    </div>
  );
}
