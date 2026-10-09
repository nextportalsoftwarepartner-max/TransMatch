"use client";

import { useQuery } from "@tanstack/react-query";
import { PERMISSIONS, type OptionDto, type TransactionDetailDto, type TransactionListRowDto } from "@transmatch/shared";
import { useEffect, useState } from "react";
import { DataTable, type Column } from "@/components/data-table";
import { DateRangeFilter, MatchTextFilter, type DateType } from "@/components/transaction-filters";
import { Button, Card, Modal, PageHeader, SelectField, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime, parseMoney } from "@/lib/format";
import { useCan } from "@/lib/session";
import { useAction } from "@/lib/use-action";

interface BankOption extends OptionDto {
  registrationNo: string | null;
  address: string | null;
}
interface CustomerOption extends OptionDto {
  name: string;
  address: string | null;
}

const EMPTY_FILTER = {
  customerCode: "",
  customerName: "",
  customerNameMatch: "Equal" as "Equal" | "Contain",
  accountNo: "",
  targetName: "",
  fileName: "",
  description: "",
  descriptionMatch: "Equal" as "Equal" | "Contain",
  dateType: "transaction" as DateType,
  dateFrom: "",
  dateTo: "",
};

const columns: Column<TransactionListRowDto>[] = [
  { key: "customerCode", header: "Customer Code", className: "whitespace-nowrap" },
  { key: "customerName", header: "Customer Name" },
  { key: "accountNo", header: "Account Number", className: "whitespace-nowrap" },
  { key: "targetName", header: "Target Audience" },
  { key: "fileName", header: "File Name" },
  { key: "description", header: "Transaction Description" },
  { key: "transactionDate", header: "Transaction Date", className: "whitespace-nowrap" },
  { key: "entryDate", header: "Data Entry Date", render: (r) => formatDateTime(r.entryDate), className: "whitespace-nowrap" },
];

export default function DataEnrichmentPage() {
  const can = useCan(PERMISSIONS.TRN_DATA_ENRICHMENT);
  const [filterInput, setFilterInput] = useState(EMPTY_FILTER);
  // Nothing is searched until the user asks
  const [filter, setFilter] = useState<typeof EMPTY_FILTER | null>(null);
  // Counts searches, so pressing Search again with the same criteria reloads the data
  const [searchRun, setSearchRun] = useState(0);
  const [editingId, setEditingId] = useState<string | null>(null);
  const set = (patch: Partial<typeof EMPTY_FILTER>) => setFilterInput((f) => ({ ...f, ...patch }));

  const customers = useQuery({ queryKey: ["customer-options"], queryFn: () => api<CustomerOption[]>("/transactions/lookups/customers") });
  const files = useQuery({ queryKey: ["file-names"], queryFn: () => api<string[]>("/transactions/lookups/file-names") });
  const results = useQuery({
    queryKey: ["transactions", filter, searchRun],
    queryFn: () => api<TransactionListRowDto[]>("/transactions", { query: filter ?? {} }),
    enabled: filter !== null,
  });

  return (
    <>
      <PageHeader title="Data Enrichment" section="Transaction" />
      <div className="space-y-4">
        <Card title="Filter Criteria">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setFilter({ ...filterInput });
              setSearchRun((n) => n + 1);
            }}
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <SelectField
                label="Customer Code"
                value={filterInput.customerCode}
                onChange={(customerCode) => set({ customerCode })}
                placeholder="All"
                options={(customers.data ?? []).map((c) => ({ value: c.label, label: c.label }))}
              />
              <MatchTextFilter
                label="Customer Name"
                value={filterInput.customerName}
                match={filterInput.customerNameMatch}
                onChange={(p) => set({ ...(p.value !== undefined && { customerName: p.value }), ...(p.match && { customerNameMatch: p.match }) })}
              />
              <TextField label="Account Number" value={filterInput.accountNo} onChange={(accountNo) => set({ accountNo })} />
              <TextField label="Target Audience" value={filterInput.targetName} onChange={(targetName) => set({ targetName })} />
              <SelectField
                label="File Name"
                value={filterInput.fileName}
                onChange={(fileName) => set({ fileName })}
                placeholder="All"
                options={(files.data ?? []).map((f) => ({ value: f, label: f }))}
              />
              <MatchTextFilter
                label="Transaction Desc"
                value={filterInput.description}
                match={filterInput.descriptionMatch}
                onChange={(p) => set({ ...(p.value !== undefined && { description: p.value }), ...(p.match && { descriptionMatch: p.match }) })}
              />
              <DateRangeFilter dateType={filterInput.dateType} dateFrom={filterInput.dateFrom} dateTo={filterInput.dateTo} onChange={set} />
            </div>
            <div className="mt-3 flex gap-2">
              <Button type="submit">Search</Button>
              <Button variant="secondary" onClick={() => setFilterInput(EMPTY_FILTER)}>
                Reset
              </Button>
            </div>
          </form>
        </Card>

        <Card title="Results" actions={<span className="text-xs text-slate-500">Double-click a row to edit it</span>}>
          <DataTable
            columns={columns}
            rows={results.data ?? []}
            rowKey={(r) => r.transactionId}
            onRowDoubleClick={(r) => setEditingId(r.transactionId)}
            emptyText={
              filter === null
                ? "Enter the criteria and press Search."
                : results.isFetching
                  ? "Searching… Please wait."
                  : (results.error?.message ?? "No records found.")
            }
            maxHeight="max-h-[36rem]"
          />
          {(results.data?.length ?? 0) >= 5000 && (
            <p className="mt-1 text-xs text-amber-700">Only the first 5,000 matching rows are shown. Narrow the criteria to see the rest.</p>
          )}
        </Card>
      </div>

      {editingId && (
        <EditTransactionDialog
          transactionId={editingId}
          customers={customers.data ?? []}
          readOnly={!can("UPDATE")}
          onClose={() => setEditingId(null)}
        />
      )}
    </>
  );
}

