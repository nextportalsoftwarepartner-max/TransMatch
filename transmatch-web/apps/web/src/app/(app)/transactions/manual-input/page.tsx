"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DataTable, type Column } from "@/components/data-table";
import { useFeedback } from "@/components/feedback";
import { Button, Card, PageHeader, SelectField, TextAreaField, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatMoney, parseMoney, today } from "@/lib/format";
import { useAction } from "@/lib/use-action";

interface BankOption {
  value: string;
  label: string;
  registrationNo: string | null;
  address: string | null;
}

interface CustomerLookup {
  found: boolean;
  customerName?: string;
  address?: string | null;
}

interface EntryRow {
  key: number;
  transactionDate: string;
  description: string;
  descriptionOthers: string;
  targetName: string;
  creditAmount: number;
  debitAmount: number;
  statementBalance: number;
}

const MANUAL_BANK = "";

const emptyStatic = () => ({
  fileName: "",
  bankId: MANUAL_BANK,
  bankName: "",
  bankRegistrationNo: "",
  bankAddress: "",
  customerCode: "",
  customerName: "",
  customerAddress: "",
  statementDate: today(),
  accountNo: "",
});

const emptyEntry = () => ({
  transactionDate: today(),
  description: "",
  descriptionOthers: "",
  targetName: "",
  credit: "",
  debit: "",
  balance: "",
});

const columns: Column<EntryRow>[] = [
  { key: "transactionDate", header: "Transaction Date", className: "whitespace-nowrap" },
  { key: "description", header: "Transaction Description" },
  { key: "descriptionOthers", header: "Transaction Description-Others" },
  { key: "targetName", header: "Target Audience" },
  { key: "creditAmount", header: "Transaction Amount (Credit)", align: "right", render: (r) => (r.creditAmount ? formatMoney(r.creditAmount) : "") },
  { key: "debitAmount", header: "Transaction Amount (Debit)", align: "right", render: (r) => (r.debitAmount ? formatMoney(r.debitAmount) : "") },
  { key: "statementBalance", header: "Statement Balance", align: "right", render: (r) => formatMoney(r.statementBalance) },
];

