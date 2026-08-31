export type VectorFieldGrid = {
  bounds: [number, number, number, number];
  width: number;
  height: number;
  u: number[];
  v: number[];
  observedAt: string;
  source: string;
};
export type IncidentEnvironment = {
  wind: VectorFieldGrid | null;
  current: VectorFieldGrid | null;
};
const API_URL = process.env.NEXT_PUBLIC_API_URL;
export async function getIncidentEnvironment(
  incidentId: string,
): Promise<IncidentEnvironment> {
  if (!API_URL) return { wind: null, current: null };
  const response = await fetch(
    `${API_URL}/api/incidents/${incidentId}/environment`,
  );
  if (!response.ok) throw new Error('Environmental grid is unavailable');
  return response.json() as Promise<IncidentEnvironment>;
}
export function isValidVectorGrid(
  grid: VectorFieldGrid | null,
): grid is VectorFieldGrid {
  return Boolean(
    grid &&
    grid.width > 0 &&
    grid.height > 0 &&
    grid.u.length === grid.width * grid.height &&
    grid.v.length === grid.width * grid.height,
  );
}
