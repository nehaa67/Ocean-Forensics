'use client';
import { Navigation, Ship, X } from 'lucide-react';
import { backendDemoVessels } from '../../data/backendDemo';

export default function MockVesselDossier({
  vesselId,
  onClose,
}: {
  vesselId: string;
  onClose: () => void;
}) {
  const normalizedId = vesselId.trim().toUpperCase();
  const vessel = backendDemoVessels.find(
    (item) =>
      item.id.toUpperCase() === normalizedId ||
      item.name.toUpperCase() === normalizedId ||
      item.imo.toUpperCase() === normalizedId,
  );
  if (!vessel) return null;
  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={`${vessel.name} vessel dossier`}
    >
      <section className="mock-vessel-dossier panel">
        <header>
          <div>
            <small>VESSEL RECORD · {vessel.id}</small>
            <h2>
              {vessel.flag} {vessel.name}
            </h2>
            <p>
              {vessel.type} · {vessel.country}
            </p>
          </div>
          <button onClick={onClose}>
            <X size={16} />
          </button>
        </header>
        <div className="mock-vessel-visual">
          {vessel.image ? (
            <img src={vessel.image} alt={`${vessel.name} tanker reference`} />
          ) : (
            <Ship size={58} />
          )}
          <span>REFERENCE IMAGERY · DEMONSTRATION DOSSIER</span>
        </div>
        <div className="mock-vessel-facts">
          {[
            ['IMO', vessel.imo],
            ['MMSI', vessel.mmsi],
            ['CALL SIGN', vessel.callSign],
            ['BUILT', vessel.built],
            ['LENGTH', `${vessel.lengthM} m`],
            ['BEAM', `${vessel.beamM} m`],
            ['DRAUGHT', `${vessel.draughtM} m`],
            ['DEADWEIGHT', `${vessel.deadweightT.toLocaleString()} t`],
            ['SPEED', `${vessel.speed} kn`],
            ['HEADING', `${vessel.heading}°`],
            ['DISTANCE', `${vessel.distanceKm} km`],
            ['HOME PORT', vessel.homePort],
          ].map(([label, value]) => (
            <div key={label}>
              <small>{label}</small>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
        <section>
          <small>OPERATION / CARGO</small>
          <p>
            {vessel.operator} · {vessel.cargo}
          </p>
        </section>
        <section>
          <small>AIS TRACK</small>
          <p>
            <Navigation size={12} />
            {vessel.track.length} recorded positions · {vessel.timestamps[0]} —{' '}
            {vessel.timestamps.at(-1)}
          </p>
        </section>
        <footer>
          Demo vessel record · Live AIS metadata will replace these values when connected
        </footer>
      </section>
    </div>
  );
}