export default function ManualInputPage() {
  const feedback = useFeedback();
  const { run, busy } = useAction();

  const [info, setInfo] = useState(emptyStatic);
  const [customerKnown, setCustomerKnown] = useState(false);
  const [entry, setEntry] = useState(emptyEntry);
  const [rows, setRows] = useState<EntryRow[]>([]);
  const [selectedKey, setSelectedKey] = useState<number | null>(null);
  const [nextKey, setNextKey] = useState(1);
  const setField = (patch: Partial<ReturnType<typeof emptyStatic>>) => setInfo((s) => ({ ...s, ...patch }));
  const setEntryField = (patch: Partial<ReturnType<typeof emptyEntry>>) => setEntry((e) => ({ ...e, ...patch }));

  const banks = useQuery({ queryKey: ["bank-options"], queryFn: () => api<BankOption[]>("/transactions/lookups/banks") });
  const bankOnFile = info.bankId !== MANUAL_BANK;

  // Choosing a bank on file fills in its details; "Manual Input" lets them be typed
  const chooseBank = (bankId: string) => {
    const bank = banks.data?.find((b) => b.value === bankId);
    setField({
      bankId,
      bankName: bank?.label ?? "",
      bankRegistrationNo: bank?.registrationNo ?? "",
      bankAddress: bank?.address ?? "",
    });
  };

  // A customer code already on file brings the name and address with it
  const lookupCustomer = async () => {
    const code = info.customerCode.trim();
    if (!code) return;
    try {
      const customer = await api<CustomerLookup>("/transactions/lookups/customer-by-code", { query: { code } });
      setCustomerKnown(customer.found);
      setField({ customerName: customer.customerName ?? "", customerAddress: customer.address ?? "" });
    } catch (error) {
      feedback.error(error);
    }
  };

  const addRow = () => {
    const description = entry.description.trim();
    const descriptionOthers = entry.descriptionOthers.split(/\s+/).filter(Boolean).join(" ");
    const targetName = entry.targetName.trim();
    if (!entry.transactionDate || !description || !descriptionOthers || !targetName || !entry.balance.trim()) {
      feedback.error("All fields must be filled in.");
      return;
    }
    if (!entry.credit.trim() && !entry.debit.trim()) {
      feedback.error("Please enter either Credit Amount or Debit Amount.");
      return;
    }
    if (entry.credit.trim() && entry.debit.trim()) {
      feedback.error("You cannot enter both Credit and Debit Amounts.");
      return;
    }
    const creditAmount = parseMoney(entry.credit);
    const debitAmount = parseMoney(entry.debit);
    const statementBalance = parseMoney(entry.balance);
    if (creditAmount === null || debitAmount === null || statementBalance === null || creditAmount < 0 || debitAmount < 0) {
      feedback.error("Amounts must be numbers with at most two decimal places.");
      return;
    }
    setRows((current) => [
      ...current,
      { key: nextKey, transactionDate: entry.transactionDate, description, descriptionOthers, targetName, creditAmount, debitAmount, statementBalance },
    ]);
    setNextKey((k) => k + 1);
    setEntry({ ...emptyEntry(), transactionDate: entry.transactionDate });
  };

  // Editing moves the row back into the entry fields
  const editRow = () => {
    const row = rows.find((r) => r.key === selectedKey);
    if (!row) return;
    setEntry({
      transactionDate: row.transactionDate,
      description: row.description,
      descriptionOthers: row.descriptionOthers,
      targetName: row.targetName,
      credit: row.creditAmount ? String(row.creditAmount) : "",
      debit: row.debitAmount ? String(row.debitAmount) : "",
      balance: String(row.statementBalance),
    });
    deleteRow();
  };

  const deleteRow = () => {
    setRows((current) => current.filter((r) => r.key !== selectedKey));
    setSelectedKey(null);
  };

  const resetAll = () => {
    setInfo(emptyStatic());
    setCustomerKnown(false);
    setEntry(emptyEntry());
    setRows([]);
    setSelectedKey(null);
  };

  const save = async () => {
    if (rows.length === 0) {
      feedback.error("No transaction records found in the table.");
      return;
    }
    const ok = await run(
      () =>
        api("/transactions/batches", {
          method: "POST",
          body: {
            source: "MI",
            fileName: info.fileName,
            bank: { name: info.bankName, registrationNo: info.bankRegistrationNo, address: info.bankAddress },
            customer: { code: info.customerCode, name: info.customerName, address: info.customerAddress },
            accountNo: info.accountNo,
            statementDate: info.statementDate,
            transactions: rows.map(({ key: _key, ...row }) => row),
          },
        }),
      { success: "Transactions successfully saved into database.", refresh: ["bank-options"] },
    );
    if (ok) resetAll();
  };

  return (
    <>
      <PageHeader title="Manual Data Input" section="Transaction" />
      <div className="space-y-4">
        <Card
          title="Static Info"
          actions={
            <Button
              variant="secondary"
              onClick={() => {
                setInfo(emptyStatic());
                setCustomerKnown(false);
              }}
            >
              Reset General Info
            </Button>
          }
        >
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <TextField label="File Name" value={info.fileName} onChange={(fileName) => setField({ fileName })} maxLength={255} />
            <SelectField
              label="Bank"
              value={info.bankId}
              onChange={chooseBank}
              placeholder="Manual Input"
              options={(banks.data ?? []).map((b) => ({ value: b.value, label: b.label }))}
            />
            <TextField label="Bank Name" value={info.bankName} onChange={(bankName) => setField({ bankName })} required maxLength={100} readOnly={bankOnFile} />
            <TextField label="Bank Registration No" value={info.bankRegistrationNo} onChange={(bankRegistrationNo) => setField({ bankRegistrationNo })} maxLength={255} readOnly={bankOnFile} />
            <TextField label="Bank Address" value={info.bankAddress} onChange={(bankAddress) => setField({ bankAddress })} maxLength={255} uppercase readOnly={bankOnFile} className="xl:col-span-2" />
            <div onBlur={lookupCustomer}>
              <TextField
                label="Customer Code"
                value={info.customerCode}
                onChange={(customerCode) => {
                  setCustomerKnown(false);
                  setField({ customerCode });
                }}
                required
                uppercase
                maxLength={30}
              />
            </div>
            <TextField label="Customer Name" value={info.customerName} onChange={(customerName) => setField({ customerName })} required uppercase maxLength={100} readOnly={customerKnown} />
            <TextField label="Customer Address" value={info.customerAddress} onChange={(customerAddress) => setField({ customerAddress })} uppercase maxLength={255} readOnly={customerKnown} />
            <TextField label="Statement Date" type="date" value={info.statementDate} onChange={(statementDate) => setField({ statementDate })} required />
            <TextField
              label="Account Number"
              value={info.accountNo}
              onChange={(accountNo) => setField({ accountNo: accountNo.replace(/\D/g, "") })}
              inputMode="numeric"
              maxLength={30}
            />
          </div>
        </Card>

        <Card title="Transaction Entry">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <TextField label="Transaction Date" type="date" value={entry.transactionDate} onChange={(transactionDate) => setEntryField({ transactionDate })} />
            <TextField label="Transaction Description" value={entry.description} onChange={(description) => setEntryField({ description })} maxLength={1000} className="xl:col-span-2" />
            <TextField label="Target Audience" value={entry.targetName} onChange={(targetName) => setEntryField({ targetName })} maxLength={255} />
            <TextAreaField
              label="Transaction Description-Others"
              value={entry.descriptionOthers}
              onChange={(descriptionOthers) => setEntryField({ descriptionOthers })}
              rows={2}
              maxLength={4000}
              className="md:col-span-2 xl:col-span-4"
            />
            <TextField label="Credit Amount" value={entry.credit} onChange={(credit) => setEntryField({ credit })} inputMode="decimal" />
            <TextField label="Debit Amount" value={entry.debit} onChange={(debit) => setEntryField({ debit })} inputMode="decimal" />
            <TextField label="Statement Balance" value={entry.balance} onChange={(balance) => setEntryField({ balance })} inputMode="decimal" />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button onClick={addRow}>Add</Button>
            <Button variant="secondary" disabled={selectedKey === null} onClick={editRow}>
              Edit
            </Button>
            <Button variant="secondary" disabled={selectedKey === null} onClick={deleteRow}>
              Delete
            </Button>
            <Button variant="secondary" onClick={() => setEntry(emptyEntry())}>
              Reset
            </Button>
          </div>
        </Card>

        <Card
          title="Transaction Records"
          actions={
            <>
              <Button variant="secondary" onClick={resetAll}>
                Reset All
              </Button>
              <Button onClick={save} disabled={busy}>
                {busy ? "Saving transaction… Please wait." : "Save"}
              </Button>
            </>
          }
        >
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(r) => String(r.key)}
            selectedKey={selectedKey === null ? null : String(selectedKey)}
            onSelect={(r) => setSelectedKey(r.key)}
            emptyText="No transactions added yet."
            maxHeight="max-h-80"
            countLabel="Total Transactions"
          />
        </Card>
      </div>
    </>
  );
}
