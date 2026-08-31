export type Coordinate = [number, number];
export type EvidenceFactor = {
  label: string;
  value: number;
  status: 'match' | 'warning';
};
export type VesselRecord = {
  id: string;
  name: string;
  type: string;
  distanceKm: number;
  score: number;
  position: Coordinate;
  speed: number;
  heading: number;
  color: string;
  track: Coordinate[];
  evidence: EvidenceFactor[];
};

export const demoIncident = {
  id: '26143',
  caseId: 'OF-26143',
  detectedAt: '27 Aug 2026 · 04:32 IST',
  location: 'Bay of Bengal · Sector 04',
  center: [83.6685, 17.5368] as Coordinate,
  areaKm2: 12.84,
  perimeterKm: 19.6,
  detectionConfidence: 94,
  severity: 'High',
  estimatedAge: '8–11 hours',
  currentDirection: 'ESE · 112°',
  origin: {
    coordinate: [83.5574, 17.4912] as Coordinate,
    confidence: 81,
    time: '26 Aug 2026 · 20:18 IST',
    radiusKm: 2.1,
  },
  spillPolygon: [
    [83.63, 17.553],
    [83.645, 17.561],
    [83.674, 17.55],
    [83.705, 17.53],
    [83.722, 17.509],
    [83.699, 17.502],
    [83.668, 17.519],
    [83.642, 17.532],
    [83.63, 17.553],
  ] as Coordinate[],
  spillHeat: [
    [83.637, 17.554, 0.46],
    [83.647, 17.549, 0.62],
    [83.657, 17.543, 0.8],
    [83.6685, 17.5368, 1],
    [83.678, 17.531, 0.92],
    [83.688, 17.525, 0.78],
    [83.699, 17.518, 0.55],
    [83.664, 17.528, 0.75],
    [83.679, 17.539, 0.7],
    [83.651, 17.533, 0.58],
  ] as [number, number, number][],
  forecast: [
    {
      hour: 0,
      label: 'NOW',
      center: [83.6685, 17.5368] as Coordinate,
      areaKm2: 12.84,
      confidence: 94,
    },
    {
      hour: 2,
      label: '+2H',
      center: [83.692, 17.527] as Coordinate,
      areaKm2: 14.1,
      confidence: 89,
    },
    {
      hour: 4,
      label: '+4H',
      center: [83.719, 17.515] as Coordinate,
      areaKm2: 16.8,
      confidence: 84,
    },
    {
      hour: 6,
      label: '+6H',
      center: [83.751, 17.501] as Coordinate,
      areaKm2: 20.3,
      confidence: 78,
    },
  ],
  environment: {
    wind: { direction: 118, speedKmh: 21 },
    current: { direction: 104, speedKnots: 1.4 },
  },
  coastalRisk: {
    level: 'Moderate',
    nearestCoast: 'Andhra Pradesh coastline',
    distanceKm: 46,
    estimatedArrival: '18–24 hours',
    sensitiveArea: 'Kakinada coastal wetlands',
    projectedAreaKm2: 28.6,
    confidence: 76,
  },
  impactAssessment: {
    estimatedVolume: {
      minTonnes: 820,
      maxTonnes: 1450,
      confidence: 58,
      basis: 'Surface area with a demonstration slick-thickness range',
    },
    marineVegetation: {
      risk: 'High',
      exposedAreaKm2: 6.8,
      concern: 'Seagrass and near-shore phytoplankton exposure',
    },
    marineLife: {
      risk: 'High',
      groups: ['Seabirds', 'Juvenile fish', 'Plankton', 'Shellfish'],
      concern: 'Acute surface exposure and food-web contamination',
    },
    shoreline: {
      exposureKm: 14.2,
      arrivalWindow: '18–24 hours',
    },
    recovery: {
      surface: 'Weeks to months',
      coastalHabitat: '2–5 years',
      sensitiveHabitat: '5+ years',
    },
    responsePriority: 'Immediate containment and shoreline protection',
  },
  timeline: [
    { value: 0, label: 'T−12H', event: 'Vessels enter investigation window' },
    {
      value: 22,
      label: 'T−8H',
      event: 'Candidate routes converge near origin',
    },
    { value: 43, label: 'T−4H', event: 'Probable discharge event' },
    { value: 58, label: 'T−2H', event: 'Early slick drift detected' },
    { value: 72, label: 'NOW', event: 'Satellite spill detection' },
    { value: 82, label: '+2H', event: 'Short-range spread forecast' },
    { value: 91, label: '+4H', event: 'Forecast region expands eastward' },
    { value: 100, label: '+6H', event: 'Six-hour forecast complete' },
  ],
  vessels: [
    {
      id: 'IMO 9387421',
      name: 'MV Ocean Star',
      type: 'Crude oil tanker',
      distanceKm: 3.3,
      score: 87,
      position: [83.72, 17.49] as Coordinate,
      speed: 11.8,
      heading: 126,
      color: '#38bdf8',
      track: [
        [83.53, 17.64],
        [83.58, 17.6],
        [83.62, 17.57],
        [83.6685, 17.5368],
        [83.72, 17.49],
        [83.79, 17.44],
      ] as Coordinate[],
      evidence: [
        { label: 'Spatial proximity', value: 92, status: 'match' as const },
        { label: 'Temporal match', value: 88, status: 'match' as const },
        { label: 'Trajectory match', value: 86, status: 'match' as const },
        { label: 'Origin consistency', value: 91, status: 'match' as const },
        { label: 'Behavioral anomaly', value: 72, status: 'warning' as const },
      ],
    },
    {
      id: 'IMO 9214466',
      name: 'MT Blue Horizon',
      type: 'Product tanker',
      distanceKm: 8.5,
      score: 61,
      position: [83.74, 17.57] as Coordinate,
      speed: 13.2,
      heading: 74,
      color: '#94a3b8',
      track: [
        [83.51, 17.46],
        [83.58, 17.49],
        [83.65, 17.52],
        [83.74, 17.57],
        [83.84, 17.61],
      ] as Coordinate[],
      evidence: [
        { label: 'Spatial proximity', value: 72, status: 'match' as const },
        { label: 'Temporal match', value: 66, status: 'match' as const },
        { label: 'Trajectory match', value: 58, status: 'match' as const },
        { label: 'Origin consistency', value: 62, status: 'match' as const },
        { label: 'Behavioral anomaly', value: 31, status: 'warning' as const },
      ],
    },
    {
      id: 'IMO 9140835',
      name: 'MV Sea Wind',
      type: 'Bulk carrier',
      distanceKm: 13.3,
      score: 43,
      position: [83.77, 17.54] as Coordinate,
      speed: 9.6,
      heading: 101,
      color: '#64748b',
      track: [
        [83.56, 17.69],
        [83.62, 17.63],
        [83.69, 17.58],
        [83.77, 17.54],
        [83.86, 17.51],
      ] as Coordinate[],
      evidence: [
        { label: 'Spatial proximity', value: 51, status: 'match' as const },
        { label: 'Temporal match', value: 48, status: 'match' as const },
        { label: 'Trajectory match', value: 39, status: 'match' as const },
        { label: 'Origin consistency', value: 44, status: 'match' as const },
        { label: 'Behavioral anomaly', value: 22, status: 'warning' as const },
      ],
    },
  ] satisfies VesselRecord[],
};

