// Bounding-box based region detection — no external API needed

export type Country = "ZA" | "US" | "OTHER";

export interface RegionResult {
  country: Country;
  region: string; // Province (ZA) or State (US)
}

// ── South Africa provinces ──────────────────────────────────────────────────
const SA_PROVINCES: { name: string; minLat: number; maxLat: number; minLng: number; maxLng: number }[] = [
  { name: "Gauteng",            minLat: -26.8, maxLat: -25.4, minLng: 27.5,  maxLng: 29.2  },
  { name: "KwaZulu-Natal",      minLat: -31.1, maxLat: -26.8, minLng: 28.8,  maxLng: 32.9  },
  { name: "Western Cape",       minLat: -34.9, maxLat: -31.5, minLng: 17.8,  maxLng: 22.9  },
  { name: "Eastern Cape",       minLat: -34.1, maxLat: -30.6, minLng: 22.9,  maxLng: 30.1  },
  { name: "Limpopo",            minLat: -24.7, maxLat: -22.1, minLng: 26.5,  maxLng: 31.5  },
  { name: "Mpumalanga",         minLat: -27.0, maxLat: -24.6, minLng: 29.2,  maxLng: 32.8  },
  { name: "North West",         minLat: -27.8, maxLat: -24.3, minLng: 22.5,  maxLng: 28.0  },
  { name: "Free State",         minLat: -30.7, maxLat: -26.8, minLng: 24.3,  maxLng: 29.5  },
  { name: "Northern Cape",      minLat: -33.0, maxLat: -26.5, minLng: 16.4,  maxLng: 25.0  },
];

