"use client";

import { useQuery } from "@tanstack/react-query";
import { PERMISSIONS, type GroupDto, type OptionDto, type RoleDto, type UserDto } from "@transmatch/shared";
import { useState } from "react";
import { auditColumns, DataTable, type Column } from "@/components/data-table";
import { useFeedback } from "@/components/feedback";
import { Button, Card, Modal, PageHeader, SelectField, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useCan, useSession } from "@/lib/session";
import { useAction } from "@/lib/use-action";

interface FormOptions {
  groups: GroupDto[];
  roles: RoleDto[];
  supervisors: OptionDto[];
}

const EMPTY_FORM = {
  groupId: "",
  roleId: "",
  loginId: "",
  password: "",
  supervisorUserId: "",
  userName: "",
  email: "",
  contactNo: "",
  address1: "",
  address2: "",
  address3: "",
  address4: "",
};

const columns: Column<UserDto>[] = [
  { key: "userId", header: "User ID", className: "whitespace-nowrap" },
  { key: "userName", header: "User Name" },
  { key: "loginId", header: "Login ID" },
  { key: "groupName", header: "User Group" },
  { key: "roleName", header: "User Role" },
  { key: "supervisorName", header: "Supervisor Name" },
  ...auditColumns<UserDto>(formatDateTime),
];

