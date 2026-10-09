"use client";

import { useQuery } from "@tanstack/react-query";
import { ENQUIRY_CONDITIONS, type EnquiryResultDto, type EnquiryRowDto, type OptionDto, type WatchStatus } from "@transmatch/shared";
import { useEffect, useState } from "react";
import { DataTable, type Column } from "@/components/data-table";
import { useFeedback } from "@/components/feedback";
import { DateRangeFilter, MatchTextFilter, type DateType } from "@/components/transaction-filters";
import { Button, Card, Modal, PageHeader, SelectField, TextField } from "@/components/ui";
import { api, download } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import { useAction } from "@/lib/use-action";

const EMPTY_FILTER = {
  customerCode: "",
  customerName: "",
  customerNameMatch: "Equal" as "Equal" | "Contain",
  description: "",
  descriptionMatch: "Equal" as "Equal" | "Contain",
  bankName: "",
  fileName: "",
  condition: "All" as (typeof ENQUIRY_CONDITIONS)[number],
  printed: "All",
  agentUserId: "",
  dateType: "transaction" as DateType,
  dateFrom: "",
  dateTo: "",
};

// Row colours, as in the legend
const STATUS_CLASS: Record<WatchStatus, string> = {
  BLACKLISTED: "font-semibold text-red-600",
  BLACKLISTED_PARTIAL: "text-blue-700",
  SUSPICIOUS: "text-purple-700",
  NONE: "",
};

const columns: Column<EnquiryRowDto>[] = [
  { key: "customerCode", header: "Customer Code", className: "whitespace-nowrap" },
  { key: "customerName", header: "Customer Name" },
  { key: "description", header: "Transaction Description" },
  { key: "targetName", header: "Target Audience" },
  { key: "bankName", header: "Bank Name" },
  { key: "creditAmount", header: "Credit Amount", align: "right", render: (r) => formatMoney(r.creditAmount) },
  { key: "debitAmount", header: "Debit Amount", align: "right", render: (r) => formatMoney(r.debitAmount) },
  { key: "transactionDate", header: "Transaction Date", className: "whitespace-nowrap" },
  { key: "entryDate", header: "Data Entry Date", render: (r) => formatDateTime(r.entryDate), className: "whitespace-nowrap" },
  { key: "printed", header: "Printed Status", align: "center", render: (r) => (r.printed ? "Y" : "N") },
  { key: "agentName", header: "Agent Name" },
  { key: "fileName", header: "File Name" },
];

/** A set of transactions the user has picked for the report. */
interface Summary {
  label: string;
  rows: EnquiryRowDto[];
}

const summaryColumns: Column<Summary>[] = [
  { key: "label", header: "Summary Label" },
  { key: "count", header: "Total Transactions", align: "center", render: (s) => s.rows.length, sortValue: (s) => s.rows.length },
  {
    key: "amount",
    header: "Total Amount",
    align: "right",
    // Credits add, debits subtract
    render: (s) => formatMoney(totalAmount(s.rows)),
    sortValue: (s) => totalAmount(s.rows),
  },
  { key: "customers", header: "Total Customers", align: "center", render: (s) => new Set(s.rows.map((r) => r.customerCode)).size },
  { key: "banks", header: "Total Banks", align: "center", render: (s) => new Set(s.rows.map((r) => r.bankName)).size },
  { key: "range", header: "Transaction Date Range", align: "center", render: (s) => dateRange(s.rows) },
];

const totalAmount = (rows: EnquiryRowDto[]) => rows.reduce((sum, r) => sum + r.creditAmount - r.debitAmount, 0);

function dateRange(rows: EnquiryRowDto[]): string {
  const dates = rows.map((r) => r.transactionDate).sort();
  return dates.length > 0 ? `${dates[0]} until ${dates[dates.length - 1]}` : "-";
}