export type DemoIncident = typeof demoIncident;

export const vesselDossiers: Record<
  string,
  {
    slug: string;
    image: string;
    country: string;
    flag: string;
    mmsi: string;
    callSign: string;
    built: number;
    lengthM: number;
    beamM: number;
    draughtM: number;
    deadweightT: number;
    grossTonnage: number;
    operator: string;
    homePort: string;
    cargo: string;
    navigationStatus: string;
  }
> = {
  'IMO 9387421': {
    slug: 'mv-ocean-star',
    image: '/ship-foreground.jpeg',
    country: 'India',
    flag: '🇮🇳',
    mmsi: '419001843',
    callSign: 'AWOS7',
    built: 2008,
    lengthM: 274,
    beamM: 48,
    draughtM: 15.2,
    deadweightT: 151420,
    grossTonnage: 84610,
    operator: 'Eastern Maritime Logistics',
    homePort: 'Visakhapatnam',
    cargo: 'Crude oil · 78% capacity',
    navigationStatus: 'Under way using engine',
  },
  'IMO 9214466': {
    slug: 'mt-blue-horizon',
    image: '/ship-hero.jpeg',
    country: 'Panama',
    flag: '🇵🇦',
    mmsi: '352914000',
    callSign: '3FQX8',
    built: 2004,
    lengthM: 228,
    beamM: 32,
    draughtM: 12.4,
    deadweightT: 74210,
    grossTonnage: 43870,
    operator: 'Blue Meridian Shipping',
    homePort: 'Panama City',
    cargo: 'Refined petroleum products',
    navigationStatus: 'Under way using engine',
  },
  'IMO 9140835': {
    slug: 'mv-sea-wind',
    image: '/ship-hero.jpeg',
    country: 'Marshall Islands',
    flag: '🇲🇭',
    mmsi: '538006214',
    callSign: 'V7KS3',
    built: 1998,
    lengthM: 190,
    beamM: 30,
    draughtM: 10.8,
    deadweightT: 52140,
    grossTonnage: 30420,
    operator: 'North Pacific Carriers',
    homePort: 'Majuro',
    cargo: 'Dry bulk · declared',
    navigationStatus: 'Under way using engine',
  },
};

