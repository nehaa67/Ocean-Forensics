'use client';
import {
  type RefObject,
  useEffect,
  useMemo,
  useState,
} from 'react';
import dynamic from 'next/dynamic';
import { demoIncident, vesselDossiers } from '../../data/demoIncident';
import MockVesselDossier from './MockVesselDossier';
import {
  CloudSun,
  Droplets,
  LocateFixed,
  Radar,
  Route,
  Waves,
  Wind,
  Scale,
} from 'lucide-react';
import type { ImageAnalysisResult } from '../../services/analysisService';
import { backendDemoVessels } from '../../data/backendDemo';
import CandidateComparison from './CandidateComparison';
import InvestigationInsights from './InvestigationInsights';
import { backendApi } from '../../services/backendService';

const layerOptions = [
  'Oil spill',
  'AIS tracks',
  'Probable origin',
  'Ocean current',
  'Wind',
  'Forecast',
];
const pendingLayers = new Set(['Ocean current', 'Wind']);
const layerIcons = {
  'Oil spill': Droplets,
  'AIS tracks': Route,
  'Probable origin': LocateFixed,
  'Ocean current': Waves,
  Wind: Wind,
  Forecast: CloudSun,
};
const InvestigationMap = dynamic(() => import('../InvestigationMap'), {
  ssr: false,
  loading: () => (
    <div className="map-loading">
      <i />
      <strong>INITIALIZING GEOINT MAP</strong>
      <span>Loading deterministic incident layers…</span>
    </div>
  ),
});
const processStages = [
  { label: 'Detection', value: 42, mode: 'analysis' as const },
  { label: 'Backtrack', value: 66, mode: 'origin' as const },
  { label: 'Vessel review', value: 84, mode: 'analysis' as const },
  { label: 'Attribution', value: 96, mode: 'analysis' as const },
];

