import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import {
  demoIncident,
  getVesselBySlug,
  vesselDossiers,
} from '../../../data/demoIncident';

export const generateStaticParams = () =>
  Object.values(vesselDossiers).map((item) => ({ slug: item.slug }));
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const record = getVesselBySlug((await params).slug);
  return record
    ? {
        title: `${record.vessel.name} — Ocean Forensics`,
        description: `Synthetic maritime intelligence dossier for ${record.vessel.name}.`,
      }
    : { title: 'Vessel not found' };
}

export default async function VesselPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const record = getVesselBySlug((await params).slug);
  if (!record) notFound();
  const { vessel, dossier } = record;
  return (
    <main className="dossier-page">
      <header className="dossier-nav">
        <Link href="/#investigation" className="brand">
          <i />
          OCEAN <b>FORENSICS</b>
        </Link>
        <div>
          <span>SECURE VESSEL REGISTRY</span>
          <b>SYNTHETIC AIS · DEMO DATA</b>
        </div>
      </header>
      <section className="dossier-hero">
        <div className="dossier-image">
          <Image
            fill
            priority
            sizes="(max-width: 900px) 100vw, 58vw"
            src={dossier.image}
            alt={`Reference image for ${vessel.name}`}
          />
          <div className="dossier-image-grid" />
          <span>REFERENCE IMAGERY · NOT LIVE SATELLITE DATA</span>
        </div>
        <div className="dossier-intro">
          <small>VESSEL INTELLIGENCE DOSSIER / {vessel.id}</small>
          <h1>{vessel.name}</h1>
          <p>{vessel.type}</p>
          <div className="dossier-flag">
            <b>{dossier.flag}</b>
            <span>
              <small>FLAG STATE</small>
              <strong>{dossier.country}</strong>
            </span>
          </div>
          <div className="dossier-score">
            <span>
              <small>ATTRIBUTION SCORE</small>
              <strong>{vessel.score}%</strong>
            </span>
            <i>
              <em style={{ width: `${vessel.score}%` }} />
            </i>
            <p>Highest-ranked vessel for incident #{demoIncident.id}</p>
          </div>
          <Link className="back-investigation" href="/#investigation">
            ← RETURN TO INVESTIGATION
          </Link>
        </div>
      </section>
      <section className="dossier-body">
        <div className="dossier-section identity-section">
          <header>
            <small>01 / IDENTITY & REGISTRY</small>
            <h2>Vessel particulars</h2>
          </header>
          <div className="particulars-grid">
            {[
              ['IMO number', vessel.id.replace('IMO ', '')],
              ['MMSI', dossier.mmsi],
              ['Call sign', dossier.callSign],
              ['Year built', String(dossier.built)],
              ['Operator', dossier.operator],
              ['Home port', dossier.homePort],
              ['Navigation status', dossier.navigationStatus],
              ['Declared cargo', dossier.cargo],
            ].map(([key, value]) => (
              <div key={key}>
                <small>{key}</small>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="dossier-section dimensions-section">
          <header>
            <small>02 / PHYSICAL PROFILE</small>
            <h2>Dimensions</h2>
          </header>
          <div className="dimension-vessel">
            <div className="ship-silhouette">
              <i />
              <span className="length-line">{dossier.lengthM} M LENGTH</span>
              <span className="beam-line">{dossier.beamM} M BEAM</span>
            </div>
          </div>
          <div className="dimension-stats">
            {[
              ['Draught', `${dossier.draughtM} m`],
              ['Deadweight', `${dossier.deadweightT.toLocaleString()} t`],
              ['Gross tonnage', dossier.grossTonnage.toLocaleString()],
            ].map(([key, value]) => (
              <div key={key}>
                <small>{key}</small>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="dossier-section live-section">
          <header>
            <small>03 / LAST AIS STATE</small>
            <h2>Movement intelligence</h2>
          </header>
          <div className="movement-grid">
            <div>
              <small>POSITION</small>
              <strong>
                {vessel.position[1].toFixed(4)}° N<br />
                {vessel.position[0].toFixed(4)}° E
              </strong>
            </div>
            <div>
              <small>SPEED</small>
              <strong>
                {vessel.speed}
                <em> kn</em>
              </strong>
            </div>
            <div>
              <small>HEADING</small>
              <strong>
                {vessel.heading}
                <em>°</em>
              </strong>
            </div>
            <div>
              <small>ORIGIN DISTANCE</small>
              <strong>
                {vessel.distanceKm}
                <em> km</em>
              </strong>
            </div>
          </div>
          <div className="route-summary">
            <i />
            <div>
              <small>HISTORICAL TRACK</small>
              <strong>{vessel.track.length} correlated AIS positions</strong>
              <span>
                Route intersects the reconstructed origin corridor within the
                relevant time window.
              </span>
            </div>
          </div>
        </div>
        <div className="dossier-section evidence-section">
          <header>
            <small>04 / ATTRIBUTION ENGINE</small>
            <h2>Evidence breakdown</h2>
          </header>
          <div className="dossier-evidence">
            {vessel.evidence.map((item) => (
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
          <div className="assessment-note">
            <b>INVESTIGATIVE ASSESSMENT</b>
            <p>
              This vessel is a probabilistic lead. The score does not establish
              legal liability or confirm the discharge source.
            </p>
          </div>
        </div>
      </section>
      <footer className="dossier-footer">
        <span>OCEAN FORENSICS · INCIDENT #{demoIncident.id}</span>
        <span>DEMONSTRATION DOSSIER</span>
        <Link href="/#investigation">BACK TO CASE ↑</Link>
      </footer>
    </main>
  );
}
