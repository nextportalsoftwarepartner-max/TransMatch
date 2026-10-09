"use client";

import { useQuery } from "@tanstack/react-query";
import { can, type AccessRight, type PermissionCode, type SessionUser } from "@transmatch/shared";
import { createContext, useContext, useEffect, type ReactNode } from "react";
import { api, ApiError } from "./api";

const SessionContext = createContext<SessionUser | null>(null);

/** Leaves the session behind and returns to the login page. */
export async function signOut(): Promise<void> {
  await api("/auth/logout", { method: "POST" }).catch(() => undefined);
  window.location.assign("/login");
}

/** Loads the signed-in user and renders the application once it is known. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const { data: user, error } = useQuery({
    queryKey: ["session"],
    queryFn: () => api<SessionUser>("/auth/me"),
    staleTime: 60_000,
  });

  // An expired or revoked session: clear the cookie and go to the login page
  const expired = error instanceof ApiError && error.status === 401;
  useEffect(() => {
    if (expired) void signOut();
  }, [expired]);

  if (error && !expired) {
    return <p className="p-8 text-center text-red-700">{error.message}</p>;
  }
  if (!user) {
    return <p className="p-8 text-center text-slate-500">Loading…</p>;
  }
  return <SessionContext.Provider value={user}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionUser {
  const user = useContext(SessionContext);
  if (!user) throw new Error("useSession must be used inside SessionProvider");
  return user;
}

/** Whether the signed-in user holds a right on a screen. */
export function useCan(code: PermissionCode): (right: AccessRight) => boolean {
  const user = useSession();
  return (right) => can(user, code, right);
}
