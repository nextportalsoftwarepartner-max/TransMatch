"use client";

import { useMemo, useState, type ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  /** Cell content; defaults to the row property named by `key`. */
  render?: (row: T) => ReactNode;
  /** Value used for sorting; defaults to the row property named by `key`. */
  sortValue?: (row: T) => string | number | boolean | null | undefined;
  align?: "left" | "center" | "right";
  /** Tailwind classes for the cell, e.g. a width or "whitespace-nowrap". */
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  /** Highlighted row (single selection by clicking). */
  selectedKey?: string | null;
  onSelect?: (row: T) => void;
  onRowDoubleClick?: (row: T) => void;
  /** Checkbox selection of several rows. */
  checkedKeys?: Set<string>;
  onCheckedChange?: (keys: Set<string>) => void;
  rowClassName?: (row: T) => string;
  emptyText?: string;
  /** Tailwind max-height class of the scroll area. */
  maxHeight?: string;
  countLabel?: string;
}

const ALIGN = { left: "text-left", center: "text-center", right: "text-right" } as const;

function compare(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === null || a === undefined || a === "") return 1;
  if (b === null || b === undefined || b === "") return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

/** Sortable table with a sticky header, optional row selection and a row count. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  selectedKey,
  onSelect,
  onRowDoubleClick,
  checkedKeys,
  onCheckedChange,
  rowClassName,
  emptyText = "No records found.",
  maxHeight = "max-h-[28rem]",
  countLabel = "Total Records",
}: DataTableProps<T>) {
  const [sort, setSort] = useState<{ key: string; descending: boolean } | null>(null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const column = columns.find((c) => c.key === sort.key);
    if (!column) return rows;
    const value = column.sortValue ?? ((row: T) => (row as Record<string, unknown>)[column.key]);
    const ordered = [...rows].sort((a, b) => compare(value(a), value(b)));
    return sort.descending ? ordered.reverse() : ordered;
  }, [rows, columns, sort]);

  const checkable = checkedKeys !== undefined && onCheckedChange !== undefined;
  const allChecked = checkable && rows.length > 0 && rows.every((row) => checkedKeys.has(rowKey(row)));

  const toggleAll = () => onCheckedChange?.(allChecked ? new Set() : new Set(rows.map(rowKey)));
  const toggleOne = (key: string) => {
    const next = new Set(checkedKeys);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onCheckedChange?.(next);
  };

  return (
    <div>
      <div className={`overflow-auto rounded-md border border-slate-200 ${maxHeight}`}>
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
            <tr>
              {checkable && (
                <th className="w-10 px-2 py-2">
                  <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="Select all rows" />
                </th>
              )}
              {columns.map((column) => {
                const active = sort?.key === column.key;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={active ? (sort.descending ? "descending" : "ascending") : undefined}
                    className={`px-3 py-2 font-semibold ${ALIGN[column.align ?? "left"]}`}
                  >
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 uppercase hover:text-slate-900"
                      onClick={() => setSort({ key: column.key, descending: active ? !sort.descending : false })}
                    >
                      {column.header}
                      <span aria-hidden="true" className="text-[10px]">
                        {active ? (sort.descending ? "▼" : "▲") : ""}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 && (
              <tr>
                <td colSpan={columns.length + (checkable ? 1 : 0)} className="px-3 py-8 text-center text-slate-500">
                  {emptyText}
                </td>
              </tr>
            )}
            {sorted.map((row) => {
              const key = rowKey(row);
              const selected = selectedKey === key;
              return (
                <tr
                  key={key}
                  onClick={onSelect ? () => onSelect(row) : undefined}
                  onDoubleClick={onRowDoubleClick ? () => onRowDoubleClick(row) : undefined}
                  aria-selected={onSelect ? selected : undefined}
                  className={`border-t border-slate-100 ${selected ? "bg-blue-100" : "odd:bg-white even:bg-slate-50"} ${
                    onSelect || onRowDoubleClick ? "cursor-pointer hover:bg-blue-50" : ""
                  } ${rowClassName?.(row) ?? ""}`}
                >
                  {checkable && (
                    <td className="px-2 py-1.5 text-center" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={checkedKeys.has(key)} onChange={() => toggleOne(key)} aria-label="Select row" />
                    </td>
                  )}
                  {columns.map((column) => (
                    <td key={column.key} className={`px-3 py-1.5 ${ALIGN[column.align ?? "left"]} ${column.className ?? ""}`}>
                      {column.render ? column.render(row) : String((row as Record<string, unknown>)[column.key] ?? "")}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-1 text-right text-xs text-slate-500">
        {countLabel}: {rows.length}
        {checkable ? ` · Selected: ${rows.filter((row) => checkedKeys.has(rowKey(row))).length}` : ""}
      </p>
    </div>
  );
}

/** Created/modified columns shared by the administration tables. */
export function auditColumns<T extends { createdAt: string; createdBy: string | null; modifiedAt: string | null; modifiedBy: string | null }>(
  formatDateTime: (iso: string | null) => string,
): Column<T>[] {
  return [
    { key: "createdAt", header: "Created At", render: (r) => formatDateTime(r.createdAt), className: "whitespace-nowrap" },
    { key: "createdBy", header: "Created By" },
    { key: "modifiedAt", header: "Updated At", render: (r) => formatDateTime(r.modifiedAt), className: "whitespace-nowrap" },
    { key: "modifiedBy", header: "Updated By" },
  ];
}
