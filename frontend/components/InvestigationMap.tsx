'use client';
import {
  type CSSProperties,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import * as maplibregl from 'maplibre-gl';
import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl';
import { LocateFixed, Navigation, Pause, Play, Waves, Wind } from 'lucide-react';
import { demoIncident, type Coordinate } from '../data/demoIncident';
import { backendDemoVessels } from '../data/backendDemo';
import type { ImageAnalysisResult } from '../services/analysisService';
import 'maplibre-gl/dist/maplibre-gl.css';

type Mode = 'analysis' | 'origin' | 'forecast';
type Vessel = {
  id: string;
  name: string;
  score: number;
  color: string;
  speed: number;
  heading: number;
  track: Coordinate[];
};
type ProjectedVessel = Vessel & { x: number; y: number; path: string };
type ForecastZone = {
  label: string;
  confidence: number;
  center: Coordinate;
  radius: number;
};
type Overlay = {
  vessels: ProjectedVessel[];
  origin: { x: number; y: number };
  spill: { x: number; y: number };
  connection: string;
  forecast: {
    x: number;
    y: number;
    radius: number;
    label: string;
    confidence: number;
  }[];
  grid: { path: string; label: string; x: number; y: number }[];
  current: string[];
  wind: string[];
};
const empty: Overlay = {
  vessels: [],
  origin: { x: 0, y: 0 },
  spill: { x: 0, y: 0 },
  connection: '',
  forecast: [],
  grid: [],
  current: [],
  wind: [],
};

function interpolate(track: Coordinate[], progress: number): Coordinate {
  if (track.length < 2) return track[0];
  const scaled = Math.max(0, Math.min(1, progress / 100)) * (track.length - 1),
    index = Math.min(Math.floor(scaled), track.length - 2),
    fraction = scaled - index;
  return [
    track[index][0] + (track[index + 1][0] - track[index][0]) * fraction,
    track[index][1] + (track[index + 1][1] - track[index][1]) * fraction,
  ];
}
function partialTrack(track: Coordinate[], progress: number): Coordinate[] {
  if (track.length < 2) return track;
  const scaled = Math.max(0, Math.min(1, progress / 100)) * (track.length - 1),
    index = Math.min(Math.floor(scaled), track.length - 2);
  return [...track.slice(0, index + 1), interpolate(track, progress)];
}
function naturalDriftPoint(
  start: Coordinate,
  end: Coordinate,
  progress: number,
  phase = 0,
): Coordinate {
  const t = Math.max(0, Math.min(1, progress)),
    dx = end[0] - start[0],
    dy = end[1] - start[1],
    distance = Math.max(Math.hypot(dx, dy), 0.0001),
    perpendicular: Coordinate = [-dy / distance, dx / distance],
    broadCurve = Math.sin(Math.PI * t) * distance * 0.19,
    eddy =
      Math.sin((t * 3.4 + phase) * Math.PI) *
      Math.sin(Math.PI * t) *
      distance *
      0.045,
    lateral = broadCurve + eddy;
  return [
    start[0] + dx * t + perpendicular[0] * lateral,
    start[1] + dy * t + perpendicular[1] * lateral,
  ];
}
function shiftCoordinates(value: unknown, dx: number, dy: number): unknown {
  if (
    Array.isArray(value) &&
    typeof value[0] === 'number' &&
    typeof value[1] === 'number'
  )
    return [(value[0] as number) + dx, (value[1] as number) + dy];
  if (Array.isArray(value))
    return value.map((item) => shiftCoordinates(item, dx, dy));
  return value;
}
function linePath(map: MapLibreMap, track: Coordinate[]): string {
  return track
    .map((coordinate, index) => {
      const point = map.project(coordinate);
      return `${index ? 'L' : 'M'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
    })
    .join(' ');
}
function heatFeatures(
  center: Coordinate,
  bbox?: [number, number, number, number] | null,
) {
  const width = bbox ? Math.max(bbox[2] - bbox[0], 0.018) : 0.08,
    height = bbox ? Math.max(bbox[3] - bbox[1], 0.014) : 0.05;
  const anchors: Array<[number, number, number]> = [
    [-0.32, -0.08, 0.32],
    [-0.27, -0.02, 0.48],
    [-0.23, 0.05, 0.68],
    [-0.19, 0.1, 0.82],
    [-0.16, 0.02, 0.92],
    [-0.12, -0.07, 0.74],
    [-0.08, 0.08, 0.88],
    [-0.04, 0, 1],
    [0, -0.08, 0.9],
    [0.04, 0.06, 0.96],
    [0.08, -0.02, 0.86],
    [0.12, 0.1, 0.78],
    [0.16, 0.02, 0.92],
    [0.2, -0.07, 0.72],
    [0.24, 0.04, 0.66],
    [0.29, 0.1, 0.48],
    [-0.2, -0.16, 0.42],
    [-0.1, 0.17, 0.46],
    [0.02, 0.16, 0.52],
    [0.1, -0.17, 0.5],
    [0.2, 0.16, 0.38],
    [0.34, -0.02, 0.3],
  ];
  const pattern = anchors.flatMap(([x, y, weight], index) =>
    Array.from({ length: 3 }, (_, point) => {
      const angle = index * 2.17 + point * 2.09;
      const spread = 0.018 + point * 0.013;
      return [x + Math.cos(angle) * spread, y + Math.sin(angle) * spread, weight * (1 - point * 0.13)] as [number, number, number];
    }),
  );
  return {
    type: 'FeatureCollection' as const,
    features: pattern.map(([x, y, weight]) => ({
      type: 'Feature' as const,
      properties: { weight },
      geometry: {
        type: 'Point' as const,
        coordinates: [center[0] + x * width, center[1] + y * height],
      },
    })),
  };
}

export default function InvestigationMap({
  analysis = null,
  coordinates = null,
  replay,
  activeLayers,
  selectedVesselId,
  mode,
  onSelectVessel,
  playing = false,
  onTogglePlay,
}: {
  analysis?: ImageAnalysisResult | null;
  coordinates?: Coordinate | null;
  replay: number;
  activeLayers: string[];
  selectedVesselId: string;
  mode: Mode;
  onSelectVessel?: (id: string) => void;
  playing?: boolean;
  onTogglePlay?: () => void;
}) {
  const live = Boolean(
    analysis?.detected &&
    analysis.geometry?.polygon &&
    analysis.geometry.centroid,
  );
  const historical = analysis?.environment?.source === 'backend_incident_data';
  const search = Boolean(coordinates && !live);
  const detectedCenter = (
    live ? analysis!.geometry!.centroid! : (coordinates ?? demoIncident.center)
  ) as Coordinate;
  const origin = (
    live && analysis?.drift?.end_point
      ? [analysis.drift.end_point.lon, analysis.drift.end_point.lat]
      : demoIncident.origin.coordinate
  ) as Coordinate;
  const windVector = analysis?.environment?.wind_m_s ?? { u: -5, v: -2.5 },
    currentVector = analysis?.environment?.current_m_s ?? { u: -0.1, v: -0.05 };
  const replayWindVector = live
    ? { u: detectedCenter[0] - origin[0], v: detectedCenter[1] - origin[1] }
    : windVector;
  const windSpeedKnots = Math.hypot(windVector.u, windVector.v) * 1.94384,
    windBearing =
      ((Math.atan2(replayWindVector.u, replayWindVector.v) * 180) / Math.PI + 360) % 360,
    windCompass = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][
      Math.round(windBearing / 45) % 8
    ];
  const vessels = useMemo<Vessel[]>(
    () =>
      live
        ? (analysis?.vessels?.length ? analysis.vessels : backendDemoVessels).map((vessel, index) => ({
            id: vessel.id,
            name: vessel.name,
            score: Math.round(
              (analysis?.candidates?.find(
                (candidate) => candidate.vessel_id === vessel.id || candidate.vessel_id === vessel.name,
              )?.overall_score ?? ('visualScore' in vessel ? (vessel.visualScore ?? 0) / 100 : 0)) * 100,
            ),
            color:
              'color' in vessel
                ? vessel.color
                : ['#38bdf8', '#94a3b8', '#67e8f9', '#a78bfa'][index] ?? '#64748b',
            speed: vessel.speed,
            heading: vessel.heading,
            track: vessel.track,
          }))
        : search
          ? []
          : demoIncident.vessels.map((vessel) => ({
              id: vessel.id,
              name: vessel.name,
              score: vessel.score,
              color: vessel.color,
              speed: vessel.speed,
              heading: vessel.heading,
              track: vessel.track,
            })),
    [live, search, analysis],
  );
  const forecast = useMemo<ForecastZone[]>(() => {
    if (!live)
      return demoIncident.forecast.map((item) => ({
        label: item.label,
        confidence: item.confidence,
        center: item.center,
        radius: 18 + item.hour * 5,
      }));
    const dx = detectedCenter[0] - origin[0],
      dy = detectedCenter[1] - origin[1];
    return [0, 2, 4, 6].map((hour, index) => ({
      label: index ? '+' + hour + 'H' : 'NOW',
      confidence: Math.max(58, 94 - index * 9),
      center: [
        detectedCenter[0] + dx * index * 0.55,
        detectedCenter[1] + dy * index * 0.55,
      ],
      radius: 20 + index * 10,
    }));
  }, [live, detectedCenter, origin]);
  const mapContainer = useRef<HTMLDivElement>(null),
    mapRef = useRef<MapLibreMap | null>(null),
    stateRef = useRef({ replay, mode });
  const [ready, setReady] = useState(false),
    [tileWarning, setTileWarning] = useState(false),
    [overlay, setOverlay] = useState<Overlay>(empty);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapContainer.current,
      center: detectedCenter,
      zoom: 10,
      minZoom: 2,
      maxZoom: 16,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          dark: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors',
          },
        },
        layers: [
          {
            id: 'dark-maritime',
            type: 'raster',
            source: 'dark',
            paint: {
              'raster-saturation': -1,
              'raster-brightness-min': 0,
              'raster-brightness-max': 0.24,
              'raster-contrast': 0.48,
              'raster-opacity': 0.82,
            },
          },
        ],
      },
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: true }),
      'top-right',
    );
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      'bottom-right',
    );
    map.on('error', () => setTileWarning(true));
    map.on('load', () => {
      const geometry = live
        ? analysis!.geometry!.polygon!
        : {
            type: 'Polygon' as const,
            coordinates: [demoIncident.spillPolygon],
          };
      map.addSource('investigation-spill', {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: { role: 'detected-spill' },
          geometry,
        },
      });
      map.addSource('spill-heat', {
        type: 'geojson',
        data: heatFeatures(detectedCenter, analysis?.geometry?.bbox),
      });
      if (live && analysis?.drift?.trajectory?.length) {
        map.addSource('backend-backtrack', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: { role: 'backward-drift' },
            geometry: {
              type: 'LineString',
              coordinates: analysis.drift.trajectory.map((point) => [point.lon, point.lat]),
            },
          },
        });
        map.addLayer({
          id: 'backend-backtrack-glow',
          type: 'line',
          source: 'backend-backtrack',
          paint: { 'line-color': '#38bdf8', 'line-width': 7, 'line-opacity': 0.12, 'line-blur': 5 },
        });
        map.addLayer({
          id: 'backend-backtrack-line',
          type: 'line',
          source: 'backend-backtrack',
          paint: { 'line-color': '#60a5fa', 'line-width': 2.3, 'line-opacity': 0.95, 'line-dasharray': [2, 2.5] },
        });
      }
      map.addLayer({
        id: 'spill-heatmap',
        type: 'heatmap',
        source: 'spill-heat',
        paint: {
          'heatmap-weight': [
            'interpolate',
            ['linear'],
            ['get', 'weight'],
            0,
            0,
            1,
            1.3,
          ],
          'heatmap-intensity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            6,
            1.15,
            12,
            2.05,
          ],
          'heatmap-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            6,
            12,
            10,
            24,
            13,
            34,
          ],
          'heatmap-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            5,
            0.58,
            12,
            0.9,
          ],
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0,
            'rgba(67,20,7,0)',
            0.12,
            'rgba(127,29,29,.16)',
            0.3,
            'rgba(194,65,12,.35)',
            0.5,
            'rgba(234,88,12,.58)',
            0.7,
            'rgba(245,158,11,.76)',
            0.86,
            'rgba(250,204,21,.9)',
            1,
            'rgba(255,247,205,.98)',
          ],
        },
      });
      map.addLayer({
        id: 'spill-soft-edge',
        type: 'line',
        source: 'investigation-spill',
        paint: {
          'line-color': '#f59e0b',
          'line-width': 10,
          'line-opacity': historical ? 0 : 0.1,
          'line-blur': 7,
        },
      });
      map.addLayer({
        id: 'spill-fill',
        type: 'fill',
        source: 'investigation-spill',
        paint: { 'fill-color': '#7c2d12', 'fill-opacity': historical ? 0 : 0.12 },
      });
      map.addLayer({
        id: 'spill-outline',
        type: 'line',
        source: 'investigation-spill',
        paint: {
          'line-color': '#fbbf24',
          'line-width': historical ? 0 : 1.6,
          'line-opacity': historical ? 0 : 0.92,
        },
      });
      map.on(
        'mouseenter',
        'spill-fill',
        () => (map.getCanvas().style.cursor = 'crosshair'),
      );
      map.on(
        'mouseleave',
        'spill-fill',
        () => (map.getCanvas().style.cursor = ''),
      );
      map.on('click', 'spill-fill', (event) =>
        new maplibregl.Popup({ className: 'intel-popup', offset: 12 })
          .setLngLat(event.lngLat)
          .setHTML(
            `<small>DETECTED SPILL</small><strong>${live ? (analysis!.geometry!.area / 1e6).toFixed(2) : demoIncident.areaKm2} km²</strong><span>${live ? 'GEOTIFF MASK' : '94% confidence · satellite detection'}</span>`,
          )
          .addTo(map),
      );
      setReady(true);
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    stateRef.current = { replay, mode };
    const map = mapRef.current;
    if (!ready || !map) return;
    const sync = () => {
      const progress = stateRef.current.replay,
        originProgress = Math.min(1, progress / 55);
      let spillCoordinate: Coordinate;
      if (progress <= 55)
        spillCoordinate = naturalDriftPoint(
          origin,
          detectedCenter,
          originProgress,
          0.35,
        );
      else {
        const p = (progress - 55) / 45,
          vector: [number, number] = [
            detectedCenter[0] - origin[0],
            detectedCenter[1] - origin[1],
          ],
          projectedEnd: Coordinate = [
            detectedCenter[0] + vector[0] * 0.8,
            detectedCenter[1] + vector[1] * 0.8,
          ];
        spillCoordinate = naturalDriftPoint(
          detectedCenter,
          projectedEnd,
          p,
          0.8,
        );
      }
      const driftTrack: Coordinate[] =
        progress <= 55
          ? Array.from({ length: 20 }, (_, index) =>
              naturalDriftPoint(
                origin,
                detectedCenter,
                originProgress * (index / 19),
                0.35,
              ),
            )
          : [
              ...Array.from({ length: 20 }, (_, index) =>
                naturalDriftPoint(
                  origin,
                  detectedCenter,
                  index / 19,
                  0.35,
                ),
              ),
              ...Array.from({ length: 14 }, (_, index) => {
                const vector: Coordinate = [
                    detectedCenter[0] - origin[0],
                    detectedCenter[1] - origin[1],
                  ],
                  projectedEnd: Coordinate = [
                    detectedCenter[0] + vector[0] * 0.8,
                    detectedCenter[1] + vector[1] * 0.8,
                  ];
                return naturalDriftPoint(
                  detectedCenter,
                  projectedEnd,
                  ((progress - 55) / 45) * (index / 13),
                  0.8,
                );
              }),
            ];
      const geometry = live
          ? analysis!.geometry!.polygon!
          : {
              type: 'Polygon' as const,
              coordinates: [demoIncident.spillPolygon],
            },
        shiftX = spillCoordinate[0] - detectedCenter[0],
        shiftY = spillCoordinate[1] - detectedCenter[1];
      const source = map.getSource('investigation-spill') as
        GeoJSONSource | undefined;
      source?.setData({
        type: 'Feature',
        properties: {
          phase:
            progress < 55
              ? 'backtrack'
              : progress > 72
                ? 'forecast'
                : 'detected',
        },
        geometry: {
          ...geometry,
          coordinates: shiftCoordinates(geometry.coordinates, shiftX, shiftY),
        } as GeoJSON.Geometry,
      });
      const heatSource = map.getSource('spill-heat') as
        GeoJSONSource | undefined;
      heatSource?.setData(
        heatFeatures(spillCoordinate, analysis?.geometry?.bbox),
      );
      const projectedVessels = vessels.map((vessel) => {
          const position = interpolate(vessel.track, progress),
            point = map.project(position);
          return {
            ...vessel,
            x: point.x,
            y: point.y,
            path: linePath(map, partialTrack(vessel.track, progress)),
          };
        }),
        originPoint = map.project(origin),
        spillPoint = map.project(spillCoordinate);
      const bounds = map.getBounds(),
        west = bounds.getWest(),
        east = bounds.getEast(),
        south = bounds.getSouth(),
        north = bounds.getNorth(),
        grid = [] as Overlay['grid'];
      for (let i = 1; i < 5; i++) {
        const lon = west + ((east - west) * i) / 5,
          lat = south + ((north - south) * i) / 5;
        const a = map.project([lon, south]),
          b = map.project([lon, north]),
          c = map.project([west, lat]),
          d = map.project([east, lat]);
        grid.push(
          {
            path: `M${a.x} ${a.y}L${b.x} ${b.y}`,
            label: `${lon.toFixed(2)}°`,
            x: a.x + 3,
            y: 18,
          },
          {
            path: `M${c.x} ${c.y}L${d.x} ${d.y}`,
            label: `${lat.toFixed(2)}°`,
            x: 4,
            y: c.y - 3,
          },
        );
      }
      const incidentBbox = analysis?.geometry?.bbox,
        corridorWidth = Math.abs(detectedCenter[0] - origin[0]),
        corridorHeight = Math.abs(detectedCenter[1] - origin[1]),
        areaWidth = Math.max(
          incidentBbox ? (incidentBbox[2] - incidentBbox[0]) * 1.7 : 0.16,
          corridorWidth * 1.35,
          0.045,
        ),
        areaHeight = Math.max(
          incidentBbox ? (incidentBbox[3] - incidentBbox[1]) * 2.2 : 0.11,
          corridorHeight * 1.35,
          0.04,
        ),
        corridorCenter: [number, number] = [
          (detectedCenter[0] + origin[0]) / 2,
          (detectedCenter[1] + origin[1]) / 2,
        ],
        areaWest = corridorCenter[0] - areaWidth / 2,
        areaSouth = corridorCenter[1] - areaHeight / 2;
      const currentNorm = Math.max(
          Math.hypot(currentVector.u, currentVector.v),
          0.001,
        ),
        currentDx = (currentVector.u / currentNorm) * areaWidth * 0.23,
        currentDy = (currentVector.v / currentNorm) * areaHeight * 0.23;
      const currentTracks = Array.from({ length: 12 }, (_, index) => {
        const column = index % 4,
          row = Math.floor(index / 4),
          start: [number, number] = [
            areaWest + areaWidth * (0.14 + column * 0.24),
            areaSouth + areaHeight * (0.18 + row * 0.31),
          ],
          end: [number, number] = [start[0] + currentDx, start[1] + currentDy];
        return linePath(map, [
          start,
          [
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2 + areaHeight * 0.025,
          ],
          end,
        ]);
      });
      const windNorm = Math.max(Math.hypot(replayWindVector.u, replayWindVector.v), 0.001),
        windUnitX = replayWindVector.u / windNorm,
        windUnitY = replayWindVector.v / windNorm,
        perpendicularX = -windUnitY,
        perpendicularY = windUnitX,
        windLength = Math.max(
          Math.hypot(corridorWidth, corridorHeight) * 1.25,
          Math.max(areaWidth, areaHeight) * 0.8,
        );
      const windTracks = Array.from({ length: 9 }, (_, index) => {
        const lane = index - 4,
          lateral = lane * Math.min(areaWidth, areaHeight) * 0.1,
          start: [number, number] = [
            corridorCenter[0] - windUnitX * windLength * 0.52 + perpendicularX * lateral,
            corridorCenter[1] - windUnitY * windLength * 0.52 + perpendicularY * lateral,
          ],
          end: [number, number] = [
            corridorCenter[0] + windUnitX * windLength * 0.52 + perpendicularX * lateral,
            corridorCenter[1] + windUnitY * windLength * 0.52 + perpendicularY * lateral,
          ],
          bend: [number, number] = [
            (start[0] + end[0]) / 2 + perpendicularX * areaWidth * 0.025,
            (start[1] + end[1]) / 2 + perpendicularY * areaHeight * 0.025,
          ];
        return linePath(map, [start, bend, end]);
      });
      const projectedForecast = forecast.map((zone) => {
        const point = map.project(zone.center);
        return {
          x: point.x,
          y: point.y,
          radius: zone.radius,
          label: zone.label,
          confidence: zone.confidence,
        };
      });
      setOverlay({
        vessels: projectedVessels,
        origin: { x: originPoint.x, y: originPoint.y },
        spill: { x: spillPoint.x, y: spillPoint.y },
        connection: linePath(map, driftTrack),
        forecast: projectedForecast,
        grid,
        current: currentTracks,
        wind: windTracks,
      });
    };
    sync();
    map.on('move', sync);
    map.on('resize', sync);
    return () => {
      map.off('move', sync);
      map.off('resize', sync);
    };
  }, [
    ready,
    replay,
    mode,
    live,
    analysis,
    vessels,
    forecast,
    detectedCenter,
    origin,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const show = activeLayers.includes('Oil spill');
    ['spill-heatmap', 'spill-soft-edge', 'spill-fill', 'spill-outline'].forEach(
      (id) =>
        map.getLayer(id) &&
        map.setLayoutProperty(id, 'visibility', show ? 'visible' : 'none'),
    );
  }, [activeLayers, ready]);
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !live) return;
    const visible = activeLayers.includes('Probable origin') && replay >= 32;
    ['backend-backtrack-glow', 'backend-backtrack-line'].forEach((id) => {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
    });
  }, [activeLayers, replay, ready, live]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const frame = () => {
      const points = [
          origin,
          detectedCenter,
          ...vessels.flatMap((vessel) => vessel.track),
          ...forecast.map((zone) => zone.center),
        ],
        lngs = points.map((point) => point[0]),
        lats = points.map((point) => point[1]);
      map.fitBounds(
        [
          [Math.min(...lngs), Math.min(...lats)],
          [Math.max(...lngs), Math.max(...lats)],
        ],
        { padding: 80, duration: 700, maxZoom: 12 },
      );
    };
    map.loaded() ? frame() : map.once('load', frame);
  }, []);

  const showSpill = activeLayers.includes('Oil spill'),
    showOrigin = activeLayers.includes('Probable origin') && replay >= 32,
    showAIS = activeLayers.includes('AIS tracks'),
    showCurrent = activeLayers.includes('Ocean current'),
    showWind = activeLayers.includes('Wind'),
    showForecast =
      activeLayers.includes('Forecast') &&
      (mode === 'forecast' || replay >= 72);
  return (
    <div className="live-map-shell intelligence-map">
      <div ref={mapContainer} className="live-map" />
      <svg
        className="forensic-overlay"
        aria-label="Maritime investigation overlays"
      >
        <defs>
          <filter id="spillGlow">
            <feGaussianBlur stdDeviation="8" />
          </filter>
          <filter id="selectedGlow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <marker
            id="aisArrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path
              d="M1 1 9 5 1 9"
              fill="none"
              stroke="context-stroke"
              strokeWidth="1.5"
            />
          </marker>
          <marker
            id="flowArrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path
              d="M1 1 9 5 1 9"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="1.4"
            />
          </marker>
          <marker
            id="windVectorArrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path
              d="M1 1 9 5 1 9"
              fill="none"
              stroke="#e6edf3"
              strokeWidth="1.4"
            />
          </marker>
        </defs>
        <g className="geo-grid">
          {overlay.grid.map((line, index) => (
            <g key={index}>
              <path d={line.path} />
              <text x={line.x} y={line.y}>
                {line.label}
              </text>
            </g>
          ))}
        </g>
        {showCurrent && (
          <g className="scientific-current">
            {overlay.current.map((path, index) => (
              <path key={index} d={path} markerEnd="url(#flowArrow)" />
            ))}
          </g>
        )}
        {showWind && (
          <g className="scientific-wind">
            {overlay.wind.map((path, index) => (
              <path key={index} d={path} markerEnd="url(#windVectorArrow)" />
            ))}
          </g>
        )}
        {showForecast && (
          <g className="map-forecast-zones">
            {overlay.forecast.map((zone, index) => (
              <g
                key={zone.label}
                style={{ opacity: Math.max(0.18, 0.58 - index * 0.11) }}
              >
                <circle cx={zone.x} cy={zone.y} r={zone.radius} />
                <text x={zone.x} y={zone.y - zone.radius - 5}>
                  {zone.label}
                </text>
              </g>
            ))}
          </g>
        )}
        {showOrigin && (
          <g className="probable-origin-layer">
            {!live && <path d={overlay.connection} />}
            <circle cx={overlay.origin.x} cy={overlay.origin.y} r="31" />
            <circle cx={overlay.origin.x} cy={overlay.origin.y} r="21" />
            <circle cx={overlay.origin.x} cy={overlay.origin.y} r="5" />
          </g>
        )}
        {showAIS && (
          <g>
            {overlay.vessels.map((vessel) => (
              <path
                key={vessel.id}
                d={vessel.path}
                className={`intelligence-ais-track ${vessel.id === selectedVesselId ? 'selected' : ''}`}
                style={{ stroke: vessel.color }}
                markerEnd="url(#aisArrow)"
                filter={
                  vessel.id === selectedVesselId
                    ? 'url(#selectedGlow)'
                    : undefined
                }
              />
            ))}
          </g>
        )}
      </svg>
      {showSpill && (
        <div
          className="map-annotation spill-annotation"
          style={{ left: overlay.spill.x + 18, top: overlay.spill.y - 55 }}
        >
          <small>DETECTED SPILL</small>
          <b>
            {live
              ? (analysis!.geometry!.area / 1e6).toFixed(2)
              : demoIncident.areaKm2}{' '}
            km²
          </b>
          <span>{live ? 'GEOTIFF DETECTION' : '94% CONFIDENCE'}</span>
        </div>
      )}
      {showOrigin && (
        <button
          className="map-annotation origin-annotation"
          style={{ left: overlay.origin.x + 22, top: overlay.origin.y + 10 }}
          onClick={() => {
            const map = mapRef.current;
            if (map)
              new maplibregl.Popup({ className: 'intel-popup' })
                .setLngLat(origin)
                .setHTML(
                  `<small>PROBABLE ORIGIN</small><strong>${live ? 'BACKTRACKED ESTIMATE' : '81% confidence'}</strong><span>Uncertainty area · not a confirmed source</span>`,
                )
                .addTo(map);
          }}
        >
          <small>PROBABLE ORIGIN</small>
          <b>{live ? 'ESTIMATED' : '81% CONFIDENCE'}</b>
        </button>
      )}
      {showAIS &&
        overlay.vessels.map((vessel) => (
          <button
            key={vessel.id}
            title={`${vessel.name} · ${vessel.speed} kn · ${vessel.score}% match`}
            className={`intel-vessel ${vessel.id === selectedVesselId ? 'selected' : ''}`}
            style={
              {
                left: vessel.x,
                top: vessel.y,
                '--vessel-color': vessel.color,
                '--heading': `${vessel.heading}deg`,
              } as CSSProperties
            }
            onClick={() => onSelectVessel?.(vessel.id)}
          >
            <i>
              <Navigation />
            </i>
            <span>
              {vessel.name}
              <b>
                {vessel.score}% MATCH · {vessel.speed} kn
              </b>
            </span>
          </button>
        ))}
      <div className="map-layer-legend">
        <span>
          <i className="legend-spill" />
          OIL SPILL
        </span>
        <span>
          <i className="legend-origin" />
          PROBABLE ORIGIN
        </span>
        <span>
          <i className="legend-track" />
          AIS TRACK
        </span>
        <span>
          <Navigation />
          VESSEL
        </span>
        <span>
          <Waves />
          CURRENT
        </span>
        <span>
          <Wind />
          WIND
        </span>
        <span>
          <i className="legend-forecast" />
          FORECAST
        </span>
      </div>
      {showWind && (
        <div className="compact-vector-indicator wind-indicator">
          <Wind />
          <span>
            WIND ·{' '}
            {analysis?.environment?.source === 'deterministic_demo_input'
              ? 'MODEL INPUT'
              : 'INCIDENT DATA'}
            <b>
              {windSpeedKnots.toFixed(1)} kn · {windCompass}
            </b>
          </span>
        </div>
      )}
      {onTogglePlay && (
        <button
          type="button"
          className={`map-playback-control${playing ? ' active' : ''}`}
          onClick={onTogglePlay}
          aria-label={playing ? 'Pause incident replay' : 'Play incident replay'}
        >
          {playing ? <Pause /> : <Play />}
          <span>{playing ? 'PAUSE MOVEMENT' : 'PLAY MOVEMENT'}</span>
        </button>
      )}
      {showForecast && (
        <div className="compact-vector-indicator forecast-indicator">
          <LocateFixed />
          <span>
            FORECAST<b>+6H · {overlay.forecast.at(-1)?.confidence ?? 67}%</b>
          </span>
        </div>
      )}
      {!ready && (
        <div className="map-state">
          <i />
          <strong>INITIALIZING MARITIME INTELLIGENCE</strong>
        </div>
      )}
      {tileWarning && (
        <div className="tile-warning">
          DARK BASEMAP LINK DEGRADED · ANALYTICAL LAYERS REMAIN ACTIVE
        </div>
      )}
      <div className="map-readout">
        <i />{' '}
        {mode === 'origin'
          ? 'BACKTRACK ACTIVE'
          : mode === 'forecast'
            ? 'FORECAST ACTIVE'
            : 'LIVE GEOINT'}{' '}
        <span>
          {detectedCenter[1].toFixed(4)}° N / {detectedCenter[0].toFixed(4)}° E
        </span>
      </div>
      <div className="synthetic-tag">
        {live ? 'LIVE GEOMETRY · DEMO AIS/ENV' : 'DETERMINISTIC INCIDENT DATA'}
      </div>
    </div>
  );
}
