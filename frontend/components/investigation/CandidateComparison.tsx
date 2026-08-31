'use client';

import { CheckCircle2, X } from 'lucide-react';
import type { VesselRecord } from '../../data/demoIncident';

export default function CandidateComparison({
  vessels,
  onClose,
}: {
  vessels: VesselRecord[];
  onClose: () => void;
}) {
  const candidates = vessels.slice(0, 3);
  const factors = candidates[0]?.evidence.map((item) => item.label) ?? [];

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className="comparison-modal panel">
        <header>
          <div>
            <small>CANDIDATE COMPARISON</small>
            <h2>Why the leading vessel ranks first</h2>
            <p>
              Compare the evidence behind each attribution score. These demo
              rankings indicate investigative probability, not legal certainty.
            </p>
          </div>
          <button onClick={onClose} aria-label="Close comparison"><X /></button>
        </header>
        <div className="comparison-table">
          <div className="comparison-row comparison-head">
            <span>Evidence</span>
            {candidates.map((vessel, index) => (
              <strong key={vessel.id} className={index === 0 ? 'leader' : ''}>
                <small>#{index + 1}</small>{vessel.name}<b>{vessel.score}%</b>
              </strong>
            ))}
          </div>
          {factors.map((factor, factorIndex) => (
            <div className="comparison-row" key={factor}>
              <span>{factor}</span>
              {candidates.map((vessel, index) => {
                const value = vessel.evidence[factorIndex]?.value ?? 0;
                return (
                  <div key={vessel.id} className={index === 0 ? 'leader' : ''}>
                    <i><em style={{ width: `${value}%` }} /></i>
                    <b>{value}%</b>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <footer>
          <CheckCircle2 />
          <p>
            <strong>{candidates[0]?.name}</strong> has the strongest combined
            spatial, temporal, trajectory and origin consistency across this
            demonstration dataset.
          </p>
        </footer>
      </section>
    </div>
  );
}
