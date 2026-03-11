import { DeviceLocation } from "@/types/device";
import { Activity, Radio, Wifi, WifiOff } from "lucide-react";

interface StatsBarProps {
  devices: DeviceLocation[];
  lastRefresh: Date | null;
}

export default function StatsBar({ devices, lastRefresh }: StatsBarProps) {
  const online = devices.filter((d) => d.online).length;
  const offline = devices.length - online;

  const stats = [
    { icon: Radio, label: "Total", value: devices.length, color: "text-accent" },
    { icon: Wifi, label: "Online", value: online, color: "text-online" },
    { icon: WifiOff, label: "Offline", value: offline, color: "text-offline" },
    { icon: Activity, label: "GPS Lock", value: devices.filter((d) => d.gps_lock).length, color: "text-primary" },
  ];

  return (
    <div className="flex items-center gap-6 px-4 py-2.5 bg-card border border-border rounded-lg">
      {stats.map((s) => (
        <div key={s.label} className="flex items-center gap-2">
          <s.icon className={`w-4 h-4 ${s.color}`} />
          <span className="text-xs text-muted-foreground">{s.label}</span>
          <span className="text-sm font-bold text-foreground">{s.value}</span>
        </div>
      ))}
      {lastRefresh && (
        <span className="ml-auto text-xs text-muted-foreground">
          Auto-refresh: 60s
        </span>
      )}
    </div>
  );
}
