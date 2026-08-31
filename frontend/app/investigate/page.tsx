'use client';

import { useEffect, useRef, useState } from 'react';

import InvestigationDashboard from '../../components/investigation/InvestigationDashboard';
import GlobalSpillMonitor from '../../components/global/GlobalSpillMonitor';

import type { ImageAnalysisResult } from '../../services/analysisService';

export default function InvestigatePage() {
  const globalMonitor = useRef<HTMLElement>(null);
  const dashboard = useRef<HTMLElement>(null);

  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);

  const [liveAnalysis, setLiveAnalysis] = useState<ImageAnalysisResult | null>(
    null,
  );

  const [searchCoordinates, setSearchCoordinates] = useState<
    [number, number] | null
  >(null);

  useEffect(() => {
    if (!selectedIncident) return;

    const frame = window.requestAnimationFrame(() => {
      dashboard.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [selectedIncident]);

  return (
    <main className="site-shell investigate-shell">
      <header className="site-header investigate-site-header">
        <a className="brand investigate-brand" href="/">
          <img src="/favicon.png" alt="Ocean Forensics" />
          <i />
          OCEAN <b>FORENSICS</b>
        </a>
        <nav className="investigate-header-nav" aria-label="Primary navigation">
          <a href="/">Home</a>
          <a className="header-investigate-btn" href="/awareness">
            OIL SPILL AWARENESS <span>↗</span>
          </a>
        </nav>
      </header>
      <GlobalSpillMonitor
        sectionRef={globalMonitor}
        onAnalysis={(result) => {
          setLiveAnalysis(result);
          setSearchCoordinates(null);

          if (result.detected) {
            setSelectedIncident('live');

            window.setTimeout(
              () =>
                dashboard.current?.scrollIntoView({
                  behavior: 'smooth',
                }),
              120,
            );
          }
        }}
        onCoordinates={(coordinates) => {
          setLiveAnalysis(null);
          setSearchCoordinates(coordinates);
          setSelectedIncident('coordinates');

          window.setTimeout(
            () =>
              dashboard.current?.scrollIntoView({
                behavior: 'smooth',
              }),
            80,
          );
        }}
      />

      {selectedIncident && (
        <InvestigationDashboard
          sectionRef={dashboard}
          analysis={selectedIncident === 'live' ? liveAnalysis : null}
          coordinates={
            selectedIncident === 'coordinates' ? searchCoordinates : null
          }
        />
      )}
    </main>
  );
}
