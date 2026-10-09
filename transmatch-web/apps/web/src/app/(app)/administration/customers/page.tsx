"use client";

import { useQuery } from "@tanstack/react-query";
import { PERMISSIONS, type CustomerDto } from "@transmatch/shared";
import { useState } from "react";
import { auditColumns, DataTable, type Column } from "@/components/data-table";
import { useFeedback } from "@/components/feedback";
import { Button, Card, Modal, PageHeader, TextAreaField, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useCan } from "@/lib/session";
import { useAction } from "@/lib/use-action";

const EMPTY_FORM = { customerCode: "", customerName: "", email: "", contactNo: "+60", address: "" };

const columns: Column<CustomerDto>[] = [
  { key: "customerCode", header: "Customer Code", className: "whitespace-nowrap" },
  { key: "customerName", header: "Customer Name" },
  { key: "email", header: "Customer Email" },
  { key: "contactNo", header: "Customer Contact", className: "whitespace-nowrap" },
  { key: "address", header: "Customer Address" },
  { key: "remark", header: "Remark", render: (c) => (c.remark ? "Yes" : ""), align: "center" },
  ...auditColumns<CustomerDto>(formatDateTime),
];

export default function CustomersPage() {
  const can = useCan(PERMISSIONS.ADM_CUSTOMER_PROFILE);
  const feedback = useFeedback();
  const { run, busy } = useAction();

  const [filterInput, setFilterInput] = useState({ code: "", name: "" });
  const [filter, setFilter] = useState(filterInput);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [remarkOf, setRemarkOf] = useState<CustomerDto | null>(null);
  const set = (patch: Partial<typeof EMPTY_FORM>) => setForm((f) => ({ ...f, ...patch }));

  const customers = useQuery({
    queryKey: ["customers", filter],
    queryFn: () => api<CustomerDto[]>("/customers", { query: filter }),
  });
  const rows = customers.data ?? [];
  const checkedRows = rows.filter((c) => checked.has(c.customerId));

  const resetEntry = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    // "+60" alone is just the default country code, not a number
    const body = { ...form, contactNo: /^\+\d{1,4}$/.test(form.contactNo.trim()) ? "" : form.contactNo };
    const ok = await run(
      () => (editingId ? api(`/customers/${editingId}`, { method: "PUT", body }) : api("/customers", { method: "POST", body })),
      { success: editingId ? "Customer updated successfully." : "Customer added successfully.", refresh: ["customers"] },
    );
    if (ok) resetEntry();
  };

  const edit = () => {
    const customer = checkedRows[0];
    if (!customer) return;
    setEditingId(customer.customerId);
    setForm({
      customerCode: customer.customerCode,
      customerName: customer.customerName,
      email: customer.email ?? "",
      contactNo: customer.contactNo ?? "+60",
      address: customer.address ?? "",
    });
  };

  const remove = async () => {
    const confirmed = await feedback.confirm({
      title: "Delete customers",
      message: `Are you sure you want to delete ${checkedRows.length} customer(s)?`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    const ok = await run(
      async () => {
        for (const customer of checkedRows) await api(`/customers/${customer.customerId}`, { method: "DELETE" });
      },
      { success: `Deleted ${checkedRows.length} customer(s) successfully.`, refresh: ["customers"] },
    );
    if (ok) {
      setChecked(new Set());
      resetEntry();
    }
  };

  return (
    <>
      <PageHeader title="Customer Profile" section="Administration" />
      <div className="space-y-4">
        <Card title="Filter Criteria">
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              setFilter({ code: filterInput.code.trim(), name: filterInput.name.trim() });
            }}
          >
            <TextField label="Customer Code" value={filterInput.code} onChange={(code) => setFilterInput({ ...filterInput, code })} className="w-56" />
            <TextField label="Customer Name" value={filterInput.name} onChange={(name) => setFilterInput({ ...filterInput, name })} className="w-72" />
            <Button type="submit">Search</Button>
            <Button
              variant="secondary"
              onClick={() => {
                setFilterInput({ code: "", name: "" });
                setFilter({ code: "", name: "" });
              }}
            >
              Reset
            </Button>
          </form>
        </Card>

        {(can("CREATE") || can("UPDATE")) && (
          <Card title={editingId ? "Edit Customer" : "Data Entry"}>
            <form className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={save}>
              <TextField label="Customer Code" value={form.customerCode} onChange={(customerCode) => set({ customerCode })} required maxLength={30} uppercase />
              <TextField label="Customer Name" value={form.customerName} onChange={(customerName) => set({ customerName })} required maxLength={100} uppercase />
              <TextField label="Customer Email" type="email" value={form.email} onChange={(email) => set({ email })} maxLength={100} />
              <TextField label="Customer Contact" value={form.contactNo} onChange={(contactNo) => set({ contactNo })} maxLength={20} placeholder="+60123456789" />
              <TextField label="Customer Address" value={form.address} onChange={(address) => set({ address })} maxLength={255} className="md:col-span-2 xl:col-span-4" />
              <div className="flex gap-2 md:col-span-2 xl:col-span-4">
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
          title="Customer Table"
          actions={
            <>
              <span className="text-xs text-slate-500">Double-click a row to view or edit its remark</span>
              {can("UPDATE") && (
                <Button variant="secondary" disabled={checkedRows.length !== 1} onClick={edit}>
                  Edit
                </Button>
              )}
              {can("DELETE") && (
                <Button variant="danger" disabled={checkedRows.length === 0 || busy} onClick={remove}>
                  Delete
                </Button>
              )}
            </>
          }
        >
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(c) => c.customerId}
            checkedKeys={checked}
            onCheckedChange={setChecked}
            onRowDoubleClick={setRemarkOf}
            emptyText={customers.isLoading ? "Loading…" : (customers.error?.message ?? "No customers found.")}
          />
        </Card>
      </div>

      {remarkOf && <RemarkDialog customer={remarkOf} readOnly={!can("UPDATE")} onClose={() => setRemarkOf(null)} />}
    </>
  );
}

function RemarkDialog({ customer, readOnly, onClose }: { customer: CustomerDto; readOnly: boolean; onClose: () => void }) {
  const { run, busy } = useAction();
  const [remark, setRemark] = useState(customer.remark ?? "");

  const save = async () => {
    const ok = await run(() => api(`/customers/${customer.customerId}/remark`, { method: "PUT", body: { remark } }), {
      success: "Remark updated successfully.",
      refresh: ["customers"],
    });
    if (ok) onClose();
  };

  return (
    <Modal title={`Customer Remark: ${customer.customerCode}`} onClose={onClose} width="max-w-xl">
      <TextAreaField label="Customer Remark" value={remark} onChange={setRemark} rows={12} maxLength={4000} readOnly={readOnly} />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        {!readOnly && (
          <Button onClick={save} disabled={busy}>
            Save
          </Button>
        )}
      </div>
    </Modal>
  );
}
