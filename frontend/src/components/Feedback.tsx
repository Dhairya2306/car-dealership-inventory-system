import { LoaderCircle } from "lucide-react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-3 p-12 text-sm text-slate-500"
    >
      <LoaderCircle
        className="animate-spin motion-reduce:animate-none"
        size={20}
        aria-hidden="true"
      />
      {label}
    </div>
  );
}
export function ErrorMessage({ message }: { message: string }) {
  return message ? (
    <p
      role="alert"
      className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      {message}
    </p>
  ) : null;
}