export const getVesselBySlug = (slug: string) => {
  const vessel = demoIncident.vessels.find(
    (item) => vesselDossiers[item.id]?.slug === slug,
  );
  return vessel ? { vessel, dossier: vesselDossiers[vessel.id] } : null;
};

export const globalSpills = [
  {
    id: '26143',
    name: 'Bay of Bengal Slick',
    location: 'Bay of Bengal · Sector 04',
    coordinate: [83.6685, 17.5368] as Coordinate,
    detected: '27 Aug 2026 · 04:32 IST',
    area: 12.84,
    confidence: 94,
    severity: 'HIGH',
    status: 'Investigation ready',
    ready: true,
  },
  {
    id: '26098',
    name: 'Arabian Sea Sheen',
    location: 'Arabian Sea · Sector 11',
    coordinate: [67.82, 19.21] as Coordinate,
    detected: '26 Aug 2026 · 21:14 IST',
    area: 7.42,
    confidence: 88,
    severity: 'MEDIUM',
    status: 'Monitoring',
    ready: false,
  },
  {
    id: '26071',
    name: 'Malacca Corridor Event',
    location: 'Strait of Malacca',
    coordinate: [101.25, 2.71] as Coordinate,
    detected: '26 Aug 2026 · 15:08 IST',
    area: 4.18,
    confidence: 81,
    severity: 'MEDIUM',
    status: 'Verification',
    ready: false,
  },
  {
    id: '25984',
    name: 'Gulf Transit Anomaly',
    location: 'Persian Gulf · East',
    coordinate: [52.61, 26.39] as Coordinate,
    detected: '25 Aug 2026 · 10:41 IST',
    area: 18.62,
    confidence: 92,
    severity: 'HIGH',
    status: 'Monitoring',
    ready: false,
  },
  {
    id: '25877',
    name: 'Mediterranean Surface Film',
    location: 'Central Mediterranean',
    coordinate: [17.21, 35.54] as Coordinate,
    detected: '24 Aug 2026 · 06:19 IST',
    area: 3.06,
    confidence: 76,
    severity: 'LOW',
    status: 'Review',
    ready: false,
  },
  {
    id: '25791',
    name: 'South Atlantic Detection',
    location: 'South Atlantic · Sector 07',
    coordinate: [12.45, -24.32] as Coordinate,
    detected: '22 Aug 2026 · 18:52 IST',
    area: 9.31,
    confidence: 84,
    severity: 'MEDIUM',
    status: 'Monitoring',
    ready: false,
  },
];

export const globalMonitorStats = {
  active: 7,
  totalDetected: 1428,
  highPriority: 2,
  monitoredRegions: 12,
};
