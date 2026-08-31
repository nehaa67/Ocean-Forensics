'use client';

import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import {
  MapPin,
  Satellite,
  ScanSearch,
  Waves,
  Ship,
  Target,
  FileSearch,
} from 'lucide-react';

export default function Home() {
  const root = useRef<HTMLElement>(null);

  const briefs = [
    {
      location: 'BAY OF BENGAL',
      title: 'SPILL DETECTION',
      description: 'Satellite anomaly detected during SAR pass.',
      meta: 'SAR · 29 AUG 2026 · PASS 04',
      image: '/spill-1.png',
    },
    {
      location: 'ARABIAN SEA',
      title: 'VESSEL / SPILL CORRELATION',
      description: 'AIS track intersects detected anomaly.',
      meta: 'AIS · 28 AUG 2026 · CORRELATION',
      image: '/spill-2.png',
    },
    {
      location: 'EASTERN COAST',
      title: 'NEW SATELLITE PASS',
      description: 'Fresh imagery available for analysis.',
      meta: 'SAR · 27 AUG 2026 · PASS 07',
      image: '/spill-3.png',
    },
    {
      location: 'MARITIME WATCH',
      title: 'ACTIVE INVESTIGATIONS',
      description: 'Three cases currently under attribution.',
      meta: 'LIVE · SYSTEM STATUS',
      image: '/spill-4.png',
    },
  ];
  const features = [
    {
      icon: Satellite,
      title: 'SATELLITE SPILL DETECTION',
      backTitle: 'SAR-BASED ANALYSIS',
      description:
        'Analyse satellite imagery to identify potential oil spill anomalies across large maritime regions.',
    },
    {
      icon: ScanSearch,
      title: 'SPILL CHARACTERISATION',
      backTitle: 'GEOMETRY & EXTENT',
      description:
        'Extract spill boundaries and geometric properties to better understand the detected anomaly.',
    },
    {
      icon: Waves,
      title: 'DRIFT RECONSTRUCTION',
      backTitle: 'TRACE THE ORIGIN',
      description:
        'Use oceanographic and environmental data to trace the slick backward toward its probable origin.',
    },
    {
      icon: Ship,
      title: 'AIS CORRELATION',
      backTitle: 'VESSEL TRACK ANALYSIS',
      description:
        'Reconstruct vessel movement around the suspected origin window using historical AIS tracks.',
    },
    {
      icon: Target,
      title: 'SUSPECT RANKING',
      backTitle: 'EVIDENCE-BASED SCORING',
      description:
        'Score potential vessels based on proximity, trajectory and behavioural anomalies.',
    },
    {
      icon: FileSearch,
      title: 'FORENSIC INVESTIGATION',
      backTitle: 'FROM SIGNAL TO EVIDENCE',
      description:
        'Transform satellite observations and maritime intelligence into a focused investigation.',
    },
  ];

  const [comparisonPosition, setComparisonPosition] = useState(50);

  const [briefIndex, setBriefIndex] = useState(0);

  useEffect(() => {
    if (
      !root.current ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    )
      return;

    const context = gsap.context(() => {
      gsap
        .timeline({ defaults: { ease: 'power3.out' } })
        .from('[data-nav]', {
          y: -20,
          opacity: 0,
          duration: 0.65,
        })
        .from(
          '[data-hero-copy]',
          {
            y: 35,
            opacity: 0,
            duration: 0.9,
          },
          '-=.25',
        );
    }, root);

    return () => context.revert();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setBriefIndex((current) => (current + 1) % briefs.length);
    }, 6000);

    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    let isAutoScrolling = false;
    let unlockTimer: ReturnType<typeof setTimeout>;

    const handleWheel = (event: WheelEvent) => {
      const hero = document.querySelector('.hero-section');
      const comparison = document.querySelector('.comparison-section');

      if (!hero || !comparison) return;

      // Block ALL wheel events during automatic scrolling
      if (isAutoScrolling) {
        event.preventDefault();
        return;
      }

      const comparisonRect = comparison.getBoundingClientRect();
      const heroRect = hero.getBoundingClientRect();

      // HERO → COMPARISON
      if (
        event.deltaY > 0 &&
        heroRect.top > -100 &&
        heroRect.bottom > window.innerHeight * 0.5
      ) {
        event.preventDefault();
        isAutoScrolling = true;

        comparison.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });

        clearTimeout(unlockTimer);
        unlockTimer = setTimeout(() => {
          isAutoScrolling = false;
        }, 1000);

        return;
      }

      // COMPARISON → HERO
      if (
        event.deltaY < 0 &&
        comparisonRect.top >= -100 &&
        comparisonRect.top < 150
      ) {
        event.preventDefault();
        isAutoScrolling = true;

        hero.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });

        clearTimeout(unlockTimer);
        unlockTimer = setTimeout(() => {
          isAutoScrolling = false;
        }, 1000);
      }
    };

    window.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      window.removeEventListener('wheel', handleWheel);
      clearTimeout(unlockTimer);
    };
  }, []);

  const currentBrief = briefs[briefIndex];

  const nextBrief = () => {
    setBriefIndex((current) => (current + 1) % briefs.length);
  };

  const previousBrief = () => {
    setBriefIndex((current) => (current - 1 + briefs.length) % briefs.length);
  };

  return (
    <main ref={root} className="site-shell">
      {/* STICKY GLOBAL HEADER */}
      <header className="site-header" data-nav>
        <div className="brand">
          <img src="/favicon.png" alt="Ocean Forensics" />
          <i />
          OCEAN <b>FORENSICS</b>
        </div>

        <nav className="site-header-nav" aria-label="Primary navigation">
          <a href="/awareness">AWARENESS</a>
          <button
          className="header-investigate-btn"
          onClick={() => {
            window.location.href = '/investigate';
          }}
        >
          OPEN INVESTIGATION
          <span>↗</span>
          </button>
        </nav>
      </header>

      {/* HERO */}
      <section className="hero-section">
        <div className="hero-image" />
        <div className="hero-shade" />
        <div className="technical-grid" />

        <div className="hero-copy hero-copy-editorial" data-hero-copy>
          <div className="hero-copy-kicker">
            <i /> MARITIME INTELLIGENCE / 01
          </div>

          <div className="hero-copy-line">
            <span>SPILLS</span>
            <em>LEAVE</em>
          </div>

          <strong>
            EVIDENCE<span>.</span>
          </strong>

          <p>From satellite detection to vessel attribution.</p>
        </div>

        <div className="intelligence-carousel">
          <div className="intelligence-header">
            <span>LIVE MARITIME FEED</span>

            <span className="intelligence-count">
              {String(briefIndex + 1).padStart(2, '0')} / 04
            </span>
          </div>

          <div className="intelligence-image">
            <img src={currentBrief.image} alt={currentBrief.title} />
          </div>

          <div className="intelligence-content" key={briefIndex}>
            <div className="intelligence-location">
              <MapPin className="location-pin" size={11} />
              {currentBrief.location}
            </div>

            <h3>{currentBrief.title}</h3>
            <p>{currentBrief.description}</p>
            <span className="intelligence-meta">{currentBrief.meta}</span>
          </div>

          <div className="intelligence-footer">
            <div className="intelligence-dots">
              {briefs.map((_, index) => (
                <button
                  key={index}
                  className={index === briefIndex ? 'active' : ''}
                  aria-label={`Feed ${index + 1}`}
                  onClick={() => setBriefIndex(index)}
                />
              ))}
            </div>

            <button
              className="view-analysis"
              onClick={() => {
                window.location.href = '/investigate';
              }}
            >
              VIEW ANALYSIS
            </button>
          </div>
        </div>

        <button
          type="button"
          className="launch-button trace-button stable-launch-button"
          onClick={() => {
            window.location.href = '/investigate';
          }}
        >
          <span className="launch-radar">
            <i />
            <em />
          </span>

          <span className="launch-copy">
            <small>GLOBAL SURVEILLANCE</small>
            <strong>OPEN SPILL MONITOR</strong>
          </span>

          <span className="launch-arrow">↗</span>
        </button>

        <div className="hero-meta">
          <span>SCROLL TO KNOW MORE ↓</span>
        </div>
      </section>

      <section className="comparison-section">
        <div className="comparison-layout">
          {/* LEFT — INFORMATION */}
          <div className="comparison-info">
            <span className="section-kicker">DETECTION PIPELINE</span>

            <h2>
              FROM RAW DATA
              <span> TO EVIDENCE.</span>
            </h2>

            <p className="comparison-description">
              Our AI transforms raw satellite imagery into actionable evidence,
              identifying potential oil spills and defining their boundaries for
              further investigation.
            </p>

            <div className="comparison-steps">
              <div className="comparison-step">
                <span>01</span>
                <div>
                  <strong>SATELLITE IMAGERY</strong>
                  <p>Raw SAR imagery captured over maritime regions.</p>
                </div>
              </div>

              <div className="comparison-step">
                <span>02</span>
                <div>
                  <strong>AI ANALYSIS</strong>
                  <p>Detection models analyze anomalies in the imagery.</p>
                </div>
              </div>

              <div className="comparison-step">
                <span>03</span>
                <div>
                  <strong>SPILL BOUNDARY</strong>
                  <p>Detected regions are isolated for investigation.</p>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT — IMAGE COMPARISON */}
          <div className="comparison-visual">
            <div
              className="comparison-frame"
              style={
                {
                  '--comparison-position': `${comparisonPosition}%`,
                } as React.CSSProperties
              }
            >
              {/* AFTER — always full size */}
              <img
                src="/spill-after.png"
                alt="AI oil spill detection"
                className="comparison-image comparison-after"
              />

              {/* BEFORE — always full size, only clipped */}
              <img
                src="/spill-before.png"
                alt="Raw satellite imagery"
                className="comparison-image comparison-before"
              />

              {/* DIVIDER */}
              <div className="comparison-divider">
                <div className="comparison-handle">
                  <span>‹</span>
                  <span>›</span>
                </div>
              </div>

              {/* LABELS */}
              <div className="comparison-label comparison-label-before">
                RAW DATA
              </div>

              <div className="comparison-label comparison-label-after">
                AI DETECTION
              </div>

              {/* SLIDER */}
              <input
                type="range"
                min="0"
                max="100"
                value={comparisonPosition}
                onChange={(e) => setComparisonPosition(Number(e.target.value))}
                className="comparison-slider"
                aria-label="Compare raw satellite image and AI detection"
              />
            </div>

            <div className="comparison-caption">
              <span>BEFORE</span>
              <span>AFTER</span>
            </div>
          </div>
        </div>
      </section>

      {/* CORE CAPABILITIES */}
      <section className="capabilities-section">
        <div className="capabilities-header">
          <div className="capabilities-kicker">
            <p>OCEAN FORENSICS / CORE CAPABILITIES</p>
          </div>

          <h2>
            WHY <span>OCEAN FORENSICS?</span>
          </h2>

          <p className="capabilities-intro">
            An integrated intelligence pipeline that connects satellite
            detection with vessel attribution.
          </p>
        </div>

        <div className="capabilities-grid">
          {features.map((feature, index) => {
            const Icon = feature.icon;

            return (
              <div className="feature-card" key={feature.title}>
                <div className="feature-card-inner">
                  {/* FRONT */}
                  <div className="feature-card-front">
                    <div className="feature-number">
                      {String(index + 1).padStart(2, '0')}
                    </div>

                    <Icon className="feature-icon" strokeWidth={1.5} />

                    <h3>{feature.title}</h3>

                    <span className="feature-hover-hint">
                      HOVER TO EXPLORE +
                    </span>
                  </div>

                  {/* BACK */}
                  <div className="feature-card-back">
                    <div className="feature-back-top">
                      <span>
                        {String(index + 1).padStart(2, '0')} / CAPABILITY
                      </span>
                      <Icon size={22} strokeWidth={1.5} />
                    </div>

                    <div className="feature-back-content">
                      <h3>{feature.backTitle}</h3>
                      <p>{feature.description}</p>
                    </div>

                    <div className="feature-back-line" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="capabilities-footer">
          <span>DETECTION</span>
          <i />
          <span>RECONSTRUCTION</span>
          <i />
          <span>CORRELATION</span>
          <i />
          <span>ATTRIBUTION</span>
        </div>
      </section>

      <footer className="site-footer">
        <div className="footer-main">
          <div className="footer-identity">
            <div className="brand footer-brand">
              <img src="/favicon.png" alt="Ocean Forensics" />
              <i />
              OCEAN <b>FORENSICS</b>
            </div>

            <p>
              Satellite intelligence for detecting marine spills, reconstructing
              their origin, and identifying responsible vessels.
            </p>
          </div>

          <div className="footer-block">
            <small>PLATFORM</small>
            <a href="/investigate">Create investigation</a>
            <a href="/investigate">Investigation dashboard</a>
            <a href="/investigate">Evidence analysis</a>
            <a href="/awareness">Oil spill awareness</a>
          </div>

          <div className="footer-block">
            <small>DATA FUSION</small>
            <span>Sentinel-1 SAR</span>
            <span>AIS vessel tracks</span>
            <span>Ocean drift models</span>
          </div>

          <div className="footer-status">
            <small>NETWORK STATUS</small>

            <strong>
              <i /> ALL SYSTEMS OPERATIONAL
            </strong>

            <span>BAY OF BENGAL / SECTOR 04</span>
          </div>
        </div>

        <div className="footer-bottom">
          <span>SIH 2026 · OCEAN FORENSICS</span>
          <span>MARITIME INTELLIGENCE PLATFORM</span>

          <button
            onClick={() =>
              window.scrollTo({
                top: 0,
                behavior: 'smooth',
              })
            }
          >
            BACK TO TOP ↑
          </button>
        </div>
      </footer>
    </main>
  );
}