export default function EnquiryPage() {
  const feedback = useFeedback();
  const { run, busy } = useAction();

  const [filterInput, setFilterInput] = useState(EMPTY_FILTER);
  const [filter, setFilter] = useState<typeof EMPTY_FILTER | null>(null);
  // Counts searches, so pressing Search again with the same criteria reloads the data
  const [searchRun, setSearchRun] = useState(0);
  const set = (patch: Partial<typeof EMPTY_FILTER>) => setFilterInput((f) => ({ ...f, ...patch }));

  // Rows shown in the results table; taken out when they are added to a summary
  const [rows, setRows] = useState<EnquiryRowDto[]>([]);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [selectedSummary, setSelectedSummary] = useState<string | null>(null);
  const [nextNumber, setNextNumber] = useState(1);
  // Label kept while a summary is being edited, so it is put back under the same name
  const [editingLabel, setEditingLabel] = useState<string | null>(null);
  const [exportedText, setExportedText] = useState<string | null>(null);

  const banks = useQuery({ queryKey: ["bank-options"], queryFn: () => api<OptionDto[]>("/transactions/lookups/banks") });
  const files = useQuery({ queryKey: ["file-names"], queryFn: () => api<string[]>("/transactions/lookups/file-names") });
  const agents = useQuery({ queryKey: ["agent-options"], queryFn: () => api<OptionDto[]>("/transactions/lookups/agents") });
  const search = useQuery({
    queryKey: ["enquiry", filter, searchRun],
    queryFn: () => api<EnquiryResultDto>("/reports/enquiry", { query: filter ?? {} }),
    enabled: filter !== null,
    staleTime: 0,
    gcTime: 0,
  });

  // A finished search fills the results table with every row ticked
  useEffect(() => {
    if (!search.data) return;
    setRows(search.data.rows);
    setChecked(new Set(search.data.rows.map((r) => r.transactionId)));
    setEditingLabel(null);
  }, [search.data]);

  const addSummary = () => {
    const picked = rows.filter((r) => checked.has(r.transactionId));
    if (picked.length === 0) {
      feedback.error("No records selected.");
      return;
    }
    const label = editingLabel ?? `Transaction Summary #${nextNumber}`;
    if (!editingLabel) setNextNumber((n) => n + 1);
    setSummaries((current) => [...current, { label, rows: picked }]);
    setEditingLabel(null);
    setRows([]);
    setChecked(new Set());
  };

  // Editing puts the summary's rows back into the results table
  const editSummary = () => {
    const summary = summaries.find((s) => s.label === selectedSummary);
    if (!summary) return;
    setSummaries((current) => current.filter((s) => s.label !== summary.label));
    setSelectedSummary(null);
    setEditingLabel(summary.label);
    setRows(summary.rows);
    setChecked(new Set(summary.rows.map((r) => r.transactionId)));
  };

  const deleteSummary = () => {
    setSummaries((current) => current.filter((s) => s.label !== selectedSummary));
    setSelectedSummary(null);
  };

  const resetSummaries = async () => {
    const confirmed = await feedback.confirm({ title: "Reset", message: "Are you sure you want to clear all summary data?", confirmLabel: "Clear" });
    if (!confirmed) return;
    setSummaries([]);
    setSelectedSummary(null);
    setNextNumber(1);
  };

  const summaryIds = () => [...new Set(summaries.flatMap((s) => s.rows.map((r) => r.transactionId)))];

  const exportText = () =>
    run(async () => {
      const result = await api<{ text: string }>("/reports/enquiry/export/text", { method: "POST", body: { transactionIds: summaryIds() } });
      setExportedText(result.text);
    });

  const exportExcel = () =>
    run(() => download("/reports/enquiry/export/excel", "Transaction_Export.xlsx", { method: "POST", body: { transactionIds: summaryIds() } }), {
      success: "Excel exported.",
    });

  return (
    <>
      <PageHeader title="Enquiry and Report Generation" section="Report / Enquiry" />
      <div className="space-y-4">
        <Card title="Filters">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setFilter({ ...filterInput });
              setSearchRun((n) => n + 1);
            }}
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <TextField label="Customer Code" value={filterInput.customerCode} onChange={(customerCode) => set({ customerCode })} />
              <MatchTextFilter
                label="Customer Name"
                value={filterInput.customerName}
                match={filterInput.customerNameMatch}
                onChange={(p) => set({ ...(p.value !== undefined && { customerName: p.value }), ...(p.match && { customerNameMatch: p.match }) })}
              />
              <MatchTextFilter
                label="Transaction Desc"
                value={filterInput.description}
                match={filterInput.descriptionMatch}
                onChange={(p) => set({ ...(p.value !== undefined && { description: p.value }), ...(p.match && { descriptionMatch: p.match }) })}
              />
              <SelectField
                label="Bank Name"
                value={filterInput.bankName}
                onChange={(bankName) => set({ bankName })}
                placeholder="All"
                options={(banks.data ?? []).map((b) => ({ value: b.label, label: b.label }))}
              />
              <SelectField
                label="File Name"
                value={filterInput.fileName}
                onChange={(fileName) => set({ fileName })}
                placeholder="All"
                options={(files.data ?? []).map((f) => ({ value: f, label: f }))}
              />
              <SelectField
                label="Condition"
                value={filterInput.condition}
                onChange={(condition) => set({ condition: condition as typeof filterInput.condition })}
                options={ENQUIRY_CONDITIONS.map((c) => ({ value: c, label: c }))}
              />
              <SelectField
                label="Printed Status"
                value={filterInput.printed}
                onChange={(printed) => set({ printed })}
                options={["All", "Yes", "No"].map((v) => ({ value: v, label: v }))}
              />
              <SelectField label="Agent Name" value={filterInput.agentUserId} onChange={(agentUserId) => set({ agentUserId })} placeholder="All" options={agents.data ?? []} />
              <DateRangeFilter dateType={filterInput.dateType} dateFrom={filterInput.dateFrom} dateTo={filterInput.dateTo} onChange={set} />
            </div>
            <div className="mt-3 flex gap-2">
              <Button type="submit" disabled={search.isFetching}>
                {search.isFetching ? "Searching… Please wait." : "Search"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setFilterInput(EMPTY_FILTER);
                  setRows([]);
                  setChecked(new Set());
                  setEditingLabel(null);
                }}
              >
                Clear
              </Button>
            </div>
          </form>
        </Card>

        <Card
          title="Search Results"
          actions={
            <div className="flex flex-wrap items-center gap-3 text-xs italic">
              <span className="text-red-600">● Blacklisted</span>
              <span className="text-blue-700">● Blacklisted (Partial Match)</span>
              <span className="text-purple-700">● Suspicious</span>
            </div>
          }
        >
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(r) => r.transactionId}
            checkedKeys={checked}
            onCheckedChange={setChecked}
            rowClassName={(r) => STATUS_CLASS[r.watchStatus]}
            emptyText={search.error?.message ?? (filter === null ? "Enter the criteria and press Search." : "No records found.")}
            maxHeight="max-h-96"
            countLabel="Total Rows"
          />
          {search.data?.truncated && (
            <p className="mt-1 text-xs text-amber-700">More than 10,000 rows matched; only the first 10,000 are shown. Narrow the criteria to see the rest.</p>
          )}
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <Button onClick={addSummary} disabled={rows.length === 0}>
              {editingLabel ? `Update ${editingLabel}` : "Add to Summary"}
            </Button>
            <Button variant="secondary" disabled={!selectedSummary} onClick={editSummary}>
              Edit Summary
            </Button>
            <Button variant="secondary" disabled={!selectedSummary} onClick={deleteSummary}>
              Delete Summary
            </Button>
            <Button variant="secondary" disabled={summaries.length === 0} onClick={resetSummaries}>
              Reset
            </Button>
          </div>
        </Card>

        <Card
          title="General Summary"
          actions={
            <>
              <Button variant="secondary" disabled={summaries.length === 0 || busy} onClick={exportExcel}>
                Export Excel
              </Button>
              <Button variant="secondary" disabled={summaries.length === 0 || busy} onClick={exportText}>
                Export Plain Text
              </Button>
            </>
          }
        >
          <DataTable
            columns={summaryColumns}
            rows={summaries}
            rowKey={(s) => s.label}
            selectedKey={selectedSummary}
            onSelect={(s) => setSelectedSummary(s.label)}
            emptyText="Tick the transactions you want and press Add to Summary."
            maxHeight="max-h-60"
            countLabel="Summaries"
          />
        </Card>
      </div>

      {exportedText !== null && (
        <Modal title="Exported Plain Text" onClose={() => setExportedText(null)} width="max-w-4xl">
          <textarea readOnly aria-label="Exported plain text" className="h-[28rem] w-full rounded-md border border-slate-300 p-3 font-mono text-sm" value={exportedText} />
          <div className="mt-3 flex justify-end gap-2">
            <Button
              onClick={() =>
                navigator.clipboard.writeText(exportedText).then(
                  () => feedback.success("Text copied to clipboard."),
                  () => feedback.error("Could not copy. Please select the text and copy it manually."),
                )
              }
            >
              Copy
            </Button>
            <Button variant="secondary" onClick={() => setExportedText(null)}>
              Close
            </Button>
          </div>
        </Modal>
      )}
    </>
  );
}
