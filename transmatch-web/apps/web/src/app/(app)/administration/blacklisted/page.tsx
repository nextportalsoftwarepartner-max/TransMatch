"use client";

import { PERMISSIONS } from "@transmatch/shared";
import { WatchlistScreen } from "@/components/watchlist-screen";

export default function BlacklistedPage() {
  return <WatchlistScreen kind="blacklisted" label="Blacklisted" permission={PERMISSIONS.ADM_BLACKLISTED} />;
}
