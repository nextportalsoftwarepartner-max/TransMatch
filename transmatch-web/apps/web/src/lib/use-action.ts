"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { useFeedback } from "@/components/feedback";

interface ActionOptions {
  /** Shown when the action succeeds. */
  success?: string;
  /** Query keys to reload afterwards. */
  refresh?: string[];
}

/**
 * Runs a save/delete style action: tracks the busy state, reports the outcome
 * and reloads the lists that changed. Resolves true when the action succeeded.
 */
export function useAction() {
  const feedback = useFeedback();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);

  const run = useCallback(
    async (action: () => Promise<unknown>, options: ActionOptions = {}): Promise<boolean> => {
      setBusy(true);
      try {
        await action();
        if (options.success) feedback.success(options.success);
        await Promise.all((options.refresh ?? []).map((key) => queryClient.invalidateQueries({ queryKey: [key] })));
        return true;
      } catch (error) {
        feedback.error(error);
        return false;
      } finally {
        setBusy(false);
      }
    },
    [feedback, queryClient],
  );

  return { run, busy };
}
