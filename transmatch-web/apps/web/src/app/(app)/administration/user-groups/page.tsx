"use client";

import { useQuery } from "@tanstack/react-query";
import { PERMISSIONS, type GroupDto } from "@transmatch/shared";
import { useState } from "react";
import { auditColumns, DataTable, type Column } from "@/components/data-table";
import { useFeedback } from "@/components/feedback";
import { NameFilter } from "@/components/name-filter";
import { Button, Card, PageHeader, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useCan } from "@/lib/session";
import { useAction } from "@/lib/use-action";

const columns: Column<GroupDto>[] = [
  { key: "groupId", header: "Group ID", className: "whitespace-nowrap" },
  { key: "groupName", header: "Group Name" },
  { key: "groupDesc", header: "Description" },
  { key: "status", header: "Status", render: (g) => (g.status === "A" ? "Active" : "Deactivated") },
  ...auditColumns<GroupDto>(formatDateTime),
];

export default function UserGroupsPage() {
  const can = useCan(PERMISSIONS.ADM_USER_GROUP);
  const feedback = useFeedback();
  const { run, busy } = useAction();

  const [nameFilter, setNameFilter] = useState("");
  const [selected, setSelected] = useState<GroupDto | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [groupName, setGroupName] = useState("");
  const [groupDesc, setGroupDesc] = useState("");

  const groups = useQuery({
    queryKey: ["groups", nameFilter],
    queryFn: () => api<GroupDto[]>("/groups", { query: { name: nameFilter } }),
  });

  const resetEntry = () => {
    setEditingId(null);
    setGroupName("");
    setGroupDesc("");
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const body = { groupName, groupDesc };
    const ok = await run(
      () => (editingId ? api(`/groups/${editingId}`, { method: "PUT", body }) : api("/groups", { method: "POST", body })),
      { success: editingId ? "Group updated successfully." : "Group added successfully.", refresh: ["groups"] },
    );
    if (ok) resetEntry();
  };

  const edit = () => {
    if (!selected) return;
    setEditingId(selected.groupId);
    setGroupName(selected.groupName);
    setGroupDesc(selected.groupDesc ?? "");
  };

  const remove = async () => {
    if (!selected) return;
    const confirmed = await feedback.confirm({
      title: "Delete user group",
      message: `Delete the group "${selected.groupName}"?`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    const ok = await run(() => api(`/groups/${selected.groupId}`, { method: "DELETE" }), {
      success: "Group deleted.",
      refresh: ["groups"],
    });
    if (ok) {
      setSelected(null);
      resetEntry();
    }
  };

  const setStatus = async (status: "A" | "I") => {
    if (!selected) return;
    const ok = await run(() => api(`/groups/${selected.groupId}/status`, { method: "PATCH", body: { status } }), {
      success: `Group has been ${status === "A" ? "activated" : "deactivated"}.`,
      refresh: ["groups"],
    });
    if (ok) setSelected(null);
  };

  return (
    <>
      <PageHeader title="User Group" section="Administration" />
      <div className="space-y-4">
        <NameFilter label="Group Name" onSearch={setNameFilter} />

        {(can("CREATE") || can("UPDATE")) && (
          <Card title={editingId ? "Edit Group" : "Data Entry"}>
            <form className="flex flex-wrap items-end gap-3" onSubmit={save}>
              <TextField label="Group Name" value={groupName} onChange={setGroupName} required maxLength={50} className="w-72" />
              <TextField label="Description" value={groupDesc} onChange={setGroupDesc} maxLength={100} className="w-96" />
              <Button type="submit" disabled={busy || !can(editingId ? "UPDATE" : "CREATE")}>
                {editingId ? "Update" : "Add"}
              </Button>
              <Button variant="secondary" onClick={resetEntry}>
                Reset
              </Button>
            </form>
          </Card>
        )}

        <Card
          title="Group Table"
          actions={
            <>
              {can("UPDATE") && (
                <>
                  <Button variant="secondary" disabled={!selected} onClick={edit}>
                    Edit
                  </Button>
                  <Button variant="secondary" disabled={!selected || selected.status === "I" || busy} onClick={() => setStatus("I")}>
                    Deactivate
                  </Button>
                  <Button variant="secondary" disabled={!selected || selected.status === "A" || busy} onClick={() => setStatus("A")}>
                    Activate
                  </Button>
                </>
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
            rows={groups.data ?? []}
            rowKey={(g) => g.groupId}
            selectedKey={selected?.groupId}
            onSelect={setSelected}
            emptyText={groups.isLoading ? "Loading…" : (groups.error?.message ?? "No matching user group found.")}
          />
        </Card>
      </div>
    </>
  );
}
