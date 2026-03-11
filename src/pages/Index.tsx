import { useCallback, useEffect, useRef, useState } from "react";
import { ApiConfig, DeviceLocation, FilterStatus } from "@/types/device";
import { fetchFleetLocations } from "@/lib/particle-api";
import FleetMap from "@/components/FleetMap";
import DeviceList from "@/components/DeviceList";
import StatsBar from "@/components/StatsBar";
import ApiConfigPanel from "@/components/ApiConfigPanel";
import FleetAnalytics from "@/components/FleetAnalytics";
import { Zap } from "lucide-react";

const REFRESH_INTERVAL = 60_000;
const STORAGE_KEY = "fleet-api-config";

function loadStoredConfig(): ApiConfig | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function Index() {
  const [devices, setDevices] = useState<DeviceLocation[]>([]);
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [search, setSearch] = useState("");
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiConfig, setApiConfig] = useState<ApiConfig | null>(loadStoredConfig);
  const [apiError, setApiError] = useState<string | undefined>();
  const [usingMock, setUsingMock] = useState(false);

  // Ref so the interval always sees the latest config without re-registering
  const apiConfigRef = useRef<ApiConfig | null>(apiConfig);
  apiConfigRef.current = apiConfig;

  const loadDevices = useCallback(async (config?: ApiConfig | null) => {
    const activeConfig = config !== undefined ? config : apiConfigRef.current;
    setLoading(true);
    try {
      const { devices: data, error } = await fetchFleetLocations(activeConfig ?? undefined);
      setDevices(data ?? []);
      setApiError(error);
      setUsingMock(!activeConfig?.url || !!error);
      setLastRefresh(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unexpected error";
      console.error("loadDevices crashed:", message);
      setApiError(message);
      setUsingMock(true);
      // Keep existing devices — don't blank the screen
    } finally {
      setLoading(false);
    }
  }, []);

  const handleConfigSave = (config: ApiConfig | null) => {
    setApiConfig(config);
    apiConfigRef.current = config;
    if (config) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    loadDevices(config);
  };

  useEffect(() => {
    loadDevices();
    const interval = setInterval(() => loadDevices(), REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [loadDevices]);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <header className="flex items-center gap-3 px-5 py-3 border-b border-border bg-card">
        <Zap className="w-5 h-5 text-primary" />
        <h1 className="text-base font-bold tracking-wide text-foreground">
          Maxwell &amp; Spark
        </h1>
        <span className="text-xs text-muted-foreground ml-2">Aftersale Fleet Map · B524 Devices</span>
        <button
          onClick={() => loadDevices()}
          disabled={loading}
          className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
        <ApiConfigPanel
          config={apiConfig}
          onSave={handleConfigSave}
          apiError={apiError}
          usingMock={usingMock}
        />
      </header>

      <div className="px-5 py-3">
        <StatsBar devices={devices} lastRefresh={lastRefresh} />
      </div>

      <div className="px-5 pb-3">
        <FleetAnalytics devices={devices} />
      </div>

      <div className="flex-1 flex gap-4 px-5 pb-5 min-h-0">
        <div className="w-80 shrink-0">
          <DeviceList
            devices={devices}
            filter={filter}
            onFilterChange={setFilter}
            search={search}
            onSearchChange={setSearch}
            selectedDeviceId={selectedDeviceId}
            onSelectDevice={setSelectedDeviceId}
          />
        </div>

        <div className="flex-1 rounded-lg border border-border overflow-hidden">
          <FleetMap
            devices={devices}
            selectedDeviceId={selectedDeviceId}
            onSelectDevice={setSelectedDeviceId}
          />
        </div>
      </div>
    </div>
  );
}
