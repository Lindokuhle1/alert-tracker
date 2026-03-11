import { DeviceLocation, FilterStatus } from "@/types/device";
import { formatDistanceToNow } from "date-fns";
import { Radio, Search, Signal, SignalZero, Wifi } from "lucide-react";

interface DeviceListProps {
  devices: DeviceLocation[];
  filter: FilterStatus;
  onFilterChange: (f: FilterStatus) => void;
  search: string;
  onSearchChange: (s: string) => void;
  selectedDeviceId: string | null;
  onSelectDevice: (id: string) => void;
}

export default function DeviceList({
  devices,
  filter,
  onFilterChange,
  search,
  onSearchChange,
  selectedDeviceId,
  onSelectDevice,
}: DeviceListProps) {
  const counts = {
    all: devices.length,
    online: devices.filter((d) => d.online).length,
    offline: devices.filter((d) => !d.online).length,
  };

  const filtered = devices
    .filter((d) => {
      if (filter === "online") return d.online;
      if (filter === "offline") return !d.online;
      return true;
    })
    .filter((d) =>
      d.device_name.toLowerCase().includes(search.toLowerCase()) ||
      d.device_id.toLowerCase().includes(search.toLowerCase())
    );

  return (
    <div className="flex flex-col h-full bg-card rounded-lg border border-border overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-3">
          <Radio className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-bold tracking-wider uppercase text-foreground">
            Fleet Devices
          </h2>
          <span className="ml-auto text-xs text-muted-foreground">{devices.length} total</span>
        </div>

        {/* Search */}
        <div className="relative mb-3">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search devices..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-secondary border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1">
          {(["all", "online", "offline"] as FilterStatus[]).map((f) => (
            <button
              key={f}
              onClick={() => onFilterChange(f)}
              className={`flex-1 text-xs py-1.5 rounded-md capitalize transition-colors ${
                filter === f
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-muted"
              }`}
            >
              {f} ({counts[f]})
            </button>
          ))}
        </div>
      </div>

      {/* Device list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-6 text-center text-muted-foreground text-xs">
            No devices found
          </div>
        ) : (
          filtered.map((d) => (
            <button
              key={d.device_id}
              onClick={() => onSelectDevice(d.device_id)}
              className={`w-full text-left p-3 border-b border-border transition-colors hover:bg-muted ${
                selectedDeviceId === d.device_id ? "bg-muted" : ""
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                {d.online ? (
                  <Wifi className="w-3.5 h-3.5 text-online shrink-0" />
                ) : (
                  <SignalZero className="w-3.5 h-3.5 text-offline shrink-0" />
                )}
                <span className="text-sm font-semibold text-foreground truncate">
                  {d.device_name}
                </span>
                <span
                  className={`status-dot shrink-0 ml-auto ${
                    d.online ? "status-online glow-green" : "status-offline"
                  }`}
                />
              </div>
              <div className="pl-5.5 text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(d.last_heard), { addSuffix: true })}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
