'use client';
import { type FormEvent, type RefObject, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  AlertTriangle,
  FileUp,
  Globe2,
  LocateFixed,
  MapPin,
  Radar,
  ScanSearch,
} from 'lucide-react';
import AnalyzeImageModal from '../analysis/AnalyzeImageModal';
import type { ImageAnalysisResult } from '../../services/analysisService';
import { globalSpills } from '../../data/demoIncident';

const GlobalSpillMap = dynamic(() => import('./GlobalSpillMap'), {
  ssr: false,
  loading: () => (
    <div className="global-map-loading">
      <i />
      Loading global overview…
    </div>
  ),
});

export default function GlobalSpillMonitor({
  sectionRef,
  onCoordinates,
  onAnalysis,
}: {
  sectionRef: RefObject<HTMLElement | null>;
  onCoordinates: (coordinates: [number, number]) => void;
  onAnalysis: (result: ImageAnalysisResult) => void;
}) {
  const [method, setMethod] = useState<'coordinates' | 'geotiff'>(
    'coordinates',
  );
  const [latitude, setLatitude] = useState('17.5368'),
    [longitude, setLongitude] = useState('83.6685');
  const [error, setError] = useState(''),
    [analyzeOpen, setAnalyzeOpen] = useState(false);
  const [selectedSpill, setSelectedSpill] = useState(globalSpills[0].id);
  const activeSpill =
    globalSpills.find((spill) => spill.id === selectedSpill) ?? globalSpills[0];
  const openArea = (event: FormEvent) => {
    event.preventDefault();
    const lat = Number(latitude),
      lon = Number(longitude);
    if (
      !Number.isFinite(lat) ||
      !Number.isFinite(lon) ||
      lat < -90 ||
      lat > 90 ||
      lon < -180 ||
      lon > 180
    ) {
      setError('Enter valid latitude (−90 to 90) and longitude (−180 to 180).');
      return;
    }
    setError('');
    onCoordinates([lon, lat]);
  };
  return (
    <section
      ref={sectionRef}
      className="global-monitor intake-section"
      id="investigation-intake"
    >
      <header className="global-header intake-header">
        <div>
          <p>NEW INVESTIGATION</p>
          <h1>Create an investigation</h1>
          <span>
            Provide a location or upload satellite data to open the nearby-area
            workspace.
          </span>
        </div>
        <div className="global-live">
          <i /> SYSTEM READY<small>SECURE ORGANISATION ACCESS</small>
        </div>
      </header>
      <div className="intake-flow" aria-label="Investigation flow">
        <span className="active">
          <b>01</b>Add location
        </span>
        <i>→</i>
        <span>
          <b>02</b>Review area
        </span>
        <i>→</i>
        <span>
          <b>03</b>Investigate
        </span>
        <i>→</i>
        <span>
          <b>04</b>Identify source
        </span>
      </div>
      <div className="intake-grid">
        <section className="intake-card panel">
          <header>
            <small>Choose your starting point</small>
            <h2>How would you like to begin?</h2>
            <p>The map opens only after an investigation area is supplied.</p>
          </header>
          <div className="intake-methods">
            <button
              className={method === 'coordinates' ? 'active' : ''}
              onClick={() => setMethod('coordinates')}
            >
              <LocateFixed />
              <span>
                <strong>Enter coordinates</strong>
                <small>Open a nearby-area search map</small>
              </span>
            </button>
            <button
              className={method === 'geotiff' ? 'active' : ''}
              onClick={() => setMethod('geotiff')}
            >
              <FileUp />
              <span>
                <strong>Open investigation</strong>
                <small>Sanchi demo or complete evidence package</small>
              </span>
            </button>
          </div>
          {method === 'coordinates' ? (
            <form className="coordinate-form" onSubmit={openArea}>
              <div>
                <label>
                  LATITUDE
                  <input
                    value={latitude}
                    onChange={(event) => setLatitude(event.target.value)}
                    inputMode="decimal"
                    placeholder="17.5368"
                  />
                </label>
                <label>
                  LONGITUDE
                  <input
                    value={longitude}
                    onChange={(event) => setLongitude(event.target.value)}
                    inputMode="decimal"
                    placeholder="83.6685"
                  />
                </label>
              </div>
              {error && <p className="coordinate-error">{error}</p>}
              <button type="submit">
                <Radar size={16} />
                OPEN NEARBY AREA <span>→</span>
              </button>
              <small>
                Coordinates define the search centre. Spill geometry and nearby
                vessels require backend data.
              </small>
            </form>
          ) : (
            <div className="geotiff-entry">
              <ScanSearch size={38} />
              <strong>Backend investigation pipeline</strong>
              <p>
                Run the frozen Sanchi case, or upload Sentinel-1, wind,
                currents and AIS evidence for a new investigation.
              </p>
              <button onClick={() => setAnalyzeOpen(true)}>
                <FileUp size={16} />
                SELECT .TIF / .TIFF <span>→</span>
              </button>
            </div>
          )}
        </section>
        <aside className="intake-explainer panel">
          <small>Investigation process</small>
          <ol>
            <li>
              <b>01</b>
              <div>
                <strong>We locate the area</strong>
                <span>
                  GeoTIFF metadata or entered coordinates determine the map
                  viewport.
                </span>
              </div>
            </li>
            <li>
              <b>02</b>
              <div>
                <strong>We gather nearby evidence</strong>
                <span>
                  The system requests spill detections, AIS tracks and
                  environmental data near the area.
                </span>
              </div>
            </li>
            <li>
              <b>03</b>
              <div>
                <strong>You review the investigation</strong>
                <span>
                  Analysts inspect geometry, movement, nearby vessels and
                  attribution evidence.
                </span>
              </div>
            </li>
          </ol>
          <div className="intake-note">
            <Radar size={17} />
            <span>
              <b>Focused search area</b>The platform opens only the
              investigation area supplied by your organisation.
            </span>
          </div>
        </aside>
      </div>
      <section className="world-overview" aria-labelledby="world-overview-title">
        <header className="world-overview-header">
          <div>
            <span>
              <Globe2 size={18} /> Global awareness
            </span>
            <h2 id="world-overview-title">Reported oil spills worldwide</h2>
            <p>
              Explore representative incidents before opening a focused
              investigation. All incidents shown here use demonstration data.
            </p>
          </div>
          <div className="overview-stats">
            <span>
              <strong>{globalSpills.length}</strong>Active incidents
            </span>
            <span>
              <strong>
                {globalSpills.filter((spill) => spill.severity === 'HIGH').length}
              </strong>
              High priority
            </span>
            <span>
              <strong>
                {globalSpills.reduce((total, spill) => total + spill.area, 0).toFixed(1)}
              </strong>
              km² monitored
            </span>
          </div>
        </header>
        <div className="world-overview-grid">
          <div className="world-map-panel">
            <GlobalSpillMap onSelect={setSelectedSpill} />
            <div className="world-map-legend">
              <span><i className="high" />High</span>
              <span><i className="medium" />Medium</span>
              <span><i className="low" />Low</span>
              <b>Demonstration data</b>
            </div>
          </div>
          <aside className="world-incident-panel">
            <div className="selected-incident">
              <span className={`incident-priority ${activeSpill.severity.toLowerCase()}`}>
                <AlertTriangle size={14} /> {activeSpill.severity} priority
              </span>
              <h3>{activeSpill.name}</h3>
              <p><MapPin size={15} /> {activeSpill.location}</p>
              <dl>
                <div><dt>Detected</dt><dd>{activeSpill.detected}</dd></div>
                <div><dt>Estimated area</dt><dd>{activeSpill.area} km²</dd></div>
                <div><dt>Confidence</dt><dd>{activeSpill.confidence}%</dd></div>
                <div><dt>Status</dt><dd>{activeSpill.status}</dd></div>
              </dl>
              <button onClick={() => onCoordinates(activeSpill.coordinate)}>
                Open nearby investigation <span>→</span>
              </button>
            </div>
            <div className="incident-list" aria-label="Mock global incidents">
              {globalSpills.map((spill) => (
                <button
                  key={spill.id}
                  className={spill.id === activeSpill.id ? 'active' : ''}
                  onClick={() => setSelectedSpill(spill.id)}
                >
                  <i className={spill.severity.toLowerCase()} />
                  <span><strong>{spill.name}</strong><small>{spill.location}</small></span>
                  <b>{spill.area} km²</b>
                </button>
              ))}
            </div>
          </aside>
        </div>
      </section>
      {analyzeOpen && (
        <AnalyzeImageModal
          onClose={() => setAnalyzeOpen(false)}
          onResult={onAnalysis}
        />
      )}
    </section>
  );
}