export default function InvestigationDashboard({
  sectionRef,
  analysis = null,
  coordinates = null,
}: {
  sectionRef: RefObject<HTMLElement | null>;
  analysis?: ImageAnalysisResult | null;
  coordinates?: [number, number] | null;
}) {
  const isLive = Boolean(analysis?.detected && analysis.geometry);
  const isSearch = Boolean(coordinates && !isLive);
  const liveCenter = analysis?.geometry?.centroid;
  const liveLocation = liveCenter
    ? `${liveCenter[1].toFixed(4)}° N · ${liveCenter[0].toFixed(4)}° E`
    : 'Location unavailable';
  const rankedCandidates = useMemo(
    () =>
      analysis?.candidates?.map((candidate) => {
        const mock = backendDemoVessels.find(
          (vessel) => vessel.id === candidate.vessel_id,
        );
        const visual = analysis?.vessels?.find(
          (vessel) =>
            vessel.id === candidate.vessel_id ||
            vessel.name === candidate.vessel_id,
        );
        const visualPosition = visual?.track.at(-1) ?? visual?.position;
        const visualDistance =
          visualPosition && liveCenter
            ? Math.hypot(
                (visualPosition[0] - liveCenter[0]) *
                  111 *
                  Math.cos((liveCenter[1] * Math.PI) / 180),
                (visualPosition[1] - liveCenter[1]) * 111,
              )
            : 0;
        return {
          id: candidate.vessel_id,
          name: visual?.name ?? mock?.name ?? candidate.vessel_id,
          type: mock?.type ?? 'AIS candidate',
          distanceKm:
            mock?.distanceKm ?? Number(visualDistance.toFixed(1)),
          score: Math.round(candidate.overall_score * 100),
          position: (visualPosition ??
            mock?.track.at(-1) ??
            liveCenter ??
            demoIncident.center) as [number, number],
          speed: visual?.speed ?? mock?.speed ?? 0,
          heading: visual?.heading ?? mock?.heading ?? 0,
          color: mock?.color ?? '#64748b',
          track: visual?.track ?? mock?.track ?? [],
          evidence: [
            {
              label: 'Spatial proximity',
              value: Math.round(candidate.spatial_proximity * 100),
              status:
                candidate.spatial_proximity > 0.4
                  ? ('match' as const)
                  : ('warning' as const),
            },
            {
              label: 'Temporal match',
              value: Math.round(candidate.temporal_proximity * 100),
              status:
                candidate.temporal_proximity > 0.4
                  ? ('match' as const)
                  : ('warning' as const),
            },
            {
              label: 'Trajectory consistency',
              value: Math.round(candidate.trajectory_consistency * 100),
              status:
                candidate.trajectory_consistency > 0.4
                  ? ('match' as const)
                  : ('warning' as const),
            },
            {
              label: 'Heading consistency',
              value: Math.round(candidate.heading_consistency * 100),
              status:
                candidate.heading_consistency > 0.4
                  ? ('match' as const)
                  : ('warning' as const),
            },
          ],
        };
      }) ?? [],
    [analysis, liveCenter],
  );
  const liveCandidates = useMemo(() => {
    const rankedIds = new Set(
      rankedCandidates.flatMap((vessel) => [vessel.id, vessel.name]),
    );
    const contextual = (analysis?.vessels ?? [])
      .filter(
        (vessel) => !rankedIds.has(vessel.id) && !rankedIds.has(vessel.name),
      )
      .map((vessel, index) => {
        const position = vessel.track.at(-1) ?? vessel.position;
        const distanceKm = liveCenter
          ? Math.hypot(
              (position[0] - liveCenter[0]) *
                111 *
                Math.cos((liveCenter[1] * Math.PI) / 180),
              (position[1] - liveCenter[1]) * 111,
            )
          : 0;
        const score = vessel.visualScore ?? Math.max(8, 18 - index * 6);
        return {
          id: vessel.id,
          name: vessel.name,
          type: 'Contextual AIS traffic',
          distanceKm: Number(distanceKm.toFixed(1)),
          score,
          position,
          speed: vessel.speed,
          heading: vessel.heading,
          color: ['#67e8f9', '#a78bfa'][index] ?? '#64748b',
          track: vessel.track,
          evidence: [
            { label: 'Spatial proximity', value: Math.min(38, score + 12), status: 'warning' as const },
            { label: 'Temporal match', value: Math.min(32, score + 8), status: 'warning' as const },
            { label: 'Trajectory consistency', value: Math.max(6, score - 4), status: 'warning' as const },
            { label: 'Heading consistency', value: Math.min(30, score + 5), status: 'warning' as const },
          ],
        };
      });
    return [...rankedCandidates, ...contextual].sort(
      (first, second) => second.score - first.score,
    );
  }, [analysis?.vessels, liveCenter, rankedCandidates]);
  const [selectedId, setSelectedId] = useState(demoIncident.vessels[0].id);
  const [replay, setReplay] = useState(62);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [playDirection, setPlayDirection] = useState<1 | -1>(1);
  const [layers, setLayers] = useState(
    isSearch ? [] : layerOptions.filter((layer) => !pendingLayers.has(layer)),
  );
  const [mode, setMode] = useState<'analysis' | 'origin' | 'forecast'>(
    'analysis',
  );
  const [distance, setDistance] = useState(15);
  const [details, setDetails] = useState(false);
  const [reportGenerating, setReportGenerating] = useState(false);
  const [reportError, setReportError] = useState('');
  const [mockDossierOpen, setMockDossierOpen] = useState(false);
  const [comparisonOpen, setComparisonOpen] = useState(false);

  useEffect(() => {
    if (isLive)
      setLayers([
        'Oil spill',
        'AIS tracks',
        'Probable origin',
        'Ocean current',
        'Wind',
      ]);
  }, [isLive]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(
      () =>
        setReplay((value) => {
          const next = value + playDirection;
          if (next >= 100 || next <= 0) {
            setPlaying(false);
            return Math.max(0, Math.min(100, next));
          }
          return next;
        }),
      170 / speed,
    );
    return () => window.clearInterval(timer);
  }, [playing, speed, playDirection]);
  const sourceVessels = isLive
    ? liveCandidates
    : isSearch
      ? []
      : demoIncident.vessels;
  const vessels = useMemo(
    () =>
      sourceVessels.filter((vessel) => isLive || vessel.distanceKm <= distance),
    [sourceVessels, distance, isLive],
  );
  const selected =
    sourceVessels.find((vessel) => vessel.id === selectedId) ??
    sourceVessels[0] ??
    demoIncident.vessels[0];
  const stage =
    [...demoIncident.timeline].reverse().find((item) => replay >= item.value) ??
    demoIncident.timeline[0];
  const toggleLayer = (layer: string) =>
    setLayers((current) =>
      current.includes(layer)
        ? current.filter((item) => item !== layer)
        : [...current, layer],
    );
  const runMode = (next: 'analysis' | 'origin' | 'forecast') => {
    setMode(next);
    if (next === 'origin') {
      setReplay(72);
      setPlayDirection(-1);
      setPlaying(true);
    }
    if (next === 'forecast') {
      setReplay(72);
      setPlayDirection(1);
      setPlaying(true);
    }
  };
  const jumpTo = (
    value: number,
    nextMode: 'analysis' | 'origin' | 'forecast' = 'analysis',
  ) => {
    setPlaying(false);
    setReplay(value);
    setMode(nextMode);
  };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement)?.matches('input,select,button')) return;
      if (event.code === 'Space') {
        event.preventDefault();
        setPlaying((value) => !value);
      }
      if (event.key === 'ArrowRight')
        setReplay((value) => Math.min(100, value + 3));
      if (event.key === 'ArrowLeft')
        setReplay((value) => Math.max(0, value - 3));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  const activeProcess = [...processStages]
    .reverse()
    .findIndex((item) => replay >= item.value);
  const activeProcessIndex =
    activeProcess < 0 ? 0 : processStages.length - 1 - activeProcess;

  return (
    <section ref={sectionRef} className="dashboard-section" id="investigation">
      <header className="workspace-header">
        <div>
          <p>
            {isLive
              ? 'LIVE BACKEND RESULT'
              : isSearch
                ? 'COORDINATE SEARCH AREA'
                : 'SECURE CASE NODE'}{' '}
            · #{isLive ? 'TIFF-001' : isSearch ? 'NEW' : demoIncident.id}
          </p>
          <h1>Investigation workspace</h1>
        </div>
        <div className="workspace-actions">
          <button
            className={mode === 'analysis' ? 'active' : ''}
            onClick={() => jumpTo(55, 'analysis')}
            disabled={isSearch}
          >
            DETECTION VIEW
          </button>
          <button
            className={mode === 'origin' ? 'active' : ''}
            onClick={() => runMode('origin')}
            disabled={isSearch}
          >
            RECONSTRUCT ORIGIN
          </button>
        </div>
      </header>
      <button
        className="incident-summary"
        onClick={() => setDetails(!details)}
        aria-expanded={details}
      >
        {[
          [
            'CASE',
            isLive
              ? '#TIFF-001'
              : isSearch
                ? 'NEW SEARCH'
                : `#${demoIncident.id}`,
          ],
          [
            'STATUS',
            isLive
              ? 'SPILL DETECTED'
              : isSearch
                ? 'SEARCH AREA READY'
                : demoIncident.detectedAt,
          ],
          [
            'LOCATION',
            isLive
              ? liveLocation
              : isSearch
                ? `${coordinates![1].toFixed(4)}° N · ${coordinates![0].toFixed(4)}° E`
                : demoIncident.location,
          ],
          [
            'SPILL AREA',
            isLive
              ? `${((analysis?.geometry?.area ?? 0) / 1_000_000).toFixed(2)} km²`
              : isSearch
                ? 'PENDING'
                : `${demoIncident.areaKm2} km²`,
          ],
          [
            'SOURCE',
            isLive
              ? 'FASTAPI / GEOTIFF'
              : isSearch
                ? 'COORDINATE INPUT'
                : `${demoIncident.detectionConfidence}% CONFIDENCE`,
          ],
        ].map(([key, value]) => (
          <span key={key}>
            <small>{key}</small>
            <strong>{value}</strong>
          </span>
        ))}
        <i>{details ? '−' : '+'}</i>
      </button>
      {details && (
        <div className="incident-details">
          <span>
            Perimeter{' '}
            <b>
              {isLive
                ? `${((analysis?.geometry?.perimeter ?? 0) / 1000).toFixed(2)} km`
                : `${demoIncident.perimeterKm} km`}
            </b>
          </span>
          <span>
            Pixels{' '}
            <b>
              {isLive
                ? analysis?.geometry?.pixel_count
                : demoIncident.estimatedAge}
            </b>
          </span>
          <span>
            Geometry{' '}
            <b>
              {isLive
                ? analysis?.geometry?.polygon?.type
                : demoIncident.severity}
            </b>
          </span>
          <span>
            CRS{' '}
            <b>
              {isLive ? analysis?.geometry?.crs : demoIncident.currentDirection}
            </b>
          </span>
          <em>
            {isLive
              ? 'LIVE BACKEND RESPONSE'
              : 'SYNTHETIC INCIDENT · DEMONSTRATION DATA'}
          </em>
        </div>
      )}
      <nav
        className="investigation-progress"
        aria-label="Investigation progress"
      >
        {processStages.map((item, index) => (
          <button
            key={item.label}
            className={
              index < activeProcessIndex
                ? 'complete'
                : index === activeProcessIndex
                  ? 'active'
                  : ''
            }
            onClick={() => jumpTo(item.value, item.mode)}
          >
            <i>{index < activeProcessIndex ? '✓' : `0${index + 1}`}</i>
            <span>{item.label}</span>
            {index < processStages.length - 1 && <em />}
          </button>
        ))}
      </nav>
      <div className="workspace-grid">
        <section className="workspace-map panel">
          <div className="map-command">
            <div>
              <small>
                {isSearch
                  ? 'NEARBY AREA SEARCH'
                  : mode === 'origin'
                    ? 'BACKTRACKING MODEL'
                    : mode === 'forecast'
                      ? 'PREDICTIVE DRIFT MODEL'
                      : 'LIVE INVESTIGATION MAP'}
              </small>
              <strong>
                {isLive
                  ? liveLocation
                  : isSearch
                    ? `${coordinates![1].toFixed(4)}° N · ${coordinates![0].toFixed(4)}° E`
                    : 'BAY OF BENGAL · SECTOR 04'}
              </strong>
            </div>
            <div className="layer-controls">
              {layerOptions.map((layer) => {
                const Icon = layerIcons[layer as keyof typeof layerIcons],
                  pending =
                    isSearch ||
                    (!isLive && pendingLayers.has(layer)) ||
                    (isLive && layer === 'Forecast');
                return (
                  <button
                    key={layer}
                    className={layers.includes(layer) ? 'active' : ''}
                    onClick={() => toggleLayer(layer)}
                    disabled={pending}
                    title={
                      pending ? 'Awaiting backend data' : `Toggle ${layer}`
                    }
                  >
                    <Icon size={11} />
                    {layer}
                    {pending && <em>PENDING</em>}
                  </button>
                );
              })}
            </div>
          </div>
          <InvestigationMap
            analysis={analysis}
            coordinates={coordinates}
            replay={replay}
            activeLayers={layers}
            selectedVesselId={selected.id}
            mode={mode}
            playing={playing}
            onTogglePlay={() => {
              if (playing) {
                setPlaying(false);
                return;
              }
              if (replay >= 100) setReplay(0);
              setPlayDirection(1);
              setPlaying(true);
            }}
            onSelectVessel={(id) => {
              setSelectedId(id);
              const dossier = vesselDossiers[id];
              if (dossier) window.location.href = `/vessels/${dossier.slug}`;
            }}
          />
        </section>

        <aside className="workspace-side">
          {isSearch ? (
            <section className="coordinate-awaiting panel">
              <Radar />
              <small>LOCAL AREA INITIALIZED</small>
              <h2>Waiting for nearby evidence</h2>
              <p>
                The coordinates have centred the map. Connect the detection and
                AIS endpoints to populate spill geometry, nearby vessels, drift
                and attribution results.
              </p>
              <div>
                <span>
                  SPILL DETECTION <b>PENDING</b>
                </span>
                <span>
                  NEARBY AIS <b>PENDING</b>
                </span>
                <span>
                  ENVIRONMENT <b>PENDING</b>
                </span>
              </div>
            </section>
          ) : (
            <>
              <section className="vessel-panel panel">
                <header>
                  <div>
                    <small>AIS VESSEL INTELLIGENCE</small>
                    <h2>Suspect vessels</h2>
                  </div>
                  <span>{vessels.length} RANKED</span>
                </header>
                {isLive ? (
                  <div className="backend-data-notice">
                    BACKEND CANDIDATES · CONTEXTUAL AIS TRAFFIC
                  </div>
                ) : (
                  <div className="vessel-filters">
                    <label>
                      TIME WINDOW{' '}
                      <select>
                        <option>04:00 — 08:00</option>
                      </select>
                    </label>
                    <label>
                      DISTANCE{' '}
                      <select
                        value={distance}
                        onChange={(event) =>
                          setDistance(Number(event.target.value))
                        }
                      >
                        <option value="5">&lt; 5 km</option>
                        <option value="10">&lt; 10 km</option>
                        <option value="15">&lt; 15 km</option>
                      </select>
                    </label>
                  </div>
                )}
                <div className="vessel-ranking">
                  {vessels.map((vessel, index) => (
                    <button
                      key={vessel.id}
                      className={selected.id === vessel.id ? 'selected' : ''}
                      onClick={() => setSelectedId(vessel.id)}
                    >
                      <b>0{index + 1}</b>
                      <div>
                        <strong>{vessel.name}</strong>
                        <small>
                          {vessel.id} · {vessel.distanceKm} km
                        </small>
                      </div>
                      <em>{vessel.score}%</em>
                      <span>
                        {vessel.speed} kn · {vessel.heading}°
                      </span>
                    </button>
                  ))}
                </div>
              </section>
              <section className="attribution-panel panel">
                <header>
                  <div>
                    <small>EXPLAINABLE ATTRIBUTION</small>
                    <h2>Why {selected.name}?</h2>
                  </div>
                  <strong>{selected.score}%</strong>
                </header>
                <p>
                  {isLive
                    ? 'Backend attribution score enriched with the deterministic demo AIS track and vessel dossier.'
                    : 'Route, timing and reconstructed origin produce the strongest investigative correlation.'}
                </p>
                <div className="attribution-bars">
                  {selected.evidence.map((item) => (
                    <div key={item.label}>
                      <span>
                        {item.status === 'warning' ? '△' : '✓'} {item.label}
                      </span>
                      <b>{item.value}%</b>
                      <i>
                        <em style={{ width: `${item.value}%` }} />
                      </i>
                    </div>
                  ))}
                </div>
                <div className="attribution-actions">
                  <button
                    onClick={() => {
                      if (isLive) {
                        setMockDossierOpen(true);
                        return;
                      }
                      const dossier = vesselDossiers[selected.id];
                      if (dossier)
                        window.location.href = `/vessels/${dossier.slug}`;
                    }}
                  >
                    {isLive ? 'VIEW DEMO DOSSIER →' : 'VIEW VESSEL DOSSIER →'}
                  </button>
                  <button
                    disabled={reportGenerating}
                    onClick={async () => {
                      setReportGenerating(true);
                      setReportError('');
                      try {
                        await backendApi.generateReport();
                      } catch (error) {
                        setReportError(
                          error instanceof Error
                            ? error.message
                            : 'Report generation failed.',
                        );
                      } finally {
                        setReportGenerating(false);
                      }
                    }}
                  >
                    GENERATE REPORT ↗
                  </button>
                </div>
                {reportError && (
                  <p className="report-download-error">{reportError}</p>
                )}
                {sourceVessels.length > 1 && (
                  <button
                    className="compare-candidates"
                    onClick={() => setComparisonOpen(true)}
                  >
                    <Scale /> Compare top candidates
                  </button>
                )}
              </section>
            </>
          )}
        </aside>

        {isLive ? (
          <section className="replay-workspace live-analysis-replay panel">
            <button
              title="Play backward from detection to origin"
              onClick={() => {
                if (playing && playDirection === -1) {
                  setPlaying(false);
                  return;
                }
                setReplay((value) => (value <= 0 || value > 55 ? 55 : value));
                setPlayDirection(-1);
                setPlaying(true);
              }}
              className={
                playing && playDirection === -1
                  ? 'replay-play active'
                  : 'replay-play'
              }
            >
              ←
            </button>
            <button
              title="Play forward from detection"
              onClick={() => {
                if (playing && playDirection === 1) {
                  setPlaying(false);
                  return;
                }
                setReplay((value) => (value < 55 || value >= 100 ? 55 : value));
                setPlayDirection(1);
                setPlaying(true);
              }}
              className={
                playing && playDirection === 1
                  ? 'replay-play active'
                  : 'replay-play'
              }
            >
              →
            </button>
            <div className="replay-event">
              <small>
                SPILL MOVEMENT ·{' '}
                {playing
                  ? playDirection === -1
                    ? 'BACKTRACK PLAYING'
                    : 'FORWARD PLAYING'
                  : 'PAUSED'}
              </small>
              <strong>
                {replay < 48
                  ? 'RECONSTRUCTING TOWARD PROBABLE ORIGIN'
                  : replay < 58
                    ? 'SATELLITE DETECTION POSITION'
                    : 'PROJECTED FORWARD DIRECTION'}
              </strong>
            </div>
            <div className="replay-slider live-replay-slider">
              <input
                type="range"
                min="0"
                max="100"
                value={replay}
                onChange={(event) => {
                  setPlaying(false);
                  setReplay(Number(event.target.value));
                }}
                aria-label="Oil spill movement timeline"
              />
              <div>
                <button
                  style={{ left: '0%' }}
                  className="passed"
                  onClick={() => jumpTo(0, 'origin')}
                >
                  <i />
                  <span>ORIGIN</span>
                </button>
                <button
                  style={{ left: '55%' }}
                  className={replay >= 55 ? 'passed' : ''}
                  onClick={() => jumpTo(55)}
                >
                  <i />
                  <span>DETECTED</span>
                </button>
                <button
                  style={{ left: '100%' }}
                  className={replay >= 100 ? 'passed' : ''}
                  onClick={() => jumpTo(100, 'forecast')}
                >
                  <i />
                  <span>PROJECTED</span>
                </button>
              </div>
            </div>
            <button
              className="speed-control"
              onClick={() =>
                setSpeed((value) => (value === 1 ? 2 : value === 2 ? 4 : 1))
              }
            >
              {speed}×
            </button>
            <small className="keyboard-hint">
              ← BACKTRACK · → FORWARD · DRAG TO SCRUB
            </small>
          </section>
        ) : (
          <section className="replay-workspace panel">
            <button
              onClick={() => {
                setPlayDirection(1);
                setPlaying(!playing);
              }}
              className="replay-play"
            >
              {playing ? 'Ⅱ' : '▶'}
            </button>
            <button onClick={() => jumpTo(0)}>↺</button>
            <div className="replay-event" aria-live="polite">
              <small>INCIDENT REPLAY · {stage.label}</small>
              <strong>{stage.event}</strong>
            </div>
            <div className="replay-slider">
              <input
                type="range"
                min="0"
                max="100"
                value={replay}
                onChange={(event) => {
                  setPlaying(false);
                  setReplay(Number(event.target.value));
                }}
                aria-label="Incident timeline"
              />
              <div>
                {demoIncident.timeline.map((item) => (
                  <button
                    key={item.label}
                    style={{ left: `${item.value}%` }}
                    className={replay >= item.value ? 'passed' : ''}
                    onClick={() =>
                      jumpTo(
                        item.value,
                        item.value > 72 ? 'forecast' : 'analysis',
                      )
                    }
                  >
                    <i />
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <button
              className="speed-control"
              onClick={() =>
                setSpeed((value) => (value === 1 ? 2 : value === 2 ? 4 : 1))
              }
            >
              {speed}×
            </button>
            <small className="keyboard-hint">
              SPACE PLAY · ← → SCRUB
            </small>
          </section>
        )}
      </div>
      {!isSearch && <InvestigationInsights replay={replay} />}
      {mockDossierOpen && (
        <MockVesselDossier
          vesselId={selected.id}
          onClose={() => setMockDossierOpen(false)}
        />
      )}
      {comparisonOpen && (
        <CandidateComparison
          vessels={sourceVessels}
          onClose={() => setComparisonOpen(false)}
        />
      )}
    </section>
  );
}
