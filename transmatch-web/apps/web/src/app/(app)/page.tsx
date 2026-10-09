"use client";

import Link from "next/link";
import { visibleNavigation } from "@/components/app-shell";
import { useSession } from "@/lib/session";

export default function HomePage() {
  const user = useSession();
  const sections = visibleNavigation(user);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">Welcome, {user.userName}</h1>
      {sections.length === 0 && (
        <p className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Your account has not been given access to any function yet. Please contact your administrator.
        </p>
      )}
      {sections.map((section) => (
        <section key={section.code}>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">{section.label}</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {section.items.map((item) => (
              <Link
                key={item.code}
                href={item.href}
                className="rounded-lg border border-slate-200 bg-white px-4 py-6 text-center font-medium text-slate-800 shadow-sm transition hover:border-accent hover:text-accent hover:shadow"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
