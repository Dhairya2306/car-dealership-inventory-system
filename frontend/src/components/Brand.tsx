import { CarFront } from "lucide-react";

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 ${light ? "text-white" : "text-slate-950"}`}
    >
      <span className="grid size-10 place-items-center rounded-xl bg-orange-500 text-white">
        <CarFront size={23} aria-hidden="true" />
      </span>
      <div>
        <span className="text-xl font-extrabold tracking-tight">
          Motor<span className="text-orange-500">desk</span>
        </span>
        <p
          className={`text-[10px] font-semibold uppercase tracking-[.2em] ${light ? "text-slate-400" : "text-slate-500"}`}
        >
          Dealership workspace
        </p>
      </div>
    </div>
  );
}
