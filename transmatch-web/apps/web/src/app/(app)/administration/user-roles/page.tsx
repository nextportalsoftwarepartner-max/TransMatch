"use client";

import { useQuery } from "@tanstack/react-query";
import { PERMISSIONS, type GroupDto, type RoleDto } from "@transmatch/shared";
import { useState } from "react";
import { auditColumns, DataTable, type Column } from "@/components/data-table";
import { useFeedback } from "@/components/feedback";
import { NameFilter } from "@/components/name-filter";
import { Button, Card, PageHeader, SelectField, TextAreaField, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useCan } from "@/lib/session";
import { useAction } from "@/lib/use-action";

const columns: Column<RoleDto>[] = [
  { key: "groupName", header: "Group Name" },
  { key: "roleId", header: "Role ID", className: "whitespace-nowrap" },
  { key: "roleName", header: "Role Name" },
  { key: "roleDesc", header: "Description" },
  { key: "status", header: "Status", render: (r) => (r.status === "A" ? "Active" : "Deactivated") },
  ...auditColumns<RoleDto>(formatDateTime),
];

export default function UserRolesPage() {
  const can = useCan(PERMISSIONS.ADM_USER_ROLE);
  const feedback = useFeedback();
  const { run, busy } = useAction();

  const [nameFilter, setNameFilter] = useState("");
  const [selected, setSelected] = useState<RoleDto | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [groupId, setGroupId] = useState("");
  const [roleName, setRoleName] = useState("");
  const [roleDesc, setRoleDesc] = useState("");

  const roles = useQuery({
    queryKey: ["roles", nameFilter],
    queryFn: () => api<RoleDto[]>("/roles", { query: { name: nameFilter } }),
  });
  const groups = useQuery({ queryKey: ["groups", "options"], queryFn: () => api<GroupDto[]>("/roles/group-options") });

  const resetEntry = () => {
    setEditingId(null);
    setGroupId("");
    setRoleName("");
    setRoleDesc("");
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const body = { groupId, roleName, roleDesc };
    const ok = await run(
      () => (editingId ? api(`/roles/${editingId}`, { method: "PUT", body }) : api("/roles", { method: "POST", body })),
      { success: editingId ? "Role updated successfully." : "Role added successfully.", refresh: ["roles"] },
    );
    if (ok) resetEntry();
  };

  const edit = () => {
    if (!selected) return;
    setEditingId(selected.roleId);
    setGroupId(selected.groupId);
    setRoleName(selected.roleName);
    setRoleDesc(selected.roleDesc ?? "");
  };

  const remove = async () => {
    if (!selected) return;
    const confirmed = await feedback.confirm({
      title: "Delete user role",
      message: `Delete the role "${selected.roleName}"?`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    const ok = await run(() => api(`/roles/${selected.roleId}`, { method: "DELETE" }), {
      success: "Role deleted.",
      refresh: ["roles"],
    });
    if (ok) {
      setSelected(null);
      resetEntry();
    }
  };

  const setStatus = async (status: "A" | "I") => {
    if (!selected) return;
    const ok = await run(() => api(`/roles/${selected.roleId}/status`, { method: "PATCH", body: { status } }), {
      success: `Role has been ${status === "A" ? "activated" : "deactivated"}.`,
      refresh: ["roles"],
    });
    if (ok) setSelected(null);
  };

  return (
    <>
      <PageHeader title="User Role" section="Administration" />
      <div className="space-y-4">
        <NameFilter label="Role Name" onSearch={setNameFilter} />

        {(can("CREATE") || can("UPDATE")) && (
          <Card title={editingId ? "Edit Role" : "Data Entry"}>
            <form className="grid grid-cols-1 gap-3 md:grid-cols-2" onSubmit={save}>
              <SelectField
                label="Group"
                value={groupId}
                onChange={setGroupId}
                required
                placeholder="Select a group"
                options={(groups.data ?? []).map((g) => ({ value: g.groupId, label: g.groupName }))}
              />
              <TextField label="Role Name" value={roleName} onChange={setRoleName} required maxLength={50} />
              <TextAreaField label="Description" value={roleDesc} onChange={setRoleDesc} maxLength={255} rows={2} className="md:col-span-2" />
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
          title="Role Table"
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
            rows={roles.data ?? []}
            rowKey={(r) => r.roleId}
            selectedKey={selected?.roleId}
            onSelect={setSelected}
            emptyText={roles.isLoading ? "Loading…" : (roles.error?.message ?? "No matching user role found.")}
          />
        </Card>
      </div>
    </>
  );
}
