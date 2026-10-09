"use client";

import { useQuery } from "@tanstack/react-query";
import type { BankTemplateDto, StatementPreviewDto, StatementPreviewRowDto } from "@transmatch/shared";
import { useRef, useState } from "react";
import { useFeedback } from "@/components/feedback";
import { Button, Card, PageHeader, SelectField, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useAction } from "@/lib/use-action";

const CELL_INPUT = "w-full rounded border border-slate-300 px-1.5 py-0.5 text-sm focus:border-accent focus:outline-none";

export default function PdfUploadPage() {
  const feedback = useFeedback();
  const { run, busy } = useAction();
  const fileInput = useRef<HTMLInputElement>(null);

  const [templateId, setTemplateId] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [info, setInfo] = useState<Omit<StatementPreviewDto, "transactions"> | null>(null);
  const [rows, setRows] = useState<StatementPreviewRowDto[]>([]);

  const templates = useQuery({
    queryKey: ["bank-templates"],
    queryFn: () => api<BankTemplateDto[]>("/transactions/lookups/bank-templates"),
    staleTime: Infinity,
  });

  const reset = () => {
    setInfo(null);
    setRows([]);
  };

  const extract = async (file: File) => {
    reset();
    setExtracting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      if (templateId) form.append("bankId", templateId);
      const { transactions, ...header } = await api<StatementPreviewDto>("/transactions/pdf/extract", { method: "POST", form });
      setInfo(header);
      setRows(transactions);
      if (transactions.length === 0) feedback.error("No transactions were found in this statement.");
    } catch (error) {
      feedback.error(error);
    } finally {
      setExtracting(false);
    }
  };

  const setField = (patch: Partial<Omit<StatementPreviewDto, "transactions">>) => setInfo((current) => (current ? { ...current, ...patch } : current));
  const setRow = (index: number, patch: Partial<StatementPreviewRowDto>) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));

  const undated = rows.filter((row) => !row.transactionDate).length;

  const save = async () => {
    if (!info) return;
    if (!info.customerCode.trim()) {
      feedback.error("Customer Code is a mandatory field.\nPlease enter a valid customer code for this transaction upload.");
      return;
    }
    if (!info.statementDate) {
      feedback.error("Please enter the statement date.");
      return;
    }
    if (undated > 0) {
      feedback.error(`${undated} transaction(s) have no valid date. Please enter the date for the highlighted rows.`);
      return;
    }
    const ok = await run(
      () =>
        api("/transactions/batches", {
          method: "POST",
          body: {
            source: "PU",
            fileName: info.fileName,
            bank: { name: info.bankName, registrationNo: info.bankRegistrationNo, address: info.bankAddress },
            customer: { code: info.customerCode, name: info.customerName, address: info.customerAddress },
            // Account numbers are stored as digits only
            accountNo: info.accountNumber.replace(/\D/g, ""),
            statementDate: info.statementDate,
            transactions: rows.map(({ rawDate: _rawDate, ...row }) => row),
          },
        }),
      { success: "Transactions successfully saved into database." },
    );
    if (ok) reset();
  };

  return (
    <>
      <PageHeader title="Docx Upload" section="Transaction" />
      <div className="space-y-4">
        <Card title="Select PDF File">
          <div className="flex flex-wrap items-end gap-3">
            <SelectField
              label="Bank template"
              value={templateId}
              onChange={setTemplateId}
              placeholder="Detect automatically"
              options={(templates.data ?? []).map((t) => ({ value: String(t.id), label: t.name }))}
              className="w-64"
            />
            <Button disabled={extracting} onClick={() => fileInput.current?.click()}>
              {extracting ? "Extracting PDF detail… Please wait." : "Browse…"}
            </Button>
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              aria-label="Bank statement PDF"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) void extract(file);
              }}
            />
            {info && (
              <p className="text-sm text-slate-600">
                <span className="font-medium">{info.fileName}</span> · read as {info.bankTemplate}
              </p>
            )}
          </div>
        </Card>

        {info && (
          <>
            <Card title="Statement Details">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <TextField label="Bank Name" value={info.bankName} onChange={(bankName) => setField({ bankName })} required maxLength={100} />
                <TextField label="Bank Registration No" value={info.bankRegistrationNo} onChange={(bankRegistrationNo) => setField({ bankRegistrationNo })} maxLength={255} />
                <TextField label="Bank Address" value={info.bankAddress} onChange={(bankAddress) => setField({ bankAddress })} maxLength={255} />
                <TextField
                  label={info.customerKnown ? "Customer Code (customer already on file)" : "Customer Code"}
                  value={info.customerCode}
                  onChange={(customerCode) => setField({ customerCode })}
                  required
                  uppercase
                  maxLength={30}
                  readOnly={info.customerKnown}
                />
                <TextField label="Customer Name" value={info.customerName} onChange={(customerName) => setField({ customerName })} required maxLength={100} readOnly={info.customerKnown} />
                <TextField label="Customer Address" value={info.customerAddress} onChange={(customerAddress) => setField({ customerAddress })} maxLength={255} />
                <TextField label="Statement Date" type="date" value={info.statementDate ?? ""} onChange={(statementDate) => setField({ statementDate })} required />
                <TextField label="Account Number" value={info.accountNumber} onChange={(accountNumber) => setField({ accountNumber })} maxLength={30} />
              </div>
            </Card>

            <Card
              title="Transactions"
              actions={
                <>
                  <Button onClick={save} disabled={busy || rows.length === 0}>
                    {busy ? "Saving transaction… Please wait." : "Save"}
                  </Button>
                  <Button variant="secondary" onClick={reset}>
                    Reset
                  </Button>
                </>
              }
            >
              <div className="max-h-[32rem] overflow-auto rounded-md border border-slate-200">
                <table className="w-full border-collapse text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
                    <tr>
                      <th scope="col" className="px-2 py-2 text-left">Transaction Date</th>
                      <th scope="col" className="px-2 py-2 text-left">Transaction Description</th>
                      <th scope="col" className="px-2 py-2 text-left">Transaction Description-Others</th>
                      <th scope="col" className="px-2 py-2 text-left">Target Audience</th>
                      <th scope="col" className="px-2 py-2 text-right">Credit Amount</th>
                      <th scope="col" className="px-2 py-2 text-right">Debit Amount</th>
                      <th scope="col" className="px-2 py-2 text-right">Statement Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, index) => (
                      <tr key={index} className={`border-t border-slate-100 ${row.transactionDate ? "odd:bg-white even:bg-slate-50" : "bg-amber-50"}`}>
                        <td className="whitespace-nowrap px-2 py-1">
                          <input
                            type="date"
                            aria-label={`Transaction date, row ${index + 1}`}
                            title={row.transactionDate ? undefined : `Printed on the statement as "${row.rawDate}"`}
                            className={CELL_INPUT}
                            value={row.transactionDate ?? ""}
                            onChange={(e) => setRow(index, { transactionDate: e.target.value || null })}
                          />
                        </td>
                        <td className="px-2 py-1">{row.description}</td>
                        <td className="px-2 py-1">{row.descriptionOthers}</td>
                        <td className="px-2 py-1">
                          <input
                            aria-label={`Target audience, row ${index + 1}`}
                            className={CELL_INPUT}
                            value={row.targetName}
                            maxLength={255}
                            onChange={(e) => setRow(index, { targetName: e.target.value })}
                          />
                        </td>
                        <td className="whitespace-nowrap px-2 py-1 text-right">{formatMoney(row.creditAmount)}</td>
                        <td className="whitespace-nowrap px-2 py-1 text-right">{formatMoney(row.debitAmount)}</td>
                        <td className="whitespace-nowrap px-2 py-1 text-right">{formatMoney(row.statementBalance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-1 text-right text-xs text-slate-500">Total Transactions: {rows.length}</p>
            </Card>
          </>
        )}
      </div>
    </>
  );
}
