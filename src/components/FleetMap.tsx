import { useEffect, useRef, useCallback } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { DeviceLocation } from "@/types/device";
import { detectRegion, detectBatteryType, BatteryType } from "@/lib/geo-regions";
import { formatDistanceToNow } from "date-fns";

interface FleetMapProps {
  devices: DeviceLocation[];
  selectedDeviceId?: string | null;
  onSelectDevice?: (id: string) => void;
}

// ── Zoom thresholds ──────────────────────────────────────────────────────────
const CLUSTER_ZOOM = 7;   // below this → region clusters
const DETAIL_ZOOM  = 10;  // at or above this → full individual markers

// ── Battery colours ──────────────────────────────────────────────────────────
const BATTERY_COLOR: Record<BatteryType, string> = {
  "Motive.li":    "#3b82f6",
  "Advantage.li": "#10b981",
  "Fridge.li":    "#8b5cf6",
  "Unknown":      "#64748b",
};

// ── Individual device marker ─────────────────────────────────────────────────
function createDeviceIcon(device: DeviceLocation, selected = false) {
  const battery = detectBatteryType(device.device_name);
  const color   = BATTERY_COLOR[battery];
  const ring    = selected ? `stroke="#fff" stroke-width="2.5"` : `stroke="${color}" stroke-width="1.5"`;
  const size    = selected ? 34 : 28;
  const r       = size / 2;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${r}" cy="${r}" r="${r - 2}" fill="${color}" fill-opacity="0.2" ${ring}/>
    <circle cx="${r}" cy="${r}" r="${r * 0.35}" fill="${color}" opacity="${device.online ? 1 : 0.4}"/>
    ${!device.online ? `<line x1="${r*0.6}" y1="${r*0.6}" x2="${r*1.4}" y2="${r*1.4}" stroke="${color}" stroke-width="1.5" opacity="0.7"/>` : ""}
  </svg>`;

  return L.divIcon({
    html: svg,
    className: "",
    iconSize:   [size, size],
    iconAnchor: [r, r],
    popupAnchor:[0, -r],
  });
}

// ── Region cluster marker ────────────────────────────────────────────────────
function createClusterIcon(
  region: string,
  total: number,
  counts: Record<BatteryType, number>,
  country: string
) {
  const TYPES: BatteryType[] = ["Motive.li", "Advantage.li", "Fridge.li", "Unknown"];
  const radius = Math.min(48, 28 + Math.sqrt(total) * 3);
  const cx = radius + 4;
  const cy = radius + 24; // extra top space for label
  const r  = radius;

  // Donut segments
  const nonZero = TYPES.filter((t) => counts[t] > 0);
  let segments = "";
  if (nonZero.length === 1) {
    // Full circle
    segments = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${BATTERY_COLOR[nonZero[0]]}" fill-opacity="0.85"/>`;
  } else {
    let startAngle = -Math.PI / 2;
    nonZero.forEach((bt) => {
      const slice  = (counts[bt] / total) * 2 * Math.PI;
      const endAngle = startAngle + slice;
      const x1 = cx + r * Math.cos(startAngle);
      const y1 = cy + r * Math.sin(startAngle);
      const x2 = cx + r * Math.cos(endAngle);
      const y2 = cy + r * Math.sin(endAngle);
      const large = slice > Math.PI ? 1 : 0;
      segments += `<path d="M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2} Z"
        fill="${BATTERY_COLOR[bt]}" fill-opacity="0.85"/>`;
      startAngle = endAngle;
    });
  }

  // Inner dark circle
  const inner = r * 0.6;
  const flag  = country === "ZA" ? "🇿🇦" : country === "US" ? "🇺🇸" : "🌍";
  const shortRegion = region.length > 12 ? region.slice(0, 11) + "…" : region;
  const w = (cx + r + 4) * 2;
  const h = cy + r + 4;

  const html = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    ${segments}
    <circle cx="${cx}" cy="${cy}" r="${inner}" fill="#0f172a"/>
    <text x="${cx}" y="${cy - 4}" text-anchor="middle" fill="white" font-size="11" font-weight="700" font-family="monospace">${total}</text>
    <text x="${cx}" y="${cy + 8}" text-anchor="middle" fill="#94a3b8" font-size="7" font-family="sans-serif">${flag}</text>
    <text x="${cx}" y="${h - 6}" text-anchor="middle" fill="#cbd5e1" font-size="8" font-weight="600" font-family="sans-serif">${shortRegion}</text>
  </svg>`;

  return L.divIcon({
    html,
    className: "",
    iconSize:   [w, h],
    iconAnchor: [cx, cy],
    popupAnchor:[0, -(r + 4)],
  });
}

// ── Cluster popup HTML ────────────────────────────────────────────────────────
function clusterPopupHtml(
  region: string,
  country: string,
  total: number,
  counts: Record<BatteryType, number>,
  online: number
) {
  const TYPES: BatteryType[] = ["Motive.li", "Advantage.li", "Fridge.li"];
  const rows = TYPES.filter((t) => counts[t] > 0)
    .map((t) => `<div style="display:flex;justify-content:space-between;gap:16px;margin-bottom:3px">
      <span style="color:${BATTERY_COLOR[t]};font-weight:600">${t}</span>
      <span style="color:#e2e8f0">${counts[t]}</span>
    </div>`)
    .join("");

  return `<div style="font-family:sans-serif;font-size:12px;color:#e2e8f0;background:#1e293b;padding:12px 14px;border-radius:8px;min-width:180px;border:1px solid #334155">
    <div style="font-size:13px;font-weight:700;margin-bottom:8px;color:#f1f5f9">${region}</div>
    <div style="color:#64748b;font-size:10px;margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em">${country === "ZA" ? "SA Province" : country === "US" ? "US State" : "Region"}</div>
    ${rows}
    <div style="border-top:1px solid #334155;margin-top:8px;padding-top:6px;display:flex;justify-content:space-between">
      <span style="color:#94a3b8">Total</span><span style="font-weight:700">${total}</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:3px">
      <span style="color:#34d399">Online</span><span style="color:#34d399">${online}</span>
    </div>
    <div style="margin-top:6px;color:#64748b;font-size:10px">Zoom in to see individual devices</div>
  </div>`;
}

// ── Component ────────────────────────────────────────────────────────────────
export default function FleetMap({ devices, selectedDeviceId, onSelectDevice }: FleetMapProps) {
  const mapRef       = useRef<L.Map | null>(null);
  const layerRef     = useRef<L.LayerGroup | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const devicesRef   = useRef(devices);
  const onSelectRef  = useRef(onSelectDevice);
  devicesRef.current  = devices;
  onSelectRef.current = onSelectDevice;

  // ── Render markers for current zoom ────────────────────────────────────────
  const renderMarkers = useCallback((zoom: number, devs: DeviceLocation[]) => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.clearLayers();

    if (zoom < CLUSTER_ZOOM) {
      // ── Region cluster view ──────────────────────────────────────────────
      type RegionKey = string;
      const regionMap = new Map<RegionKey, {
        devices: DeviceLocation[];
        counts: Record<BatteryType, number>;
        online: number;
        sumLat: number;
        sumLng: number;
        country: string;
        region: string;
      }>();

      devs.forEach((d) => {
        const { country, region } = detectRegion(d.latitude, d.longitude);
        const key = `${country}::${region}`;
        if (!regionMap.has(key)) {
          regionMap.set(key, {
            devices: [],
            counts: { "Motive.li": 0, "Advantage.li": 0, "Fridge.li": 0, "Unknown": 0 },
            online: 0, sumLat: 0, sumLng: 0, country, region,
          });
        }
        const entry = regionMap.get(key)!;
        const bt = detectBatteryType(d.device_name);
        entry.devices.push(d);
        entry.counts[bt]++;
        if (d.online) entry.online++;
        entry.sumLat += d.latitude;
        entry.sumLng += d.longitude;
      });

      regionMap.forEach((entry) => {
        const total = entry.devices.length;
        const lat   = entry.sumLat / total;
        const lng   = entry.sumLng / total;

        const marker = L.marker([lat, lng], {
          icon: createClusterIcon(entry.region, total, entry.counts, entry.country),
          zIndexOffset: 100,
        });

        marker.bindPopup(
          clusterPopupHtml(entry.region, entry.country, total, entry.counts, entry.online),
          { className: "fleet-popup", closeButton: false }
        );

        // Click cluster → zoom into it
        marker.on("click", () => {
          mapRef.current?.flyTo([lat, lng], CLUSTER_ZOOM + 1, { duration: 0.7 });
        });

        marker.addTo(layer);
      });

    } else {
      // ── Individual device view ─────────────────────────────────────────────
      devs.forEach((d) => {
        const selected = d.device_id === selectedDeviceId; // captured via closure update below
        const marker = L.marker([d.latitude, d.longitude], {
          icon: createDeviceIcon(d, selected),
          zIndexOffset: selected ? 1000 : 0,
        });

        const timeAgo = formatDistanceToNow(new Date(d.last_heard), { addSuffix: true });
        const bt      = detectBatteryType(d.device_name);
        const color   = BATTERY_COLOR[bt];

        marker.bindPopup(
          `<div style="font-family:sans-serif;font-size:12px;color:#e2e8f0;background:#1e293b;padding:12px;border-radius:8px;min-width:200px;border:1px solid #334155">
            <div style="font-size:13px;font-weight:700;margin-bottom:6px;color:${d.online ? "#34d399" : "#ef4444"}">${d.device_name}</div>
            <div style="display:inline-block;padding:2px 8px;border-radius:999px;background:${color}22;color:${color};font-size:10px;font-weight:600;margin-bottom:8px">${bt}</div>
            <div style="color:#94a3b8;margin-bottom:3px"><b>ID:</b> ${d.device_id.slice(0, 14)}…</div>
            <div style="color:#94a3b8;margin-bottom:3px"><b>Last heard:</b> ${timeAgo}</div>
            <div style="color:#94a3b8;margin-bottom:3px"><b>GPS lock:</b> ${d.gps_lock ? "✅" : "❌"}</div>
            <div style="color:#94a3b8"><b>Accuracy:</b> ${d.horizontal_accuracy ?? "N/A"}m</div>
          </div>`,
          { className: "fleet-popup", closeButton: false }
        );

        marker.on("click", () => onSelectRef.current?.(d.device_id));
        marker.addTo(layer);
      });
    }
  }, [selectedDeviceId]);

  // ── Init map ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, { zoomControl: false }).setView([-28.5, 27], 6);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; OSM &copy; CARTO',
      maxZoom: 19,
    }).addTo(map);

    const layer = L.layerGroup().addTo(map);
    layerRef.current = layer;
    mapRef.current   = map;

    // Re-render on zoom change
    map.on("zoomend", () => {
      renderMarkers(map.getZoom(), devicesRef.current);
    });

    return () => {
      map.remove();
      mapRef.current  = null;
      layerRef.current = null;
    };
  }, [renderMarkers]);

  // ── Re-render when devices change ──────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current) return;
    renderMarkers(mapRef.current.getZoom(), devices);

    if (devices.length > 0 && !selectedDeviceId) {
      const bounds = L.latLngBounds(devices.map((d) => [d.latitude, d.longitude]));
      mapRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
    }
  }, [devices, renderMarkers, selectedDeviceId]);

  // ── Re-render when selection changes (to update selected icon) ─────────────
  useEffect(() => {
    if (!mapRef.current) return;
    renderMarkers(mapRef.current.getZoom(), devicesRef.current);

    if (selectedDeviceId) {
      const device = devicesRef.current.find((d) => d.device_id === selectedDeviceId);
      if (device) mapRef.current.flyTo([device.latitude, device.longitude], Math.max(mapRef.current.getZoom(), DETAIL_ZOOM), { duration: 0.8 });
    }
  }, [selectedDeviceId, renderMarkers]);

  return <div ref={containerRef} className="w-full h-full rounded-lg overflow-hidden" />;
}
