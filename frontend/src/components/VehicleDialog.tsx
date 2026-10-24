import { useEffect, useRef, useState, type FormEvent } from "react";
import { X, AlertTriangle } from "lucide-react";
import type { Vehicle } from "../lib/types";
import { validPrice, validQuantity } from "../lib/validation";
import { ErrorMessage } from "./Feedback";
import { messageOf } from "../lib/api";

export type VehicleAction =
  | { kind: "create" }
  | { kind: "edit" | "delete" | "restock"; vehicle: Vehicle };
export function VehicleDialog({
  action,
  close,
  save,
}: {
  action: VehicleAction;
  close: () => void;
  save: (body?: unknown) => Promise<void>;
}) {
  const existing = action.kind === "create" ? undefined : action.vehicle;
  const [form, setForm] = useState({
    make: existing?.make || "",
    model: existing?.model || "",
    category: existing?.category || "",
    price: existing?.price || "",
    quantity: action.kind === "restock" ? "1" : "0",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const titles = {
    create: "Add a vehicle",
    edit: "Edit vehicle",
    delete: "Delete vehicle?",
    restock: "Restock vehicle",
  };
  function change(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    let body: unknown;
    if (action.kind === "create" || action.kind === "edit") {
      if (!form.make.trim() || !form.model.trim() || !form.category.trim()) {
        setError("Make, model and category are required.");
        return;
      }
      if (!validPrice(form.price)) {
        setError(
          "Enter a positive price with up to 10 whole digits and 2 decimal places.",
        );
        return;
      }
      body = {
        make: form.make.trim(),
        model: form.model.trim(),
        category: form.category.trim(),
        price: form.price,
      };
    }
    if (action.kind === "create" || action.kind === "restock") {
      if (!validQuantity(form.quantity, action.kind === "create")) {
        setError(
          action.kind === "create"
            ? "Enter a whole stock quantity from 0 to 2147483647."
            : "Enter a positive whole quantity up to 2147483647.",
        );
        return;
      }
      body = { ...(body || {}), quantity: Number(form.quantity) };
    }
    setBusy(true);
    try {
      await save(body);
      close();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      aria-labelledby="vehicle-dialog-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) close();
      }}
      className="modal"
    >
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-6">
        <div>
          <h2 id="vehicle-dialog-title" className="text-xl font-semibold">
            {titles[action.kind]}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {existing
              ? `${existing.make} ${existing.model}`
              : "Add the details of your next vehicle."}
          </p>
        </div>
        <button
          type="button"
          className="icon-btn"
          aria-label="Close dialog"
          disabled={busy}
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      <form onSubmit={submit} noValidate className="space-y-5 p-6">
        <ErrorMessage message={error} />
        {action.kind === "delete" ? (
          <div className="flex gap-3 rounded-xl bg-red-50 p-4 text-sm leading-6 text-red-900">
            <AlertTriangle className="shrink-0" size={22} aria-hidden="true" />
            <p>
              This permanently removes the vehicle and its remaining{" "}
              {existing?.quantity} units from inventory. This action cannot be
              undone.
            </p>
          </div>
        ) : (
          <>
            {action.kind !== "restock" && (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="field-label">
                    Make
                    <input
                      value={form.make}
                      onChange={(e) => change("make", e.target.value)}
                      maxLength={100}
                      disabled={busy}
                      placeholder="e.g. Toyota"
                    />
                  </label>
                  <label className="field-label">
                    Model
                    <input
                      value={form.model}
                      onChange={(e) => change("model", e.target.value)}
                      maxLength={100}
                      disabled={busy}
                      placeholder="e.g. Corolla"
                    />
                  </label>
                </div>
                <label className="field-label">
                  Category
                  <input
                    value={form.category}
                    onChange={(e) => change("category", e.target.value)}
                    maxLength={50}
                    disabled={busy}
                    placeholder="e.g. Sedan, SUV, Hatchback"
                  />
                </label>
                <label className="field-label">
                  Price
                  <input
                    inputMode="decimal"
                    value={form.price}
                    onChange={(e) => change("price", e.target.value)}
                    disabled={busy}
                    placeholder="0.00"
                  />
                </label>
              </>
            )}
            {action.kind !== "edit" ? (
              <label className="field-label">
                {action.kind === "restock" ? "Units to add" : "Initial stock"}
                <input
                  inputMode="numeric"
                  value={form.quantity}
                  onChange={(e) => change("quantity", e.target.value)}
                  disabled={busy}
                />
              </label>
            ) : (
              <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
                Available stock: {existing?.quantity}. Stock changes are handled
                through purchase and admin restock actions.
              </p>
            )}
          </>
        )}
        <div className="flex justify-end gap-3 border-t border-slate-100 pt-5">
          <button
            type="button"
            className="btn-secondary"
            disabled={busy}
            onClick={close}
          >
            Cancel
          </button>
          <button
            className={action.kind === "delete" ? "btn-danger" : "btn-primary"}
            disabled={busy}
          >
            {busy
              ? "Saving…"
              : action.kind === "create"
                ? "Add vehicle"
                : action.kind === "edit"
                  ? "Save changes"
                  : action.kind === "delete"
                    ? "Delete vehicle"
                    : "Add stock"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
