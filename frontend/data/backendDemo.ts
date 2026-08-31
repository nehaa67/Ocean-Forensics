import type { Coordinate, EvidenceFactor } from './demoIncident';

export type BackendDemoVessel = {
  id: string;
  name: string;
  type: string;
  flag: string;
  country: string;
  imo: string;
  mmsi: string;
  callSign: string;
  built: number;
  lengthM: number;
  beamM: number;
  draughtM: number;
  deadweightT: number;
  operator: string;
  homePort: string;
  cargo: string;
  distanceKm: number;
  speed: number;
  heading: number;
  color: string;
  track: Coordinate[];
  timestamps: string[];
  evidence: EvidenceFactor[];
  image?: string;
};

export const backendDemoVessels: BackendDemoVessel[] = [
  {
    id: 'SANCHI',
    name: 'SANCHI',
    type: 'Suezmax crude oil tanker',
    flag: '🇵🇦',
    country: 'Panama',
    imo: 'IMO 9356608',
    mmsi: '356137000',
    callSign: '3EUN9',
    built: 2008,
    lengthM: 274,
    beamM: 50,
    draughtM: 17,
    deadweightT: 164154,
    operator: 'Bright Shipping Ltd.',
    homePort: 'Panama City',
    cargo: 'Natural-gas condensate · historical incident cargo',
    distanceKm: 13.4,
    speed: 10,
    heading: 181,
    color: '#38bdf8',
    image: '/sanchi-tanker-reference.png',
    track: [
      [124.52, 28.21],
      [124.58, 28.12],
      [124.64, 28.03],
      [124.7, 27.94],
      [124.76, 27.84],
    ],
    timestamps: [
      '2018-01-06T10:30:00Z',
      '2018-01-06T11:00:00Z',
      '2018-01-06T11:30:00Z',
      '2018-01-06T12:00:00Z',
      '2018-01-06T12:30:00Z',
    ],
    evidence: [
      { label: 'Spatial proximity', value: 94, status: 'match' },
      { label: 'Temporal match', value: 91, status: 'match' },
      { label: 'Trajectory consistency', value: 89, status: 'match' },
      { label: 'Heading consistency', value: 86, status: 'match' },
    ],
  },
  {
    id: 'CF CRYSTAL',
    name: 'CF CRYSTAL',
    type: 'Bulk carrier',
    flag: '🇭🇰',
    country: 'Hong Kong',
    imo: 'IMO 9497050',
    mmsi: '477000800',
    callSign: 'VRLL2',
    built: 2011,
    lengthM: 225,
    beamM: 32,
    draughtM: 13.2,
    deadweightT: 75500,
    operator: 'Changhong Group (HK) Ltd.',
    homePort: 'Hong Kong',
    cargo: 'Grain · historical incident cargo',
    distanceKm: 18.7,
    speed: 8.4,
    heading: 6,
    color: '#94a3b8',
    image: '/ship-hero.jpeg',
    track: [
      [124.83, 27.78],
      [124.79, 27.86],
      [124.75, 27.94],
      [124.71, 28.02],
      [124.68, 28.1],
    ],
    timestamps: [
      '2018-01-06T10:30:00Z',
      '2018-01-06T11:00:00Z',
      '2018-01-06T11:30:00Z',
      '2018-01-06T12:00:00Z',
      '2018-01-06T12:30:00Z',
    ],
    evidence: [
      { label: 'Spatial proximity', value: 58, status: 'match' },
      { label: 'Temporal match', value: 62, status: 'match' },
      { label: 'Trajectory consistency', value: 45, status: 'warning' },
      { label: 'Heading consistency', value: 38, status: 'warning' },
    ],
  },
  {
    id: 'V1',
    name: 'MT Nordic Aurora',
    type: 'Crude oil tanker',
    flag: '🇩🇰',
    country: 'Denmark',
    imo: 'IMO 9387421',
    mmsi: '219018472',
    callSign: 'OZNA7',
    built: 2011,
    lengthM: 274,
    beamM: 48,
    draughtM: 15.1,
    deadweightT: 151420,
    operator: 'Nordic Maritime A/S',
    homePort: 'Esbjerg',
    cargo: 'Crude oil · 76% capacity',
    distanceKm: 0.12,
    speed: 12.2,
    heading: 92,
    color: '#38bdf8',
    track: [
      [5.221, 55.474],
      [5.226, 55.4755],
      [5.231, 55.477],
      [5.2345, 55.478],
      [5.238, 55.479],
    ],
    timestamps: [
      '2022-01-01T00:00:00Z',
      '2022-01-01T00:05:00Z',
      '2022-01-01T00:10:00Z',
      '2022-01-01T00:15:00Z',
      '2022-01-01T00:20:00Z',
    ],
    evidence: [
      { label: 'Spatial proximity', value: 100, status: 'match' },
      { label: 'Temporal match', value: 100, status: 'match' },
      { label: 'Trajectory consistency', value: 0, status: 'warning' },
      { label: 'Heading consistency', value: 100, status: 'match' },
    ],
  },
  {
    id: 'V2',
    name: 'MV Baltic Meridian',
    type: 'Product tanker',
    flag: '🇳🇴',
    country: 'Norway',
    imo: 'IMO 9214466',
    mmsi: '257914660',
    callSign: 'LAMB8',
    built: 2006,
    lengthM: 228,
    beamM: 32,
    draughtM: 12.4,
    deadweightT: 74210,
    operator: 'Meridian Sea Transport',
    homePort: 'Bergen',
    cargo: 'Refined petroleum products',
    distanceKm: 2.17,
    speed: 15.1,
    heading: 180,
    color: '#94a3b8',
    track: [
      [5.225, 55.487],
      [5.23, 55.49],
      [5.235, 55.4925],
      [5.24, 55.495],
      [5.242, 55.502],
    ],
    timestamps: [
      '2022-01-01T00:05:00Z',
      '2022-01-01T00:10:00Z',
      '2022-01-01T00:15:00Z',
      '2022-01-01T00:20:00Z',
      '2022-01-01T00:25:00Z',
    ],
    evidence: [
      { label: 'Spatial proximity', value: 100, status: 'match' },
      { label: 'Temporal match', value: 0, status: 'warning' },
      { label: 'Trajectory consistency', value: 100, status: 'match' },
      { label: 'Heading consistency', value: 0, status: 'warning' },
    ],
  },
];
