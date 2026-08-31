'use client';

import {
  Bird,
  Clock3,
  Droplets,
  Fish,
  Leaf,
  MapPin,
  ShieldAlert,
  TimerReset,
  Waves,
} from 'lucide-react';
import type { CSSProperties } from 'react';
import { demoIncident } from '../../data/demoIncident';

export default function InvestigationInsights({ replay }: { replay: number }) {
  const event =
    [...demoIncident.timeline].reverse().find((item) => replay >= item.value) ??
    demoIncident.timeline[0];
  const eventIndex = demoIncident.timeline.findIndex(
    (item) => item.value === event.value,
  );
  const risk = demoIncident.coastalRisk;
  const impact = demoIncident.impactAssessment;

  return (
    <div className="investigation-insights">
      <section className="story-panel panel">
        <header>
          <span><Clock3 /> Incident story</span>
          <b>{event.label}</b>
        </header>
        <h2>{event.event}</h2>
        <p>
          {replay < 43
            ? 'AIS positions are being evaluated against the reconstructed origin corridor.'
            : replay < 72
              ? 'The inferred discharge and early drift explain the slick position at detection.'
              : 'The detected boundary is projected using the demonstration wind and current vectors.'}
        </p>
        <div className="story-sequence">
          {demoIncident.timeline.map((item, index) => (
            <span key={item.label} className={index <= eventIndex ? 'passed' : ''}>
              <i />{item.label}
            </span>
          ))}
        </div>
      </section>
      <section className="coastal-risk-panel panel">
        <header>
          <span><ShieldAlert /> Coastal impact outlook</span>
          <b>{risk.level} risk</b>
        </header>
        <div className="coastal-risk-main">
          <div>
            <small>Estimated coastal arrival</small>
            <strong>{risk.estimatedArrival}</strong>
            <p><MapPin /> {risk.nearestCoast} · {risk.distanceKm} km away</p>
          </div>
          <div className="risk-gauge" style={{ '--risk': `${risk.confidence}%` } as CSSProperties}>
            <strong>{risk.confidence}%</strong><span>forecast confidence</span>
          </div>
        </div>
        <footer>
          <span><Waves /> Sensitive area: <b>{risk.sensitiveArea}</b></span>
          <span>Projected slick area: <b>{risk.projectedAreaKm2} km²</b></span>
        </footer>
      </section>
      <section className="impact-assessment panel">
        <header>
          <div>
            <span><Droplets /> Environmental impact estimate</span>
            <h2>Potential damage and recovery outlook</h2>
            <p>
              Screening estimates based on the demonstration spill geometry and
              stated assumptions. Field sampling is required for confirmation.
            </p>
          </div>
          <b>{impact.responsePriority}</b>
        </header>
        <div className="impact-metrics">
          <article>
            <Droplets />
            <small>Estimated oil released</small>
            <strong>{impact.estimatedVolume.minTonnes.toLocaleString()}–{impact.estimatedVolume.maxTonnes.toLocaleString()} t</strong>
            <span>{impact.estimatedVolume.confidence}% estimate confidence</span>
          </article>
          <article>
            <Leaf />
            <small>Marine vegetation</small>
            <strong>{impact.marineVegetation.risk} risk</strong>
            <span>Approx. {impact.marineVegetation.exposedAreaKm2} km² potentially exposed</span>
          </article>
          <article>
            <Fish />
            <small>Marine-life exposure</small>
            <strong>{impact.marineLife.risk} risk</strong>
            <span>{impact.marineLife.groups.join(' · ')}</span>
          </article>
          <article>
            <Waves />
            <small>Shoreline at risk</small>
            <strong>{impact.shoreline.exposureKm} km</strong>
            <span>Possible arrival in {impact.shoreline.arrivalWindow}</span>
          </article>
        </div>
        <div className="recovery-outlook">
          <div><TimerReset /><span><small>Open-water surface</small><strong>{impact.recovery.surface}</strong></span></div>
          <div><Leaf /><span><small>Coastal habitat</small><strong>{impact.recovery.coastalHabitat}</strong></span></div>
          <div><Bird /><span><small>Sensitive habitat</small><strong>{impact.recovery.sensitiveHabitat}</strong></span></div>
        </div>
        <footer>
          <ShieldAlert />
          <span>
            Volume is not calculated from area alone. This demo range assumes a
            representative slick thickness and must be replaced by backend or
            field-derived measurements in operational use.
          </span>
        </footer>
      </section>
    </div>
  );
}