export default function UserProfilesPage() {
  const can = useCan(PERMISSIONS.ADM_USER_PROFILE);
  const session = useSession();
  const feedback = useFeedback();
  const { run, busy } = useAction();

  const [filterInput, setFilterInput] = useState({ groupId: "", roleId: "", name: "" });
  const [filter, setFilter] = useState(filterInput);
  const [selected, setSelected] = useState<UserDto | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [resetting, setResetting] = useState<UserDto | null>(null);
  const set = (patch: Partial<typeof EMPTY_FORM>) => setForm((f) => ({ ...f, ...patch }));

  const options = useQuery({ queryKey: ["users", "form-options"], queryFn: () => api<FormOptions>("/users/form-options") });
  const users = useQuery({
    queryKey: ["users", filter],
    queryFn: () => api<UserDto[]>("/users", { query: filter }),
  });

  const groupOptions = (options.data?.groups ?? []).map((g) => ({ value: g.groupId, label: g.groupName }));
  const rolesOf = (groupId: string) =>
    (options.data?.roles ?? []).filter((r) => !groupId || r.groupId === groupId).map((r) => ({ value: r.roleId, label: r.roleName }));

  const resetEntry = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const { groupId: _groupId, password, supervisorUserId, ...rest } = form;
    const body = { ...rest, supervisorUserId: supervisorUserId || null };
    const ok = await run(
      () =>
        editingId
          ? api(`/users/${editingId}`, { method: "PUT", body })
          : api("/users", { method: "POST", body: { ...body, password } }),
      { success: editingId ? "User updated successfully." : "User successfully added.", refresh: ["users"] },
    );
    if (ok) resetEntry();
  };

  const edit = () => {
    if (!selected) return;
    setEditingId(selected.userId);
    setForm({
      groupId: selected.groupId ?? "",
      roleId: selected.roleId ?? "",
      loginId: selected.loginId,
      password: "",
      supervisorUserId: selected.supervisorUserId ?? "",
      userName: selected.userName,
      email: selected.email ?? "",
      contactNo: selected.contactNo ?? "",
      address1: selected.address1 ?? "",
      address2: selected.address2 ?? "",
      address3: selected.address3 ?? "",
      address4: selected.address4 ?? "",
    });
  };

  const remove = async () => {
    if (!selected) return;
    const confirmed = await feedback.confirm({
      title: "Delete user",
      message: `Are you sure you want to delete the user "${selected.loginId}"?`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    const ok = await run(() => api(`/users/${selected.userId}`, { method: "DELETE" }), {
      success: "User has been deactivated.",
      refresh: ["users"],
    });
    if (ok) {
      setSelected(null);
      resetEntry();
    }
  };

  return (
    <>
      <PageHeader title="User Profile" section="Administration" />
      <div className="space-y-4">
        <Card title="Filter Criteria">
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              setFilter({ ...filterInput, name: filterInput.name.trim() });
            }}
          >
            <SelectField
              label="User Group"
              value={filterInput.groupId}
              onChange={(groupId) => setFilterInput({ ...filterInput, groupId, roleId: "" })}
              placeholder="All"
              options={groupOptions}
              className="w-56"
            />
            <SelectField
              label="User Role"
              value={filterInput.roleId}
              onChange={(roleId) => setFilterInput({ ...filterInput, roleId })}
              placeholder="All"
              options={rolesOf(filterInput.groupId)}
              className="w-56"
            />
            <TextField label="Staff Name" value={filterInput.name} onChange={(name) => setFilterInput({ ...filterInput, name })} className="w-64" />
            <Button type="submit">Search</Button>
            <Button
              variant="secondary"
              onClick={() => {
                const cleared = { groupId: "", roleId: "", name: "" };
                setFilterInput(cleared);
                setFilter(cleared);
              }}
            >
              Clean
            </Button>
          </form>
        </Card>

        {(can("CREATE") || can("UPDATE")) && (
          <Card title={editingId ? "Edit User Profile" : "User Profile Entry"}>
            <form className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={save}>
              <SelectField
                label="User Group"
                value={form.groupId}
                onChange={(groupId) => set({ groupId, roleId: "" })}
                required
                placeholder="Select a group"
                options={groupOptions}
              />
              <SelectField
                label="User Role"
                value={form.roleId}
                onChange={(roleId) => set({ roleId })}
                required
                placeholder={form.groupId ? "Select a role" : "Select a group first"}
                options={form.groupId ? rolesOf(form.groupId) : []}
              />
              <TextField label="Login ID" value={form.loginId} onChange={(loginId) => set({ loginId })} required maxLength={100} autoComplete="off" />
              {editingId ? (
                <TextField label="Password" value="Use Reset Password to change it" onChange={() => undefined} disabled />
              ) : (
                <TextField
                  label="Password (at least 8 characters)"
                  type="password"
                  value={form.password}
                  onChange={(password) => set({ password })}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              )}
              <SelectField
                label="Supervisor"
                value={form.supervisorUserId}
                onChange={(supervisorUserId) => set({ supervisorUserId })}
                placeholder="None"
                options={(options.data?.supervisors ?? []).filter((s) => s.value !== editingId)}
              />
              <TextField label="Staff Name" value={form.userName} onChange={(userName) => set({ userName })} required maxLength={100} />
              <TextField label="Email" type="email" value={form.email} onChange={(email) => set({ email })} maxLength={100} />
              <TextField label="Contact" value={form.contactNo} onChange={(contactNo) => set({ contactNo })} maxLength={20} />
              <TextField label="Address 1" value={form.address1} onChange={(address1) => set({ address1 })} maxLength={255} className="xl:col-span-2" />
              <TextField label="Address 2" value={form.address2} onChange={(address2) => set({ address2 })} maxLength={255} className="xl:col-span-2" />
              <TextField label="Address 3" value={form.address3} onChange={(address3) => set({ address3 })} maxLength={255} className="xl:col-span-2" />
              <TextField label="Address 4" value={form.address4} onChange={(address4) => set({ address4 })} maxLength={255} className="xl:col-span-2" />
              <div className="flex gap-2 md:col-span-2 xl:col-span-4">
                <Button type="submit" disabled={busy || !can(editingId ? "UPDATE" : "CREATE")}>
                  {editingId ? "Update" : "Add"}
                </Button>
                <Button variant="secondary" onClick={resetEntry}>
                  Clean
                </Button>
              </div>
            </form>
          </Card>
        )}

        <Card
          title="Search Results"
          actions={
            <>
              {can("UPDATE") && (
                <>
                  <Button variant="secondary" disabled={!selected} onClick={edit}>
                    Edit
                  </Button>
                  <Button variant="secondary" disabled={!selected} onClick={() => setResetting(selected)}>
                    Reset Password
                  </Button>
                </>
              )}
              {can("DELETE") && (
                <Button variant="danger" disabled={!selected || busy || selected.userId === session.userId} onClick={remove}>
                  Delete
                </Button>
              )}
            </>
          }
        >
          <DataTable
            columns={columns}
            rows={users.data ?? []}
            rowKey={(u) => `${u.userId}:${u.roleId ?? ""}`}
            selectedKey={selected ? `${selected.userId}:${selected.roleId ?? ""}` : null}
            onSelect={setSelected}
            emptyText={users.isLoading ? "Loading…" : (users.error?.message ?? "No matching user found.")}
          />
        </Card>
      </div>

      {resetting && <ResetPasswordDialog user={resetting} onClose={() => setResetting(null)} />}
    </>
  );
}

function ResetPasswordDialog({ user, onClose }: { user: UserDto; onClose: () => void }) {
  const { run, busy } = useAction();
  const [newPassword, setNewPassword] = useState("");

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const ok = await run(() => api(`/users/${user.userId}/reset-password`, { method: "POST", body: { newPassword } }), {
      success: `Password for user '${user.loginId}' has been reset.`,
    });
    if (ok) onClose();
  };

  return (
    <Modal title="Reset Password" onClose={onClose} width="max-w-md">
      <form onSubmit={submit} className="space-y-4">
        <TextField
          label={`New password for user '${user.loginId}' (at least 8 characters)`}
          type="password"
          value={newPassword}
          onChange={setNewPassword}
          required
          minLength={8}
          autoFocus
          autoComplete="new-password"
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            Reset Password
          </Button>
        </div>
      </form>
    </Modal>
  );
}