// ── US states (simplified bounding boxes) ──────────────────────────────────
const US_STATES: { name: string; minLat: number; maxLat: number; minLng: number; maxLng: number }[] = [
  { name: "Alabama",        minLat: 30.1,  maxLat: 35.0,  minLng: -88.5,  maxLng: -84.9  },
  { name: "Alaska",         minLat: 51.2,  maxLat: 71.5,  minLng: -180.0, maxLng: -129.0 },
  { name: "Arizona",        minLat: 31.3,  maxLat: 37.0,  minLng: -114.8, maxLng: -109.0 },
  { name: "Arkansas",       minLat: 33.0,  maxLat: 36.5,  minLng: -94.6,  maxLng: -89.6  },
  { name: "California",     minLat: 32.5,  maxLat: 42.0,  minLng: -124.5, maxLng: -114.1 },
  { name: "Colorado",       minLat: 36.9,  maxLat: 41.0,  minLng: -109.1, maxLng: -102.0 },
  { name: "Connecticut",    minLat: 40.9,  maxLat: 42.1,  minLng: -73.7,  maxLng: -71.8  },
  { name: "Delaware",       minLat: 38.4,  maxLat: 39.8,  minLng: -75.8,  maxLng: -75.0  },
  { name: "Florida",        minLat: 24.4,  maxLat: 31.0,  minLng: -87.6,  maxLng: -80.0  },
  { name: "Georgia",        minLat: 30.4,  maxLat: 35.0,  minLng: -85.6,  maxLng: -80.8  },
  { name: "Hawaii",         minLat: 18.9,  maxLat: 22.2,  minLng: -160.2, maxLng: -154.8 },
  { name: "Idaho",          minLat: 41.9,  maxLat: 49.0,  minLng: -117.2, maxLng: -111.0 },
  { name: "Illinois",       minLat: 36.9,  maxLat: 42.5,  minLng: -91.5,  maxLng: -87.0  },
  { name: "Indiana",        minLat: 37.8,  maxLat: 41.8,  minLng: -88.1,  maxLng: -84.8  },
  { name: "Iowa",           minLat: 40.4,  maxLat: 43.5,  minLng: -96.6,  maxLng: -90.1  },
  { name: "Kansas",         minLat: 36.9,  maxLat: 40.0,  minLng: -102.1, maxLng: -94.6  },
  { name: "Kentucky",       minLat: 36.5,  maxLat: 39.1,  minLng: -89.6,  maxLng: -81.9  },
  { name: "Louisiana",      minLat: 28.9,  maxLat: 33.0,  minLng: -94.0,  maxLng: -88.8  },
  { name: "Maine",          minLat: 43.1,  maxLat: 47.5,  minLng: -71.1,  maxLng: -66.9  },
  { name: "Maryland",       minLat: 37.9,  maxLat: 39.7,  minLng: -79.5,  maxLng: -75.0  },
  { name: "Massachusetts",  minLat: 41.2,  maxLat: 42.9,  minLng: -73.5,  maxLng: -69.9  },
  { name: "Michigan",       minLat: 41.7,  maxLat: 48.3,  minLng: -90.4,  maxLng: -82.4  },
  { name: "Minnesota",      minLat: 43.5,  maxLat: 49.4,  minLng: -97.2,  maxLng: -89.5  },
  { name: "Mississippi",    minLat: 30.2,  maxLat: 35.0,  minLng: -91.7,  maxLng: -88.1  },
  { name: "Missouri",       minLat: 35.9,  maxLat: 40.6,  minLng: -95.8,  maxLng: -89.1  },
  { name: "Montana",        minLat: 44.4,  maxLat: 49.0,  minLng: -116.1, maxLng: -104.0 },
  { name: "Nebraska",       minLat: 40.0,  maxLat: 43.0,  minLng: -104.1, maxLng: -95.3  },
  { name: "Nevada",         minLat: 35.0,  maxLat: 42.0,  minLng: -120.0, maxLng: -114.0 },
  { name: "New Hampshire",  minLat: 42.7,  maxLat: 45.3,  minLng: -72.6,  maxLng: -70.6  },
  { name: "New Jersey",     minLat: 38.9,  maxLat: 41.4,  minLng: -75.6,  maxLng: -73.9  },
  { name: "New Mexico",     minLat: 31.3,  maxLat: 37.0,  minLng: -109.1, maxLng: -103.0 },
  { name: "New York",       minLat: 40.5,  maxLat: 45.0,  minLng: -79.8,  maxLng: -71.9  },
  { name: "North Carolina", minLat: 33.8,  maxLat: 36.6,  minLng: -84.3,  maxLng: -75.5  },
  { name: "North Dakota",   minLat: 45.9,  maxLat: 49.0,  minLng: -104.1, maxLng: -96.6  },
  { name: "Ohio",           minLat: 38.4,  maxLat: 42.3,  minLng: -84.8,  maxLng: -80.5  },
  { name: "Oklahoma",       minLat: 33.6,  maxLat: 37.0,  minLng: -103.0, maxLng: -94.4  },
  { name: "Oregon",         minLat: 41.9,  maxLat: 46.3,  minLng: -124.6, maxLng: -116.5 },
  { name: "Pennsylvania",   minLat: 39.7,  maxLat: 42.3,  minLng: -80.5,  maxLng: -74.7  },
  { name: "Rhode Island",   minLat: 41.1,  maxLat: 42.0,  minLng: -71.9,  maxLng: -71.1  },
  { name: "South Carolina", minLat: 32.0,  maxLat: 35.2,  minLng: -83.4,  maxLng: -78.5  },
  { name: "South Dakota",   minLat: 42.5,  maxLat: 45.9,  minLng: -104.1, maxLng: -96.4  },
  { name: "Tennessee",      minLat: 34.9,  maxLat: 36.7,  minLng: -90.3,  maxLng: -81.6  },
  { name: "Texas",          minLat: 25.8,  maxLat: 36.5,  minLng: -106.6, maxLng: -93.5  },
  { name: "Utah",           minLat: 36.9,  maxLat: 42.0,  minLng: -114.1, maxLng: -109.0 },
  { name: "Vermont",        minLat: 42.7,  maxLat: 45.0,  minLng: -73.4,  maxLng: -71.5  },
  { name: "Virginia",       minLat: 36.5,  maxLat: 39.5,  minLng: -83.7,  maxLng: -75.2  },
  { name: "Washington",     minLat: 45.5,  maxLat: 49.0,  minLng: -124.7, maxLng: -116.9 },
  { name: "West Virginia",  minLat: 37.2,  maxLat: 40.6,  minLng: -82.6,  maxLng: -77.7  },
  { name: "Wisconsin",      minLat: 42.5,  maxLat: 47.1,  minLng: -92.9,  maxLng: -86.2  },
  { name: "Wyoming",        minLat: 40.9,  maxLat: 45.0,  minLng: -111.1, maxLng: -104.0 },
];

function inBox(lat: number, lng: number, b: typeof SA_PROVINCES[0]) {
  return lat >= b.minLat && lat <= b.maxLat && lng >= b.minLng && lng <= b.maxLng;
}

// SA bounding box
const SA_BOX = { minLat: -35.0, maxLat: -22.0, minLng: 16.0, maxLng: 33.0 };
// US bounding box (lower 48 + AK + HI)
const US_BOX = { minLat: 18.9, maxLat: 71.5, minLng: -180.0, maxLng: -66.9 };

export function detectRegion(lat: number, lng: number): RegionResult {
  if (inBox(lat, lng, SA_BOX)) {
    const province = SA_PROVINCES.find((p) => inBox(lat, lng, p));
    return { country: "ZA", region: province?.name ?? "South Africa" };
  }
  if (inBox(lat, lng, US_BOX)) {
    const state = US_STATES.find((s) => inBox(lat, lng, s));
    return { country: "US", region: state?.name ?? "United States" };
  }
  return { country: "OTHER", region: "International" };
}

export type BatteryType = "Motive.li" | "Advantage.li" | "Fridge.li" | "Unknown";

export function detectBatteryType(deviceName: string): BatteryType {
  const n = deviceName.toLowerCase();
  if (n.includes("motive")) return "Motive.li";
  if (n.includes("advantage")) return "Advantage.li";
  if (n.includes("fridge")) return "Fridge.li";
  return "Unknown";
}
