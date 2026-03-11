import { useMemo, useState } from "react";
import { DeviceLocation } from "@/types/device";
import { detectRegion, detectBatteryType, BatteryType } from "@/lib/geo-regions";
import { BarChart3, Battery, MapPin, ChevronDown, ChevronUp } from "lucide-react";

interface Props {
  devices: DeviceLocation[];
}

const BATTERY_COLORS: Record<BatteryType, string> = {
  "Motive.li":    "bg-blue-500",
  "Advantage.li": "bg-emerald-500",
  "Fridge.li":    "bg-violet-500",
  "Unknown":      "bg-slate-500",
};

const BATTERY_TEXT: Record<BatteryType, string> = {
  "Motive.li":    "text-blue-400",
  "Advantage.li": "text-emerald-400",
  "Fridge.li":    "text-violet-400",
  "Unknown":      "text-slate-400",
};

const BATTERY_TYPES: BatteryType[] = ["Motive.li", "Advantage.li", "Fridge.li"];

type CountryTab = "ZA" | "US";

export default function FleetAnalytics({ devices }: Props) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<CountryTab>("ZA");

  const stats = useMemo(() => {
    // Per-battery totals
    const batteryTotals: Record<BatteryType, number> = {
      "Motive.li": 0, "Advantage.li": 0, "Fridge.li": 0, "Unknown": 0,
    };

    // Per-region breakdown: region -> batteryType -> count
    const zaRegions: Record<string, Record<BatteryType, number>> = {};
    const usRegions: Record<string, Record<BatteryType, number>> = {};

    for (const d of devices) {
      const battery = detectBatteryType(d.device_name);
      const { country, region } = detectRegion(d.latitude, d.longitude);

      batteryTotals[battery]++;

      if (country === "ZA") {
        if (!zaRegions[region]) zaRegions[region] = { "Motive.li": 0, "Advantage.li": 0, "Fridge.li": 0, "Unknown": 0 };
        zaRegions[region][battery]++;
      } else if (country === "US") {
        if (!usRegions[region]) usRegions[region] = { "Motive.li": 0, "Advantage.li": 0, "Fridge.li": 0, "Unknown": 0 };
        usRegions[region][battery]++;
      }
    }

    // Sort regions by total desc
    const sortRegions = (r: typeof zaRegions) =>
      Object.entries(r).sort(([, a], [, b]) => {
        const totalA = Object.values(a).reduce((s, v) => s + v, 0);
        const totalB = Object.values(b).reduce((s, v) => s + v, 0);
        return totalB - totalA;
      });

    return {
      batteryTotals,
      zaRegions: sortRegions(zaRegions),
      usRegions: sortRegions(usRegions),
    };
  }, [devices]);

  const activeRegions = tab === "ZA" ? stats.zaRegions : stats.usRegions;
  const regionLabel = tab === "ZA" ? "Province" : "State";
  const maxRegionTotal = Math.max(
    1,
    ...activeRegions.map(([, counts]) => Object.values(counts).reduce((s, v) => s + v, 0))
  );

  // Total for battery type bar widths
  const totalDevices = devices.length || 1;

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors"
      >
        <BarChart3 className="w-4 h-4 text-primary shrink-0" />
        <span className="text-sm font-bold tracking-wider uppercase text-foreground">
          Battery Analytics
        </span>

        {/* Mini battery pills always visible */}
        <div className="flex items-center gap-2 ml-3">
          {BATTERY_TYPES.map((bt) => (
            <span key={bt} className={`text-xs font-semibold ${BATTERY_TEXT[bt]}`}>
              {bt.replace(".li", "")} <span className="text-foreground">{stats.batteryTotals[bt]}</span>
            </span>
          ))}
        </div>

        <span className="ml-auto text-muted-foreground">
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {open && (
        <div className="border-t border-border p-4 space-y-5">

          {/* ── Battery type totals ── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Battery className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Battery Types — All Regions
              </span>
            </div>
            <div className="space-y-2">
              {BATTERY_TYPES.map((bt) => {
                const count = stats.batteryTotals[bt];
                const pct = Math.round((count / totalDevices) * 100);
                return (
                  <div key={bt} className="flex items-center gap-3">
                    <span className={`w-24 text-xs font-medium ${BATTERY_TEXT[bt]}`}>{bt}</span>
                    <div className="flex-1 bg-secondary rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${BATTERY_COLORS[bt]}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs font-bold text-foreground w-6 text-right">{count}</span>
                    <span className="text-xs text-muted-foreground w-8 text-right">{pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── Country tabs ── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                By {regionLabel}
              </span>
              <div className="ml-auto flex gap-1">
                {(["ZA", "US"] as CountryTab[]).map((c) => (
                  <button
                    key={c}
                    onClick={(e) => { e.stopPropagation(); setTab(c); }}
                    className={`text-xs px-2.5 py-1 rounded-md transition-colors ${
                      tab === c
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-secondary-foreground hover:bg-muted"
                    }`}
                  >
                    {c === "ZA" ? "🇿🇦 South Africa" : "🇺🇸 USA"}
                  </button>
                ))}
              </div>
            </div>

            {activeRegions.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">
                No devices detected in {tab === "ZA" ? "South Africa" : "the USA"} yet.
              </p>
            ) : (
              <div className="space-y-3">
                {activeRegions.map(([region, counts]) => {
                  const total = Object.values(counts).reduce((s, v) => s + v, 0);
                  const widthPct = Math.round((total / maxRegionTotal) * 100);
                  return (
                    <div key={region}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-foreground">{region}</span>
                        <span className="text-xs text-muted-foreground">{total} device{total !== 1 ? "s" : ""}</span>
                      </div>
                      {/* Stacked bar */}
                      <div className="w-full bg-secondary rounded-full h-3 overflow-hidden flex" style={{ maxWidth: "100%" }}>
                        {BATTERY_TYPES.map((bt) => {
                          const segPct = total > 0 ? (counts[bt] / maxRegionTotal) * 100 : 0;
                          return segPct > 0 ? (
                            <div
                              key={bt}
                              className={`h-full ${BATTERY_COLORS[bt]} transition-all`}
                              style={{ width: `${segPct}%` }}
                              title={`${bt}: ${counts[bt]}`}
                            />
                          ) : null;
                        })}
                      </div>
                      {/* Mini legend for this region */}
                      <div className="flex gap-3 mt-1">
                        {BATTERY_TYPES.filter((bt) => counts[bt] > 0).map((bt) => (
                          <span key={bt} className={`text-[10px] ${BATTERY_TEXT[bt]}`}>
                            {bt}: {counts[bt]}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
