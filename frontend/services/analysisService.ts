export type GeoJSONGeometry = {
  type: 'Polygon' | 'MultiPolygon';
  coordinates: unknown[];
};
export type AnalysisGeometry = {
  has_oil: boolean;
  polygon: GeoJSONGeometry | null;
  area: number;
  centroid: [number, number] | null;
  bbox: [number, number, number, number] | null;
  perimeter: number;
  pixel_count: number;
  crs: string;
};
export type DriftPoint = { lon: number; lat: number; timestamp: string };
export type AnalysisCandidate = {
  vessel_id: string;
  overall_score: number;
  spatial_proximity: number;
  temporal_proximity: number;
  trajectory_consistency: number;
  heading_consistency: number;
  explanations: Record<string, string>;
};
export type ImageAnalysisResult = {
  detected: boolean;
  case: 'oil_spill' | 'no_oil_spill' | 'lookalike';
  message?: string;
  geometry?: AnalysisGeometry;
  drift?: {
    direction: string;
    trajectory: DriftPoint[];
    start_point: DriftPoint;
    end_point: DriftPoint;
    effective_velocity_m_s?: { vx: number; vy: number };
    duration_hours?: number;
    timestep_seconds?: number;
  };
  environment?: {
    wind_m_s: { u: number; v: number };
    current_m_s: { u: number; v: number };
    windage: number;
    source: string;
  };
  candidates?: AnalysisCandidate[];
  vessels?: Array<{
    id: string;
    name: string;
    position: [number, number];
    track: [number, number][];
    speed: number;
    heading: number;
    visualScore?: number;
  }>;
};

export async function checkBackend(signal?: AbortSignal) {
  const response = await fetch('/backend-api/api/v1/health', { signal });
  if (!response.ok) throw new Error('Backend is unavailable');
  return response.json();
}
