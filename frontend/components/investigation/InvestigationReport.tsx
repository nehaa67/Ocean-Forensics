'use client';
import { demoIncident, type VesselRecord } from '../../data/demoIncident';
import type { ImageAnalysisResult } from '../../services/analysisService';

export default function InvestigationReport({
  vessel,
  candidates,
  analysis = null,
  onClose,
}: {
  vessel: VesselRecord;
  candidates: VesselRecord[];
  analysis?: ImageAnalysisResult | null;
  onClose: () => void;
}) {
  const live = Boolean(analysis?.detected && analysis.geometry);
  const center = analysis?.geometry?.centroid;
  const origin = analysis?.drift?.end_point;
  const reportCandidates = live ? candidates : demoIncident.vessels;
  const fields = live
    ? [
        ['Detection', 'Just analyzed'],
        [
          'Location',
          center
            ? `${center[1].toFixed(5)}° N, ${center[0].toFixed(5)}° E`
            : 'Unavailable',
        ],
        [
          'Spill area',
          `${((analysis?.geometry?.area ?? 0) / 1_000_000).toFixed(2)} km²`,
        ],
        ['Spill pixels', String(analysis?.geometry?.pixel_count ?? 0)],
        [
          'Probable origin',
          origin
            ? `${origin.lat.toFixed(5)}° N, ${origin.lon.toFixed(5)}° E`
            : 'Not returned',
        ],
        ['Source CRS', analysis?.geometry?.crs ?? 'Not returned'],
      ]
    : [
        ['Detection', demoIncident.detectedAt],
        ['Location', demoIncident.location],
        ['Spill area', `${demoIncident.areaKm2} km²`],
        ['Detection confidence', `${demoIncident.detectionConfidence}%`],
        [
          'Probable origin',
          `${demoIncident.origin.coordinate[1]}° N, ${demoIncident.origin.coordinate[0]}° E`,
        ],
        ['Origin confidence', `${demoIncident.origin.confidence}%`],
      ];
  return (
    <div
      className="modal-backdrop report-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Investigation report"
    >
      <article className="report-modal">
        <header>
          <div className="brand">
            <i />
            OCEAN <b>FORENSICS</b>
          </div>
          <div>
            <button onClick={() => window.print()}>PRINT / EXPORT</button>
            <button onClick={onClose}>CLOSE ×</button>
          </div>
        </header>
        <p className="report-classification">
          INVESTIGATION REPORT ·{' '}
          {live ? 'LIVE BACKEND RESPONSE' : 'SYNTHETIC DEMONSTRATION DATA'}
        </p>
        <h1>Marine Oil Spill Attribution</h1>
        <p className="report-id">
          INCIDENT #{live ? 'TIFF-001' : demoIncident.id} · GENERATED{' '}
          {new Date().toLocaleString()}
        </p>
        <div className="report-grid">
          {fields.map(([key, value]) => (
            <div key={key}>
              <small>{key}</small>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
        <section className="report-candidate">
          <small>TOP CANDIDATE</small>
          <div>
            <h2>{vessel.name}</h2>
            <strong>{vessel.score}% ATTRIBUTION</strong>
          </div>
          <p>
            {vessel.id} · {vessel.type}
            {live
              ? ' · Vessel metadata pending'
              : ` · ${vessel.distanceKm} km from probable origin`}
          </p>
        </section>
        <section className="report-evidence">
          <small>SUPPORTING EVIDENCE</small>
          {vessel.evidence.slice(0, 4).map((item) => (
            <div key={item.label}>
              <span>✓ {item.label}</span>
              <b>{item.value}%</b>
            </div>
          ))}
        </section>
        <section className="report-method">
          <small>METHOD SUMMARY</small>
          <p>
            {live
              ? 'The backend extracted spill geometry from the supplied GeoTIFF mask, reconstructed a backward drift trajectory, and returned prototype vessel-correlation scores. Vessel identity and complete AIS tracks are not present in this response.'
              : 'SAR segmentation identified the slick boundary. Ocean drift was backtracked to a probable origin corridor, then correlated against deterministic AIS trajectories within the incident time window.'}
          </p>
        </section>
        <section className="candidate-comparison">
          <small>CANDIDATE COMPARISON</small>
          {reportCandidates.map((candidate, index) => (
            <div key={candidate.id}>
              <b>0{index + 1}</b>
              <span>{candidate.name}</span>
              <em>{candidate.score}%</em>
              <i>
                <span style={{ width: `${candidate.score}%` }} />
              </i>
            </div>
          ))}
        </section>
        <footer>
          <b>ASSESSMENT CLASSIFICATION: INVESTIGATIVE LEAD</b>
          <span>
            This report presents probabilistic correlations—not confirmed
            liability or legally conclusive source attribution.
          </span>
        </footer>
      </article>
    </div>
  );
}