interface EditProps {
  transactionId: string;
  customers: CustomerOption[];
  readOnly: boolean;
  onClose: () => void;
}

function EditTransactionDialog({ transactionId, customers, readOnly, onClose }: EditProps) {
  const { run, busy } = useAction();
  const detail = useQuery({
    queryKey: ["transaction", transactionId],
    queryFn: () => api<TransactionDetailDto>(`/transactions/${transactionId}`),
    gcTime: 0,
  });
  const banks = useQuery({ queryKey: ["bank-options"], queryFn: () => api<BankOption[]>("/transactions/lookups/banks") });
  const agents = useQuery({ queryKey: ["agent-options"], queryFn: () => api<OptionDto[]>("/transactions/lookups/agents") });

  const [form, setForm] = useState<(TransactionDetailDto & { credit: string; debit: string; balance: string }) | null>(null);
  const [amountError, setAmountError] = useState(false);
  useEffect(() => {
    if (detail.data) {
      setForm({
        ...detail.data,
        credit: String(detail.data.creditAmount),
        debit: String(detail.data.debitAmount),
        balance: String(detail.data.statementBalance),
      });
    }
  }, [detail.data]);
  const set = (patch: Partial<NonNullable<typeof form>>) => setForm((f) => (f ? { ...f, ...patch } : f));

  const bank = banks.data?.find((b) => b.value === form?.bankId);
  const customer = customers.find((c) => c.value === form?.customerId);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form) return;
    const creditAmount = parseMoney(form.credit);
    const debitAmount = parseMoney(form.debit);
    const statementBalance = parseMoney(form.balance);
    if (creditAmount === null || debitAmount === null || statementBalance === null || creditAmount < 0 || debitAmount < 0) {
      setAmountError(true);
      return;
    }
    const { transactionId: _id, credit: _c, debit: _d, balance: _b, ...rest } = form;
    const ok = await run(
      () =>
        api(`/transactions/${transactionId}`, {
          method: "PUT",
          body: {
            ...rest,
            description: rest.description ?? "",
            descriptionOthers: rest.descriptionOthers ?? "",
            targetName: rest.targetName ?? "",
            creditAmount,
            debitAmount,
            statementBalance,
          },
        }),
      { success: "Transaction record updated successfully.", refresh: ["transactions", "file-names"] },
    );
    if (ok) onClose();
  };

  return (
    <Modal title="Edit Transaction Record" onClose={onClose} width="max-w-5xl">
      {!form ? (
        <p className="text-sm text-slate-500">{detail.error?.message ?? "Loading…"}</p>
      ) : (
        <form onSubmit={save}>
          <fieldset disabled={readOnly} className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <TextField label="File Name" value={form.fileName ?? ""} onChange={(fileName) => set({ fileName })} maxLength={255} className="md:col-span-2" />
            <SelectField label="Bank Name" value={form.bankId} onChange={(bankId) => set({ bankId })} required options={banks.data ?? []} />
            <TextField label="Bank Address" value={bank?.address ?? ""} onChange={() => undefined} readOnly />
            <TextField label="Bank Reg No" value={bank?.registrationNo ?? ""} onChange={() => undefined} readOnly />
            <SelectField label="Customer Code" value={form.customerId} onChange={(customerId) => set({ customerId })} required options={customers} />
            <TextField label="Customer Name" value={customer?.name ?? ""} onChange={() => undefined} readOnly />
            <TextField label="Customer Address" value={customer?.address ?? ""} onChange={() => undefined} readOnly />
            <TextField label="Account No" value={form.accountNo ?? ""} onChange={(accountNo) => set({ accountNo })} maxLength={30} />
            <TextField label="Statement Date" type="date" value={form.statementDate ?? ""} onChange={(statementDate) => set({ statementDate })} />
            <TextField label="Transaction Date" type="date" value={form.transactionDate} onChange={(transactionDate) => set({ transactionDate })} required />
            <TextField label="Transaction Desc" value={form.description ?? ""} onChange={(description) => set({ description })} maxLength={1000} />
            <TextField label="Desc Others" value={form.descriptionOthers ?? ""} onChange={(descriptionOthers) => set({ descriptionOthers })} maxLength={4000} className="md:col-span-2" />
            <TextField label="Target Audience" value={form.targetName ?? ""} onChange={(targetName) => set({ targetName })} maxLength={255} />
            <TextField label="Credit Amount" value={form.credit} onChange={(credit) => set({ credit })} inputMode="decimal" />
            <TextField label="Debit Amount" value={form.debit} onChange={(debit) => set({ debit })} inputMode="decimal" />
            <TextField label="Statement Balance" value={form.balance} onChange={(balance) => set({ balance })} inputMode="decimal" />
            <SelectField
              label="Printed Status"
              value={form.printed ? "Y" : "N"}
              onChange={(v) => set({ printed: v === "Y" })}
              options={[
                { value: "N", label: "No" },
                { value: "Y", label: "Yes" },
              ]}
            />
            <SelectField label="Agent Name" value={form.agentUserId} onChange={(agentUserId) => set({ agentUserId })} required options={agents.data ?? []} />
          </fieldset>
          {amountError && (
            <p role="alert" className="mt-3 text-sm text-red-700">
              Amounts must be numbers with at most two decimal places; credit and debit cannot be negative.
            </p>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            {!readOnly && (
              <Button type="submit" disabled={busy}>
                Save
              </Button>
            )}
          </div>
        </form>
      )}
    </Modal>
  );
}
