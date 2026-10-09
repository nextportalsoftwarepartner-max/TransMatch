"use client";

import { can, NAVIGATION, type NavSection, type SessionUser } from "@transmatch/shared";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { SessionProvider, signOut, useSession } from "@/lib/session";
import { useFeedback } from "./feedback";
import { Button, Modal, TextField } from "./ui";

/** Menu sections and items the user may open. */
export function visibleNavigation(user: SessionUser): NavSection[] {
  return NAVIGATION.filter((section) => can(user, section.code))
    .map((section) => ({ ...section, items: section.items.filter((item) => can(user, item.code)) }))
    .filter((section) => section.items.length > 0);
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <div className="flex min-h-screen flex-col">
        <TopBar />
        <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-5">{children}</main>
        <footer className="border-t border-slate-200 bg-white px-4 py-2 text-center text-xs text-slate-500">
          TransMatch System
        </footer>
      </div>
    </SessionProvider>
  );
}

function TopBar() {
  const user = useSession();
  const pathname = usePathname();
  const [changingPassword, setChangingPassword] = useState(false);

  return (
    <header className="bg-brand text-white shadow">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2">
        <Link href="/" className="text-lg font-bold tracking-wide">
          TransMatch
        </Link>

        <nav aria-label="Main" className="flex flex-1 flex-wrap items-center gap-1">
          {visibleNavigation(user).map((section) => {
            const active = section.items.some((item) => pathname.startsWith(item.href));
            return (
              <div key={section.code} className="group relative">
                <button
                  type="button"
                  aria-haspopup="true"
                  className={`rounded px-3 py-1.5 text-sm font-medium hover:bg-brand-soft ${active ? "bg-brand-soft" : ""}`}
                >
                  {section.label}
                </button>
                <ul className="invisible absolute left-0 top-full z-30 min-w-56 rounded-md border border-slate-200 bg-white py-1 text-slate-800 opacity-0 shadow-lg transition-opacity group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100">
                  {section.items.map((item) => (
                    <li key={item.code}>
                      <Link
                        href={item.href}
                        className={`block px-4 py-2 text-sm hover:bg-slate-100 ${pathname.startsWith(item.href) ? "font-semibold text-accent" : ""}`}
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-200">{user.userName}</span>
          <button type="button" className="underline-offset-2 hover:underline" onClick={() => setChangingPassword(true)}>
            Change password
          </button>
          <button type="button" className="rounded border border-white/40 px-2.5 py-1 hover:bg-brand-soft" onClick={() => void signOut()}>
            Sign out
          </button>
        </div>
      </div>
      {changingPassword && <ChangePasswordDialog onClose={() => setChangingPassword(false)} />}
    </header>
  );
}

function ChangePasswordDialog({ onClose }: { onClose: () => void }) {
  const feedback = useFeedback();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (newPassword !== repeatPassword) {
      feedback.error("The new passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      await api("/auth/change-password", { method: "POST", body: { currentPassword, newPassword } });
      feedback.success("Password changed.");
      onClose();
    } catch (error) {
      feedback.error(error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Change password" onClose={onClose} width="max-w-md">
      <form onSubmit={submit} className="space-y-3 text-slate-800">
        <TextField label="Current password" type="password" value={currentPassword} onChange={setCurrentPassword} required autoComplete="current-password" />
        <TextField label="New password (at least 8 characters)" type="password" value={newPassword} onChange={setNewPassword} required minLength={8} autoComplete="new-password" />
        <TextField label="Repeat new password" type="password" value={repeatPassword} onChange={setRepeatPassword} required minLength={8} autoComplete="new-password" />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Change password"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
