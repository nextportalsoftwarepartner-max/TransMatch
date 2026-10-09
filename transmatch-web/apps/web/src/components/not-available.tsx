import { PageHeader } from "./ui";

/** Screen that exists in the menu but has not been built yet. */
export function NotAvailable({ title, section, note }: { title: string; section: string; note: string }) {
  return (
    <>
      <PageHeader title={title} section={section} />
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
        <p className="text-base font-medium text-slate-700">This function is not available yet.</p>
        <p className="mt-2 text-sm text-slate-500">{note}</p>
      </div>
    </>
  );
}
