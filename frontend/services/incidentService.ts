import { demoIncident } from '../data/demoIncident';

const delay = (ms = 120) => new Promise((resolve) => setTimeout(resolve, ms));

export type Position = [longitude: number, latitude: number];
export type SpillFeature = {
  type: 'Feature';
  properties: {
    incidentId: string;
    areaKm2: number;
    confidence: number;
    severity: string;
  };
  geometry: {
    type: 'Polygon' | 'MultiPolygon';
    coordinates: Position[][] | Position[][][];
  };
};

const closedPolygon = [
  ...demoIncident.spillPolygon,
  demoIncident.spillPolygon[0],
] as Position[];

// Stable frontend/backend contract. Replace this mock with the API response later.
export const demoSpillFeature: SpillFeature = {
  type: 'Feature',
  properties: {
    incidentId: demoIncident.id,
    areaKm2: demoIncident.areaKm2,
    confidence: demoIncident.detectionConfidence,
    severity: demoIncident.severity,
  },
  geometry: { type: 'Polygon', coordinates: [closedPolygon] },
};

export const incidentService = {
  async getIncident(id = '26143') {
    await delay();
    return id === demoIncident.id ? demoIncident : demoIncident;
  },
  async getSpill() {
    await delay();
    return demoSpillFeature;
  },
  async getVessels() {
    await delay();
    return demoIncident.vessels;
  },
  async getOrigin() {
    await delay();
    return demoIncident.origin;
  },
  async getForecast() {
    await delay();
    return demoIncident.forecast;
  },
  async getReplay() {
    await delay();
    return demoIncident.timeline;
  },
  async getAttribution(vesselId: string) {
    await delay();
    return (
      demoIncident.vessels.find((vessel) => vessel.id === vesselId) ??
      demoIncident.vessels[0]
    );
  },
};
