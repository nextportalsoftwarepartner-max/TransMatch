"use client";

import { PERMISSIONS } from "@transmatch/shared";
import { WatchlistScreen } from "@/components/watchlist-screen";

export default function SuspiciousPage() {
  return <WatchlistScreen kind="suspicious" label="Suspicious" permission={PERMISSIONS.ADM_SUSPICIOUS} />;
}
