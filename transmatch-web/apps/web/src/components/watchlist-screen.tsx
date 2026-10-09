"use client";

import { useQuery } from "@tanstack/react-query";
import type { PermissionCode, WatchNameDto } from "@transmatch/shared";
import { useRef, useState } from "react";
import { api, download } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useCan } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import { auditColumns, DataTable, type Column } from "./data-table";
import { useFeedback } from "./feedback";
import { NameFilter } from "./name-filter";
import { Button, Card, PageHeader, SelectField, TextField } from "./ui";

interface WatchlistScreenProps {
  kind: "blacklisted" | "suspicious";
  /** "Blacklisted" or "Suspicious" */
  label: string;
  permission: PermissionCode;
}

/** Maintenance screen shared by the blacklisted and suspicious name lists. */
export function WatchlistScreen({ kind, label, permission }: WatchlistScreenProps) {
  const can = useCan(permission);
  const feedback = useFeedback();
  const { run, busy } = useAction();
  const fileInput = useRef<HTMLInputElement>(null);

  const [nameFilter, setNameFilter] = useState("");
  const [inBlacklist, setInBlacklist] = useState("");
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");

  const list = useQuery({
    queryKey: [kind, nameFilter, inBlacklist],
    queryFn: () => api<WatchNameDto[]>(`/${kind}`, { query: { name: nameFilter, existsInBlacklisted: inBlacklist } }),
  });
  const rows = list.data ?? [];
  const checkedRows = rows.filter((r) => checked.has(r.id));

  const columns: Column<WatchNameDto>[] = [
    { key: "name", header: `${label} Name` },
    ...(kind === "suspicious"
      ? [{ key: "existsInBlacklisted", header: "In Blacklist?", render: (r: WatchNameDto) => (r.existsInBlacklisted ? "Yes" : "No"), align: "center" as const }]
      : []),
    ...auditColumns<WatchNameDto>(formatDateTime),
  ];

  const resetEntry = () => {
    setEditingId(null);
    setName("");
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const body = { name };
    const ok = await run(
      () => (editingId ? api(`/${kind}/${editingId}`, { method: "PUT", body }) : api(`/${kind}`, { method: "POST", body })),
      { success: `'${name.trim()}' ${editingId ? "updated" : "inserted"} successfully.`, refresh: [kind] },
    );
    if (ok) resetEntry();
  };

  const edit = () => {
    const row = checkedRows[0];
    if (!row) return;
    setEditingId(row.id);
    setName(row.name);
  };

  const remove = async () => {
    const confirmed = await feedback.confirm({
      title: "Confirm Deletion",
      message: `Are you sure you want to delete the ${checkedRows.length} selected record(s)?`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    const ok = await run(
      async () => {
        const result = await api<{ deleted: number }>(`/${kind}/delete`, { method: "POST", body: { ids: checkedRows.map((r) => r.id) } });
        feedback.success(`${result.deleted} record(s) deleted.`);
      },
      { refresh: [kind] },
    );
    if (ok) {
      setChecked(new Set());
      resetEntry();
    }
  };

  const importFile = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    await run(
      async () => {
        const result = await api<{ inserted: number; skipped: number }>(`/${kind}/import`, { method: "POST", form });
        feedback.success(
          `${result.inserted} row(s) imported successfully.` + (result.skipped ? `\n${result.skipped} name(s) were already on the list and skipped.` : ""),
        );
      },
      { refresh: [kind] },
    );
  };

  return (
    <>
      <PageHeader title={label} section="Administration" />
      <div className="space-y-4">
        <NameFilter label={`${label} Name`} onSearch={setNameFilter} onReset={() => setInBlacklist("")}>
          {kind === "suspicious" && (
            <SelectField
              label="Exists In Blacklisted?"
              value={inBlacklist}
              onChange={setInBlacklist}
              placeholder="All"
              options={[
                { value: "Yes", label: "Yes" },
                { value: "No", label: "No" },
              ]}
              className="w-48"
            />
          )}
        </NameFilter>

        {(can("CREATE") || can("UPDATE")) && (
          <Card title={editingId ? `Edit ${label} Name` : "Data Entry"}>
            <div className="flex flex-wrap items-end gap-3">
              <form className="flex flex-wrap items-end gap-3" onSubmit={save}>
                <TextField label={`${label} Name`} value={name} onChange={setName} required maxLength={100} className="w-80" />
                <Button type="submit" disabled={busy || !can(editingId ? "UPDATE" : "CREATE")}>
                  {editingId ? "Update" : "Add"}
                </Button>
                <Button variant="secondary" onClick={resetEntry}>
                  Reset
                </Button>
              </form>
              {can("CREATE") && (
                <div className="ml-auto flex items-end gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => download(`/${kind}/template`, `${kind}_template.xlsx`).catch((error) => feedback.error(error))}
                  >
                    Download Template
                  </Button>
                  <Button variant="secondary" disabled={busy} onClick={() => fileInput.current?.click()}>
                    Import Excel
                  </Button>
                  <input
                    ref={fileInput}
                    type="file"
                    accept=".xlsx"
                    className="hidden"
                    aria-label={`Import ${label.toLowerCase()} names from Excel`}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (file) void importFile(file);
                    }}
                  />
                </div>
              )}
            </div>
          </Card>
        )}

        <Card
          title={`${label} Table`}
          actions={
            <>
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
            rowKey={(r) => r.id}
            checkedKeys={checked}
            onCheckedChange={setChecked}
            emptyText={list.isLoading ? "Loading…" : (list.error?.message ?? "No records found.")}
          />
        </Card>
      </div>
    </>
  );
}
