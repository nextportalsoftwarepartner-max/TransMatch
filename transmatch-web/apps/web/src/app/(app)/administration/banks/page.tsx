"use client";

import { useQuery } from "@tanstack/react-query";
import { PERMISSIONS, type BankDto } from "@transmatch/shared";
import { useState } from "react";
import { auditColumns, DataTable, type Column } from "@/components/data-table";
import { useFeedback } from "@/components/feedback";
import { NameFilter } from "@/components/name-filter";
import { Button, Card, PageHeader, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useCan } from "@/lib/session";
import { useAction } from "@/lib/use-action";

const EMPTY_FORM = { bankName: "", bankDisplayName: "", bankRegNo: "", bankAddress: "" };

const columns: Column<BankDto>[] = [
  { key: "bankId", header: "Bank ID", className: "whitespace-nowrap" },
  { key: "bankName", header: "Bank Name" },
  { key: "bankDisplayName", header: "Display Name" },
  { key: "bankRegNo", header: "Reg No." },
  { key: "bankAddress", header: "Address" },
  ...auditColumns<BankDto>(formatDateTime),
];

export default function BanksPage() {
  const can = useCan(PERMISSIONS.ADM_BANK_PROFILE);
  const feedback = useFeedback();
  const { run, busy } = useAction();

  const [nameFilter, setNameFilter] = useState("");
  const [selected, setSelected] = useState<BankDto | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const set = (patch: Partial<typeof EMPTY_FORM>) => setForm((f) => ({ ...f, ...patch }));

  const banks = useQuery({
    queryKey: ["banks", nameFilter],
    queryFn: () => api<BankDto[]>("/banks", { query: { name: nameFilter } }),
  });

  const resetEntry = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const ok = await run(
      () => (editingId ? api(`/banks/${editingId}`, { method: "PUT", body: form }) : api("/banks", { method: "POST", body: form })),
      { success: "Bank saved successfully.", refresh: ["banks"] },
    );
    if (ok) resetEntry();
  };

  const edit = () => {
    if (!selected) return;
    setEditingId(selected.bankId);
    setForm({
      bankName: selected.bankName,
      bankDisplayName: selected.bankDisplayName ?? "",
      bankRegNo: selected.bankRegNo ?? "",
      bankAddress: selected.bankAddress ?? "",
    });
  };

  const remove = async () => {
    if (!selected) return;
    const confirmed = await feedback.confirm({
      title: "Delete bank",
      message: `Are you sure you want to delete the bank "${selected.bankName}"?`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    const ok = await run(() => api(`/banks/${selected.bankId}`, { method: "DELETE" }), {
      success: "Bank deleted successfully.",
      refresh: ["banks"],
    });
    if (ok) {
      setSelected(null);
      resetEntry();
    }
  };

  return (
    <>
      <PageHeader title="Bank Profile" section="Administration" />
      <div className="space-y-4">
        <NameFilter label="Bank Name" onSearch={setNameFilter} />

        {(can("CREATE") || can("UPDATE")) && (
          <Card title={editingId ? "Edit Bank" : "Bank Entry"}>
            <form className="grid grid-cols-1 gap-3 md:grid-cols-2" onSubmit={save}>
              <TextField label="Bank Name" value={form.bankName} onChange={(bankName) => set({ bankName })} required maxLength={100} />
              <TextField label="Registration No." value={form.bankRegNo} onChange={(bankRegNo) => set({ bankRegNo })} maxLength={255} />
              <TextField
                label="Display Name (defaults to the bank name)"
                value={form.bankDisplayName}
                onChange={(bankDisplayName) => set({ bankDisplayName })}
                maxLength={50}
              />
              <TextField label="Address" value={form.bankAddress} onChange={(bankAddress) => set({ bankAddress })} maxLength={255} />
              <div className="flex gap-2 md:col-span-2">
                <Button type="submit" disabled={busy || !can(editingId ? "UPDATE" : "CREATE")}>
                  {editingId ? "Update" : "Add"}
                </Button>
                <Button variant="secondary" onClick={resetEntry}>
                  Reset
                </Button>
              </div>
            </form>
          </Card>
        )}

        <Card
          title="Bank List"
          actions={
            <>
              {can("UPDATE") && (
                <Button variant="secondary" disabled={!selected} onClick={edit}>
                  Edit
                </Button>
              )}
              {can("DELETE") && (
                <Button variant="danger" disabled={!selected || busy} onClick={remove}>
                  Delete
                </Button>
              )}
            </>
          }
        >
          <DataTable
            columns={columns}
            rows={banks.data ?? []}
            rowKey={(b) => b.bankId}
            selectedKey={selected?.bankId}
            onSelect={setSelected}
            emptyText={banks.isLoading ? "Loading…" : (banks.error?.message ?? "No banks found.")}
          />
        </Card>
      </div>
    </>
  );
}
