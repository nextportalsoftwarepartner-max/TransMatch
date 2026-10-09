"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { FeedbackProvider } from "@/components/feedback";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false, staleTime: 15_000 } },
      }),
  );
  return (
    <QueryClientProvider client={queryClient}>
      <FeedbackProvider>{children}</FeedbackProvider>
    </QueryClientProvider>
  );
}
