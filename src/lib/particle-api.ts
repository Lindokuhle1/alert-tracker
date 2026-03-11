import { ApiConfig, DeviceLocation, ParticleApiResponse } from "@/types/device";

const MOCK_DATA: ParticleApiResponse = {
  locations: [
    {
      device_id: "e00fce68010994e69d129bb2",
      geometry: { type: "Point", coordinates: [30.83599, -29.81477] },
      sources: ["cell_vitals"],
      horizontal_accuracy: 968,
      product_id: 17554,
      last_heard: "2025-09-23T09:06:14.000Z",
      gps_lock: false,
      updatedAt: "2025-09-23T09:06:14.658Z",
      device_name: "Motive.li-52090939",
      online: false,
    },
    {
      device_id: "a10fce68020114e69d229cc3",
      geometry: { type: "Point", coordinates: [28.0473, -26.2041] },
      sources: ["gps"],
      horizontal_accuracy: 15,
      product_id: 17554,
      last_heard: "2025-09-23T10:15:30.000Z",
      gps_lock: true,
      updatedAt: "2025-09-23T10:15:30.000Z",
      device_name: "Advantage.li-JHB-01",
      online: true,
    },
    {
      device_id: "b20fce68030224e69d339dd4",
      geometry: { type: "Point", coordinates: [18.4241, -33.9249] },
      sources: ["cell_vitals"],
      horizontal_accuracy: 500,
      product_id: 17554,
      last_heard: "2025-09-22T18:45:00.000Z",
      gps_lock: false,
      updatedAt: "2025-09-22T18:45:00.000Z",
      device_name: "Fridge.li-CPT-03",
      online: false,
    },
  ],
};

function transformResponse(raw: unknown): DeviceLocation[] {
  try {
    // Handle multiple possible shapes: { locations: [] } or just []
    let locations: unknown[];
    if (Array.isArray(raw)) {
      locations = raw;
    } else if (raw && typeof raw === "object" && Array.isArray((raw as any).locations)) {
      locations = (raw as any).locations;
    } else if (raw && typeof raw === "object" && Array.isArray((raw as any).data)) {
      locations = (raw as any).data;
    } else if (raw && typeof raw === "object" && Array.isArray((raw as any).devices)) {
      locations = (raw as any).devices;
    } else {
      console.warn("Unexpected API shape:", JSON.stringify(raw).slice(0, 200));
      return [];
    }

    return locations
      .map((loc: any) => {
        try {
          // Support both geometry.coordinates and flat lat/lng fields
          let latitude: number;
          let longitude: number;

          if (loc.geometry?.coordinates) {
            longitude = loc.geometry.coordinates[0];
            latitude = loc.geometry.coordinates[1];
          } else if (loc.lat != null && loc.lng != null) {
            latitude = loc.lat;
            longitude = loc.lng;
          } else if (loc.latitude != null && loc.longitude != null) {
            latitude = loc.latitude;
            longitude = loc.longitude;
          } else {
            return null; // skip devices with no location
          }

          return {
            device_id: String(loc.device_id ?? loc.id ?? "unknown"),
            device_name: String(loc.device_name ?? loc.name ?? loc.device_id ?? "Unknown"),
            latitude,
            longitude,
            online: Boolean(loc.online ?? loc.connected ?? false),
            last_heard: String(loc.last_heard ?? loc.lastHeard ?? loc.updatedAt ?? new Date().toISOString()),
            gps_lock: Boolean(loc.gps_lock ?? loc.gpsLock ?? false),
            horizontal_accuracy: Number(loc.horizontal_accuracy ?? loc.accuracy ?? 0),
            product_id: loc.product_id ?? loc.productId,
            sources: loc.sources ?? [],
          } as DeviceLocation;
        } catch {
          return null;
        }
      })
      .filter((d): d is DeviceLocation => d !== null);
  } catch (err) {
    console.error("transformResponse failed:", err);
    return [];
  }
}

export async function fetchFleetLocations(
  config?: ApiConfig
): Promise<{ devices: DeviceLocation[]; error?: string }> {

  // ── Multi-group mode ──────────────────────────────────────────────────────
  const groups = config?.groups?.filter((g) => g.enabled && g.url.trim());
  if (groups && groups.length > 0) {
    const results = await Promise.allSettled(
      groups.map(async (g) => {
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (g.token) headers["Authorization"] = `Bearer ${g.token}`;
        const res = await fetch(g.url, { headers });
        if (!res.ok) throw new Error(`${g.name}: HTTP ${res.status}`);
        const text = await res.text();
        let raw: unknown;
        try { raw = JSON.parse(text); } catch { throw new Error(`${g.name}: invalid JSON`); }
        return transformResponse(raw);
      })
    );

    const allDevices: DeviceLocation[] = [];
    const errors: string[] = [];
    results.forEach((r, i) => {
      if (r.status === "fulfilled") allDevices.push(...r.value);
      else errors.push(r.reason?.message ?? `Group ${i + 1} failed`);
    });

    if (allDevices.length > 0) {
      return { devices: allDevices, error: errors.length ? errors.join(" | ") : undefined };
    }
    return { devices: transformResponse(MOCK_DATA), error: errors.join(" | ") };
  }

  // ── Single URL mode (legacy) ──────────────────────────────────────────────
  if (config?.url) {
    try {
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (config.token) headers["Authorization"] = `Bearer ${config.token}`;
      const res = await fetch(config.url, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const text = await res.text();
      let raw: unknown;
      try { raw = JSON.parse(text); } catch { throw new Error(`Response is not valid JSON. Got: ${text.slice(0, 100)}`); }
      const devices = transformResponse(raw);
      if (devices.length === 0) {
        const shape = Object.keys(raw as object ?? {}).join(", ") || typeof raw;
        return { devices: transformResponse(MOCK_DATA), error: `API returned 0 usable devices. Response keys: { ${shape} }` };
      }
      return { devices };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { devices: transformResponse(MOCK_DATA), error: message };
    }
  }

  return { devices: transformResponse(MOCK_DATA) };
}
