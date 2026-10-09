"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ACCESS_RIGHTS,
  NO_RIGHTS,
  PERMISSIONS,
  type AccessRight,
  type PermissionDto,
  type RoleDto,
  type RolePermissionDto,
} from "@transmatch/shared";
import { useEffect, useState } from "react";
import { Button, Card, PageHeader, SelectField } from "@/components/ui";
import { api } from "@/lib/api";
import { useCan } from "@/lib/session";
import { useAction } from "@/lib/use-action";

// Rights the screens act on today; the remaining positions are reserved
const EDITABLE_RIGHTS: AccessRight[] = ["VIEW", "CREATE", "UPDATE", "DELETE"];
const RIGHT_LABELS: Record<string, string> = { VIEW: "View", CREATE: "Create", UPDATE: "Update", DELETE: "Delete" };

export default function UserRightsPage() {
  const can = useCan(PERMISSIONS.ADM_USER_RIGHTS);
  const { run, busy } = useAction();
  const [roleId, setRoleId] = useState("");
  const [rights, setRights] = useState<Record<string, string>>({});

  const roles = useQuery({ queryKey: ["roles", "rights-options"], queryFn: () => api<RoleDto[]>("/role-permissions/roles") });
  const permissions = useQuery({
    queryKey: ["permissions"],
    queryFn: () => api<PermissionDto[]>("/role-permissions/permissions"),
    staleTime: Infinity,
  });
  const current = useQuery({
    queryKey: ["role-permissions", roleId],
    queryFn: () => api<RolePermissionDto[]>(`/role-permissions/${roleId}`),
    enabled: roleId !== "",
  });

  // Start editing from what the role holds now
  useEffect(() => {
    setRights(Object.fromEntries((current.data ?? []).map((p) => [p.permissionId, p.rights])));
  }, [current.data]);

  const role = roles.data?.find((r) => r.roleId === roleId);
  const editable = can("UPDATE") && !!role && !role.noDelete;

  const toggle = (permissionId: string, right: AccessRight, on: boolean) => {
    const index = ACCESS_RIGHTS.indexOf(right);
    setRights((prev) => {
      const chars = (prev[permissionId] ?? NO_RIGHTS).split("");
      chars[index] = on ? "1" : "0";
      // Nothing can be done on a screen that cannot be opened
      if (right === "VIEW" && !on) return { ...prev, [permissionId]: NO_RIGHTS };
      if (right !== "VIEW" && on) chars[0] = "1";
      const next = { ...prev, [permissionId]: chars.join("") };
      // A screen is reached through its main menu, so granting it shows the menu too
      const parentId = permissions.data?.find((p) => p.permissionId === permissionId)?.parentPermissionId;
      if (on && parentId && (next[parentId] ?? NO_RIGHTS)[0] !== "1") next[parentId] = `1${NO_RIGHTS.slice(1)}`;
      return next;
    });
  };

  const save = () =>
    run(
      () =>
        api(`/role-permissions/${roleId}`, {
          method: "PUT",
          body: { items: (permissions.data ?? []).map((p) => ({ permissionId: p.permissionId, rights: rights[p.permissionId] ?? NO_RIGHTS })) },
        }),
      { success: "User rights saved. They apply the next time the affected users open a screen.", refresh: ["role-permissions", "session"] },
    );

  return (
    <>
      <PageHeader title="User Rights" section="Administration" />
      <div className="space-y-4">
        <Card title="Role">
          <SelectField
            label="User Role"
            value={roleId}
            onChange={setRoleId}
            placeholder="Select a role"
            className="max-w-md"
            options={(roles.data ?? []).map((r) => ({ value: r.roleId, label: `${r.groupName} / ${r.roleName}` }))}
          />
          {role?.noDelete && <p className="mt-2 text-sm text-amber-700">This is a protected system role; its rights cannot be changed.</p>}
        </Card>

        {roleId && (
          <Card
            title="Screens and rights"
            actions={
              editable && (
                <Button onClick={save} disabled={busy || current.isLoading}>
                  {busy ? "Saving…" : "Save"}
                </Button>
              )
            }
          >
            <div className="overflow-auto rounded-md border border-slate-200">
              <table className="w-full border-collapse text-sm">
                <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
                  <tr>
                    <th scope="col" className="px-3 py-2 text-left font-semibold">
                      Menu / Screen
                    </th>
                    {EDITABLE_RIGHTS.map((right) => (
                      <th key={right} scope="col" className="w-24 px-3 py-2 text-center font-semibold">
                        {RIGHT_LABELS[right]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(permissions.data ?? []).map((permission) => {
                    const value = rights[permission.permissionId] ?? NO_RIGHTS;
                    return (
                      <tr key={permission.permissionId} className={`border-t border-slate-100 ${permission.mainMenu ? "bg-slate-50 font-semibold" : ""}`}>
                        <th scope="row" className={`px-3 py-1.5 text-left font-normal ${permission.mainMenu ? "font-semibold" : "pl-8"}`}>
                          {permission.name}
                          <span className="ml-2 text-xs text-slate-400">{permission.description}</span>
                        </th>
                        {EDITABLE_RIGHTS.map((right) => (
                          <td key={right} className="px-3 py-1.5 text-center">
                            {/* A main menu is only shown or hidden */}
                            {(right === "VIEW" || !permission.mainMenu) && (
                              <input
                                type="checkbox"
                                aria-label={`${RIGHT_LABELS[right]} ${permission.name}`}
                                disabled={!editable}
                                checked={value[ACCESS_RIGHTS.indexOf(right)] === "1"}
                                onChange={(e) => toggle(permission.permissionId, right, e.target.checked)}
                              />
                            )}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
