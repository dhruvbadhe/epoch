"use client";
import { useState } from "react";
import { Info, RotateCcw, Save } from "lucide-react";
import type { Config, Overrides } from "@/lib/types";
import { Drawer } from "./Drawer";
import { cropLabel } from "@/lib/format";
interface EditableField {
  path: string;
  label: string;
  unit: string;
  min?: number;
  max?: number;
  step?: number;
}
const groups: { title: string; fields: EditableField[] }[] = [
  {
    title: "Individual transport",
    fields: [
      {
        path: "transport.rate_per_km_per_qtl",
        label: "Transport rate",
        unit: "₹ / km / quintal",
        step: 0.1,
      },
      {
        path: "transport.loading_per_qtl",
        label: "Loading charge",
        unit: "₹ / quintal",
      },
      {
        path: "transport.road_factor",
        label: "Road distance multiplier",
        unit: "× straight-line distance",
        step: 0.1,
        min: 1,
      },
    ],
  },
  {
    title: "Spoilage & storage",
    fields: [
      ...(["onion", "tomato", "soybean"] as const).flatMap((crop) => [
        {
          path: `spoilage_per_day.${crop}`,
          label: `${cropLabel(crop)} daily spoilage`,
          unit: "share of weight / day",
          step: 0.001,
          max: 0.99,
        },
        {
          path: `storage_cost_per_qtl_per_day.${crop}`,
          label: `${cropLabel(crop)} storage`,
          unit: "₹ / quintal / day",
          step: 0.1,
        },
      ]),
      { path: "fees_per_qtl", label: "Mandi fees", unit: "₹ / quintal" },
    ],
  },
  {
    title: "Shared trucks & capacity",
    fields: [
      {
        path: "fpo.first_mile_per_qtl",
        label: "Member → collection centre",
        unit: "₹ / quintal",
      },
      {
        path: "fpo.truck_capacity_qtl",
        label: "Truck capacity",
        unit: "quintals",
        min: 1,
      },
      {
        path: "fpo.truck_fixed_cost",
        label: "Fixed truck cost",
        unit: "₹ / trip",
      },
      {
        path: "fpo.truck_per_km",
        label: "Truck distance cost",
        unit: "₹ / km",
      },
      {
        path: "fpo.mandi_cap_qtl_per_day",
        label: "Mandi daily capacity",
        unit: "quintals / day",
        min: 1,
      },
    ],
  },
  {
    title: "Hold decision",
    fields: [
      {
        path: "hold_rule.min_gain_per_qtl",
        label: "Minimum gain from waiting",
        unit: "₹ / quintal",
      },
      {
        path: "hold_rule.max_downside_per_qtl",
        label: "Maximum downside",
        unit: "₹ / quintal",
      },
    ],
  },
];
function read(config: Config, path: string): number {
  return path
    .split(".")
    .reduce(
      (o, key) => (o as Record<string, unknown>)[key],
      config as unknown,
    ) as number;
}
function set(config: Config, path: string, value: number) {
  const keys = path.split(".");
  const parent = keys
    .slice(0, -1)
    .reduce(
      (o, key) => (o as Record<string, unknown>)[key],
      config as unknown,
    ) as Record<string, unknown>;
  parent[keys.at(-1)!] = value;
}
export function AssumptionsDrawer({
  defaults,
  current,
  onApply,
  onClose,
}: {
  defaults: Config;
  current: Overrides;
  onApply: (value: Overrides) => void;
  onClose: () => void;
}) {
  const [values, setValues] = useState<Config>(() => {
    const value = structuredClone(defaults);
    for (const group of groups)
      for (const field of group.fields) {
        const override = field.path
          .split(".")
          .reduce<unknown>(
            (o, key) =>
              o && typeof o === "object"
                ? (o as Record<string, unknown>)[key]
                : undefined,
            current,
          );
        if (typeof override === "number") set(value, field.path, override);
      }
    return value;
  });
  const [invalid, setInvalid] = useState<string[]>([]);
  const apply = () => {
    const patch: Record<string, unknown> = {};
    for (const group of groups)
      for (const field of group.fields) {
        const value = read(values, field.path);
        if (value !== read(defaults, field.path)) {
          const keys = field.path.split(".");
          let part = patch;
          for (const key of keys.slice(0, -1)) {
            part[key] ??= {};
            part = part[key] as Record<string, unknown>;
          }
          part[keys.at(-1)!] = value;
        }
      }
    onApply(Object.keys(patch).length ? (patch as Overrides) : null);
    onClose();
  };
  return (
    <Drawer
      title="Every assumption, in the open."
      subtitle="These values change Advice and FPO Plan. Evidence always uses the defaults."
      onClose={onClose}
      footer={
        <>
          <button
            className="button secondary"
            onClick={() => {
              setValues(structuredClone(defaults));
              setInvalid([]);
            }}
          >
            <RotateCcw size={15} />
            Reset to defaults
          </button>
          <button
            className="button primary"
            disabled={invalid.length > 0}
            onClick={apply}
          >
            <Save size={15} />
            Apply assumptions
          </button>
        </>
      }
    >
      <div className="notice warning">
        <Info size={18} />
        Placeholder values until a mentor confirms them. Review these for your
        local conditions.
      </div>
      {groups.map((group) => (
        <section className="assumption-group" key={group.title}>
          <h3>{group.title}</h3>
          {group.fields.map((field) => (
            <div className="assumption-field" key={field.path}>
              <label htmlFor={field.path}>
                {field.label}
                <span>{field.unit} · assumption</span>
              </label>
              <input
                id={field.path}
                type="number"
                defaultValue={undefined}
                value={
                  Number.isNaN(read(values, field.path))
                    ? ""
                    : read(values, field.path)
                }
                min={field.min ?? 0}
                max={field.max}
                step={field.step ?? 1}
                aria-invalid={invalid.includes(field.path)}
                onChange={(e) => {
                  const raw = e.target.value;
                  const value = raw === "" ? NaN : Number(raw);
                  const valid =
                    raw !== "" &&
                    Number.isFinite(value) &&
                    value >= (field.min ?? 0) &&
                    (field.max === undefined || value <= field.max);
                  setInvalid((items) =>
                    valid
                      ? items.filter((i) => i !== field.path)
                      : [...new Set([...items, field.path])],
                  );
                  setValues((v) => {
                    const next = structuredClone(v);
                    set(next, field.path, value);
                    return next;
                  });
                }}
              />
            </div>
          ))}
        </section>
      ))}
      {invalid.length > 0 && (
        <p className="field-error" role="alert">
          Enter valid values within the displayed input limits before applying.
        </p>
      )}
    </Drawer>
  );
}
