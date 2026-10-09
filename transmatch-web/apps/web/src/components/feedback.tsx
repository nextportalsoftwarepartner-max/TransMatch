"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { errorMessage } from "@/lib/api";
import { Button, Modal } from "./ui";

interface Toast {
  id: number;
  kind: "success" | "error";
  message: string;
}

interface ConfirmRequest {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  resolve: (ok: boolean) => void;
}

interface Feedback {
  success(message: string): void;
  /** Shows an error message; accepts a thrown error. */
  error(error: unknown): void;
  /** Asks the user to confirm; resolves true when they agree. */
  confirm(options: Omit<ConfirmRequest, "resolve">): Promise<boolean>;
}

const FeedbackContext = createContext<Feedback | null>(null);

const SUCCESS_MS = 4000;
const ERROR_MS = 8000;

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [request, setRequest] = useState<ConfirmRequest | null>(null);
  const nextId = useRef(1);

  const push = useCallback((kind: Toast["kind"], message: string) => {
    const id = nextId.current++;
    setToasts((list) => [...list, { id, kind, message }]);
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), kind === "error" ? ERROR_MS : SUCCESS_MS);
  }, []);

  const feedback = useMemo<Feedback>(
    () => ({
      success: (message) => push("success", message),
      error: (error) => push("error", typeof error === "string" ? error : errorMessage(error)),
      confirm: (options) => new Promise<boolean>((resolve) => setRequest({ ...options, resolve })),
    }),
    [push],
  );

  const answer = (ok: boolean) => {
    request?.resolve(ok);
    setRequest(null);
  };

  return (
    <FeedbackContext.Provider value={feedback}>
      {children}

      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="polite">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.kind === "error" ? "alert" : "status"}
            className={`pointer-events-auto whitespace-pre-line rounded-md border px-4 py-3 text-sm shadow-lg ${
              toast.kind === "error"
                ? "border-red-300 bg-red-50 text-red-900"
                : "border-emerald-300 bg-emerald-50 text-emerald-900"
            }`}
          >
            {toast.message}
          </div>
        ))}
      </div>

      {request && (
        <Modal title={request.title} onClose={() => answer(false)} width="max-w-md">
          <p className="whitespace-pre-line text-sm text-slate-700">{request.message}</p>
          <div className="mt-6 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => answer(false)}>
              Cancel
            </Button>
            <Button variant={request.danger ? "danger" : "primary"} onClick={() => answer(true)} autoFocus>
              {request.confirmLabel ?? "Confirm"}
            </Button>
          </div>
        </Modal>
      )}
    </FeedbackContext.Provider>
  );
}

export function useFeedback(): Feedback {
  const feedback = useContext(FeedbackContext);
  if (!feedback) throw new Error("useFeedback must be used inside FeedbackProvider");
  return feedback;
}
