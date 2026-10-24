import { useEffect, useState, type FormEvent } from "react";
import {
  CarFront,
  Boxes,
  CircleAlert,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  Pencil,
  Trash2,
  PackagePlus,
  ShoppingCart,
  X,
  LayoutDashboard,
  LogOut,
} from "lucide-react";
import { useAuth } from "../auth/AuthProvider";
import { ApiError, apiRequest, messageOf } from "../lib/api";
import type { Filters, Vehicle, VehiclePage } from "../lib/types";
import { priceLabel, validPrice } from "../lib/validation";
import { Brand } from "../components/Brand";
import { ErrorMessage, Loading } from "../components/Feedback";
import { VehicleDialog, type VehicleAction } from "../components/VehicleDialog";

const EMPTY_FILTERS: Filters = {
  make: "",
  model: "",
  category: "",
  min_price: "",
  max_price: "",
};
const PAGE_SIZE = 10;

export function InventoryPage() {
  const { user, token, logout, retry } = useAuth();
  const [draft, setDraft] = useState(EMPTY_FILTERS);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState<VehiclePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterError, setFilterError] = useState("");
  const [notice, setNotice] = useState("");
  const [actionError, setActionError] = useState("");
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [dialog, setDialog] = useState<VehicleAction | null>(null);
  const filtered = Object.values(filters).some(Boolean);
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    Object.entries(filters).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    setLoading(true);
    setError("");
    apiRequest<VehiclePage>(`/vehicles${filtered ? "/search" : ""}?${query}`, {
      token,
      signal: controller.signal,
    })
      .then((data) => {
        if (controller.signal.aborted) return;
        if (offset > 0 && offset >= data.total) {
          setOffset(
            Math.max(0, Math.floor((data.total - 1) / PAGE_SIZE) * PAGE_SIZE),
          );
          return;
        }
        setPage(data);
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(messageOf(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [token, filters, filtered, offset, revision]);

  function reload() {
    setRevision((value) => value + 1);
  }
  function applyFilters(event: FormEvent) {
    event.preventDefault();
    setFilterError("");
    if (
      [draft.min_price, draft.max_price].some(
        (value) => value && !validPrice(value, true),
      )
    ) {
      setFilterError(
        "Price filters must be nonnegative amounts with up to two decimal places.",
      );
      return;
    }
    if (
      draft.min_price &&
      draft.max_price &&
      Number(draft.min_price) > Number(draft.max_price)
    ) {
      setFilterError("Minimum price must not exceed maximum price.");
      return;
    }
    setFilters(
      Object.fromEntries(
        Object.entries(draft).map(([key, value]) => [key, value.trim()]),
      ) as unknown as Filters,
    );
    setOffset(0);
  }
  function resetFilters() {
    setDraft(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setOffset(0);
    setFilterError("");
  }
  function reconcileFailure(reason: unknown) {
    if (reason instanceof ApiError && [404, 409].includes(reason.status))
      reload();
    if (reason instanceof ApiError && reason.status === 403) retry();
  }
  async function purchase(vehicle: Vehicle) {
    setPurchasing(vehicle.id);
    setActionError("");
    setNotice("");
    try {
      await apiRequest<Vehicle>(`/vehicles/${vehicle.id}/purchase`, {
        method: "POST",
        token,
      });
      setNotice(
        `Purchased one ${vehicle.make} ${vehicle.model}. Inventory updated.`,
      );
      reload();
    } catch (reason) {
      setActionError(messageOf(reason));
      reconcileFailure(reason);
    } finally {
      setPurchasing(null);
    }
  }
  async function save(body?: unknown) {
    if (!dialog) return;
    const path =
      dialog.kind === "create"
        ? "/vehicles"
        : `/vehicles/${dialog.vehicle.id}${dialog.kind === "restock" ? "/restock" : ""}`;
    const method =
      dialog.kind === "edit"
        ? "PUT"
        : dialog.kind === "delete"
          ? "DELETE"
          : "POST";
    try {
      await apiRequest(path, { method, token, body });
      setNotice(
        {
          create: "Vehicle added.",
          edit: "Vehicle details updated.",
          delete: "Vehicle deleted.",
          restock: "Stock added successfully.",
        }[dialog.kind],
      );
      setActionError("");
      reload();
    } catch (reason) {
      reconcileFailure(reason);
      throw reason;
    }
  }

  const metrics = [
    {
      label: filtered ? "Vehicles matching filters" : "Vehicles in inventory",
      value: page?.total,
      icon: CarFront,
      color: "bg-orange-50 text-orange-600",
    },
    {
      label: "Available units · this page",
      value: page?.items.reduce((sum, v) => sum + v.quantity, 0),
      icon: Boxes,
      color: "bg-blue-50 text-blue-600",
    },
    {
      label: "Out of stock · this page",
      value: page?.items.filter((v) => v.quantity === 0).length,
      icon: CircleAlert,
      color: "bg-rose-50 text-rose-600",
    },
  ];

  return (
    <div className="min-h-screen bg-stone-50 lg:pl-64">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-slate-200 bg-white p-6 lg:flex">
        <Brand />
        <p className="eyebrow mb-3 mt-12 text-slate-400">Workspace</p>
        <a
          href="/inventory"
          aria-current="page"
          className="flex items-center gap-3 rounded-xl bg-orange-50 px-4 py-3 text-sm font-semibold text-orange-800"
        >
          <LayoutDashboard size={19} aria-hidden="true" />
          Vehicle inventory
        </a>
        <div className="mt-auto rounded-xl border border-slate-100 bg-slate-50 p-4">
          <p className="truncate text-sm font-semibold">
            {user?.name || user?.email}
          </p>
          <p className="mt-1 text-xs capitalize text-slate-500">
            {isAdmin ? "Administrator" : "Team member"}
          </p>
          <button
            className="mt-4 flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-orange-700"
            onClick={logout}
          >
            <LogOut size={16} aria-hidden="true" />
            Sign out
          </button>
        </div>
      </aside>
      <header className="flex min-h-20 items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 sm:px-9">
        <div className="lg:hidden">
          <Brand />
        </div>
        <p className="hidden text-sm text-slate-400 lg:block">
          Workspace <span className="px-3">/</span>
          <span className="font-medium text-slate-700">Vehicle inventory</span>
        </p>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-slate-500 sm:block">
            {user?.name || user?.email}
          </span>
          <span
            className="grid size-9 place-items-center rounded-full bg-orange-100 text-sm font-bold text-orange-800"
            aria-hidden="true"
          >
            {(user?.name || user?.email || "M").slice(0, 1).toUpperCase()}
          </span>
          <button
            aria-label="Sign out"
            className="icon-btn lg:hidden"
            onClick={logout}
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-[1500px] p-5 sm:p-9">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="eyebrow text-orange-700">
              Your dealership, at a glance
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
              Vehicle inventory
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              A clear view of every vehicle and every available unit.
            </p>
          </div>
          <button
            className="btn-primary"
            onClick={() => setDialog({ kind: "create" })}
          >
            <Plus size={18} aria-hidden="true" />
            Add vehicle
          </button>
        </div>
        <div className="mb-7 grid gap-4 sm:grid-cols-3">
          {metrics.map(({ label, value, icon: Icon, color }) => (
            <div
              key={label}
              className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-5"
            >
              <span
                className={`grid size-12 shrink-0 place-items-center rounded-xl ${color}`}
              >
                <Icon size={23} aria-hidden="true" />
              </span>
              <div>
                <p className="text-xs font-medium text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {loading || error ? "—" : (value ?? "—")}
                </p>
              </div>
            </div>
          ))}
        </div>
        <section
          aria-label="Inventory filters"
          className="mb-6 rounded-xl border border-slate-200 bg-white p-5"
        >
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <SlidersHorizontal
              size={16}
              className="text-orange-600"
              aria-hidden="true"
            />
            Find the right vehicle
          </div>
          <form onSubmit={applyFilters} noValidate>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {(
                [
                  ["make", "Make", "Any make"],
                  ["model", "Model", "Any model"],
                  ["category", "Category", "Any category"],
                  ["min_price", "Minimum price", "No minimum"],
                  ["max_price", "Maximum price", "No maximum"],
                ] as const
              ).map(([key, label, placeholder]) => (
                <label key={key} className="field-label">
                  {label}
                  <input
                    value={draft[key]}
                    onChange={(e) =>
                      setDraft((current) => ({
                        ...current,
                        [key]: e.target.value,
                      }))
                    }
                    placeholder={placeholder}
                    inputMode={key.includes("price") ? "decimal" : "text"}
                    maxLength={key === "category" ? 50 : 100}
                  />
                </label>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-400">
                Combine filters to narrow your inventory.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn-quiet"
                  onClick={resetFilters}
                >
                  Clear filters
                </button>
                <button className="btn-dark">
                  <Search size={16} aria-hidden="true" />
                  Search inventory
                </button>
              </div>
            </div>
            {filterError && (
              <div className="mt-4">
                <ErrorMessage message={filterError} />
              </div>
            )}
          </form>
        </section>
        {notice && (
          <div
            role="status"
            className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
          >
            {notice}
            <button
              className="icon-btn"
              aria-label="Dismiss notification"
              onClick={() => setNotice("")}
            >
              <X size={17} />
            </button>
          </div>
        )}
        {actionError && (
          <div className="mb-4">
            <ErrorMessage message={actionError} />
          </div>
        )}
        <section
          aria-label="Vehicle results"
          aria-busy={loading}
          className="overflow-hidden rounded-xl border border-slate-200 bg-white"
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 className="font-semibold">
              {filtered ? "Search results" : "All vehicles"}
              <span className="ml-2 rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-500">
                {loading ? "…" : (page?.total ?? 0)}
              </span>
            </h2>
            <button className="btn-quiet" onClick={reload} disabled={loading}>
              <RefreshCw size={15} aria-hidden="true" />
              Refresh
            </button>
          </div>
          {loading ? (
            <Loading label="Loading inventory…" />
          ) : error ? (
            <div className="space-y-4 p-6">
              <ErrorMessage message={error} />
              <button className="btn-secondary" onClick={reload}>
                Try again
              </button>
            </div>
          ) : !page?.items.length ? (
            <div className="px-6 py-16 text-center">
              <CarFront
                className="mx-auto mb-4 text-slate-300"
                size={44}
                aria-hidden="true"
              />
              <h3 className="font-semibold">
                {filtered
                  ? "No vehicles match your filters"
                  : "Your inventory starts here"}
              </h3>
              <p className="mb-5 mt-2 text-sm text-slate-500">
                {filtered
                  ? "Try a different make, category or price range."
                  : "Add your first vehicle to get your dealership moving."}
              </p>
              <button
                className="btn-secondary mx-auto"
                onClick={
                  filtered ? resetFilters : () => setDialog({ kind: "create" })
                }
              >
                {filtered ? "Reset filters" : "Add your first vehicle"}
              </button>
            </div>
          ) : (
            <>
              <div
                className="hidden grid-cols-[2fr_1fr_1fr_1fr_2fr] gap-4 bg-slate-50 px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500 xl:grid"
                aria-hidden="true"
              >
                <span>Vehicle</span>
                <span>Category</span>
                <span>Price</span>
                <span>Availability</span>
                <span className="text-right">Actions</span>
              </div>
              <ul className="divide-y divide-slate-100">
                {page.items.map((vehicle) => (
                  <li
                    key={vehicle.id}
                    aria-label={`${vehicle.make} ${vehicle.model}`}
                    className="grid items-center gap-4 px-5 py-5 sm:grid-cols-2 xl:grid-cols-[2fr_1fr_1fr_1fr_2fr]"
                  >
                    <div className="flex items-center gap-3">
                      <span className="grid size-12 shrink-0 place-items-center rounded-lg border border-slate-100 bg-stone-50 text-slate-500">
                        <CarFront
                          size={25}
                          strokeWidth={1.4}
                          aria-hidden="true"
                        />
                      </span>
                      <div>
                        <h3 className="font-semibold">
                          {vehicle.make} {vehicle.model}
                        </h3>
                        <p className="mt-1 text-[11px] text-slate-400">
                          ID · {vehicle.id.slice(0, 8).toUpperCase()}
                        </p>
                      </div>
                    </div>
                    <div>
                      <span className="rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600">
                        {vehicle.category}
                      </span>
                    </div>
                    <p className="text-sm font-semibold tabular-nums">
                      {priceLabel(vehicle.price)}
                    </p>
                    <div>
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${vehicle.quantity === 0 ? "bg-rose-50 text-rose-700" : vehicle.quantity <= 3 ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-700"}`}
                      >
                        <span className="size-1.5 rounded-full bg-current" />
                        {vehicle.quantity === 0
                          ? "Out of stock"
                          : `${vehicle.quantity} available`}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:col-span-2 xl:col-span-1 xl:justify-end">
                      <button
                        className="btn-buy"
                        disabled={vehicle.quantity === 0 || purchasing !== null}
                        onClick={() => purchase(vehicle)}
                        aria-label={`Purchase ${vehicle.make} ${vehicle.model}`}
                      >
                        <ShoppingCart size={14} aria-hidden="true" />
                        {purchasing === vehicle.id ? "Buying…" : "Buy 1"}
                      </button>
                      <button
                        className="icon-btn"
                        aria-label={`Edit ${vehicle.make} ${vehicle.model}`}
                        title="Edit vehicle"
                        onClick={() => setDialog({ kind: "edit", vehicle })}
                      >
                        <Pencil size={16} />
                      </button>
                      {isAdmin && (
                        <>
                          <button
                            className="icon-btn"
                            aria-label={`Restock ${vehicle.make} ${vehicle.model}`}
                            title="Restock"
                            onClick={() =>
                              setDialog({ kind: "restock", vehicle })
                            }
                          >
                            <PackagePlus size={17} />
                          </button>
                          <button
                            className="icon-btn text-red-600"
                            aria-label={`Delete ${vehicle.make} ${vehicle.model}`}
                            title="Delete vehicle"
                            onClick={() =>
                              setDialog({ kind: "delete", vehicle })
                            }
                          >
                            <Trash2 size={16} />
                          </button>
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-4">
                <p className="text-xs text-slate-500">
                  Showing {offset + 1}–{offset + page.items.length} of{" "}
                  {page.total} vehicles
                </p>
                <div className="flex items-center gap-3">
                  <button
                    className="icon-btn border border-slate-200"
                    aria-label="Previous page"
                    disabled={offset === 0}
                    onClick={() =>
                      setOffset((value) => Math.max(0, value - PAGE_SIZE))
                    }
                  >
                    <ChevronLeft size={17} />
                  </button>
                  <span className="text-xs text-slate-500">
                    Page {Math.floor(offset / PAGE_SIZE) + 1} of{" "}
                    {Math.ceil(page.total / PAGE_SIZE)}
                  </span>
                  <button
                    className="icon-btn border border-slate-200"
                    aria-label="Next page"
                    disabled={offset + PAGE_SIZE >= page.total}
                    onClick={() => setOffset((value) => value + PAGE_SIZE)}
                  >
                    <ChevronRight size={17} />
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
        <p className="mt-6 text-center text-xs text-slate-400">
          Stock is checked at purchase. Availability can change as your team
          works.
        </p>
      </main>
      {dialog && (
        <VehicleDialog
          action={dialog}
          close={() => setDialog(null)}
          save={save}
        />
      )}
    </div>
  );
}
