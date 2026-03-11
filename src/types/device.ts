export interface ApiGroup {
  id: string;
  name: string;
  url: string;
  token?: string;
  enabled: boolean;
}

export interface ApiConfig {
  url: string;
  token?: string;
  groups?: ApiGroup[];
}

export interface DeviceLocation {
  device_id: string;
  device_name: string;
  latitude: number;
  longitude: number;
  online: boolean;
  last_heard: string;
  gps_lock?: boolean;
  horizontal_accuracy?: number;
  product_id?: number;
  sources?: string[];
}

export interface ParticleApiResponse {
  locations: Array<{
    device_id: string;
    geometry: {
      type: string;
      coordinates: [number, number]; // [lng, lat]
    };
    sources: string[];
    horizontal_accuracy: number;
    product_id: number;
    last_heard: string;
    gps_lock: boolean;
    updatedAt: string;
    device_name: string;
    online: boolean;
  }>;
}

export type FilterStatus = "all" | "online" | "offline";
