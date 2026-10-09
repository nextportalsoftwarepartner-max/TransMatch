"use client";

import type { SessionUser } from "@transmatch/shared";
import { useState } from "react";
import { Button, TextField } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

export default function LoginPage() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api<SessionUser>("/auth/login", { method: "POST", body: { loginId: loginId.trim(), password } });
      // Full navigation so every page starts from the new session
      window.location.assign("/");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-brand p-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl bg-white p-8 shadow-2xl">
        <h1 className="text-center text-2xl font-bold text-brand">TransMatch</h1>
        <p className="mb-6 mt-1 text-center text-sm text-slate-500">Welcome to TransMatch</p>

        <div className="space-y-4">
          <TextField label="Username" value={loginId} onChange={setLoginId} required autoFocus autoComplete="username" placeholder="Enter your user name" />
          <TextField label="Password" type="password" value={password} onChange={setPassword} required autoComplete="current-password" placeholder="Enter your password" />
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        )}

        <Button type="submit" className="mt-6 w-full" disabled={busy}>
          {busy ? "Signing in…" : "Login"}
        </Button>
      </form>
    </main>
  );
}
