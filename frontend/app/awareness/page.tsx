import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowLeft,
  Bird,
  Droplets,
  Fish,
  HeartPulse,
  Radar,
  Satellite,
  ShieldCheck,
  Waves,
} from 'lucide-react';

export const metadata: Metadata = {
  title: 'Oil Spill Awareness — Ocean Forensics',
  description:
    'Understand how marine oil spills affect ecosystems, coastal communities and maritime response.',
};

const impacts = [
  {
    icon: Bird,
    title: 'Seabirds and wildlife',
    text: 'Oil damages the waterproofing and insulation of feathers and fur, leaving wildlife vulnerable to cold, exhaustion and poisoning.',
  },
  {
    icon: Fish,
    title: 'Marine food webs',
    text: 'Toxic compounds can harm eggs, larvae, fish and shellfish, disrupting habitats and food chains long after the visible slick disperses.',
  },
  {
    icon: Waves,
    title: 'Coastal habitats',
    text: 'Mangroves, wetlands, coral areas and beaches can trap oil, making recovery difficult and increasing the need for careful cleanup.',
  },
  {
    icon: HeartPulse,
    title: 'People and livelihoods',
    text: 'Fisheries, tourism, port operations and coastal health can all be affected, especially when response teams lack early, reliable information.',
  },
];

const response = [
  ['01', 'Detect early', 'Satellite imagery helps identify possible slicks across large and remote ocean areas.'],
  ['02', 'Understand movement', 'Wind and current information supports backtracking and short-range impact forecasting.'],
  ['03', 'Find nearby vessels', 'Historical AIS tracks identify vessels that were present during the likely discharge window.'],
  ['04', 'Explain the evidence', 'Investigators compare timing, proximity and trajectory before identifying a probable source.'],
];

export default function AwarenessPage() {
  return (
    <main className="awareness-page">
      <nav className="awareness-nav">
        <Link href="/" className="awareness-brand">
          <Image src="/favicon.png" alt="" width={34} height={34} />
          <span>OCEAN <b>FORENSICS</b></span>
        </Link>
        <Link href="/" className="awareness-back"><ArrowLeft /> Back to investigation</Link>
      </nav>

      <header className="awareness-hero">
        <div className="awareness-hero-image" />
        <div className="awareness-hero-copy">
          <span><Droplets /> Oil spill awareness</span>
          <h1>What happens after oil reaches the sea?</h1>
          <p>
            A slick is more than a mark on the ocean surface. It can move with
            wind and currents, spread into sensitive habitats and affect marine
            life and coastal communities. Fast, evidence-led investigation helps
            responders act sooner.
          </p>
          <a href="#impact">Explore the impact <span>↓</span></a>
        </div>
        <div className="awareness-hero-note">
          <Radar />
          <span><small>WHY MONITORING MATTERS</small>Early location and movement estimates help response teams prioritize limited time and resources.</span>
        </div>
      </header>

      <section className="awareness-intro" id="impact">
        <div>
          <span>THE IMPACT</span>
          <h2>One incident can affect an entire coastal system.</h2>
        </div>
        <p>
          The severity of a spill depends on the oil type, volume, weather,
          ocean conditions and proximity to vulnerable habitats. Even when a
          surface sheen becomes less visible, contamination may remain in
          sediments or sheltered shorelines.
        </p>
      </section>

      <section className="impact-grid">
        {impacts.map(({ icon: Icon, title, text }, index) => (
          <article key={title}>
            <span>0{index + 1}</span>
            <Icon />
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </section>

      <section className="awareness-feature">
        <div className="awareness-feature-image">
          <Image src="/spill-1.png" alt="Satellite view used for marine spill analysis" fill sizes="50vw" />
        </div>
        <div className="awareness-feature-copy">
          <span><Satellite /> FROM OBSERVATION TO ACTION</span>
          <h2>Evidence makes response more focused.</h2>
          <p>
            Satellite detection provides the location and geometry of a possible
            spill. Environmental data helps estimate where it came from and
            where it may move. AIS tracks then provide vessel context around the
            relevant place and time.
          </p>
          <div>
            <strong>Detection</strong><i />
            <strong>Movement</strong><i />
            <strong>Attribution</strong>
          </div>
        </div>
      </section>

      <section className="response-section">
        <header>
          <span>THE INVESTIGATION CHAIN</span>
          <h2>Four questions guide the response.</h2>
        </header>
        <div>
          {response.map(([number, title, text]) => (
            <article key={number}>
              <b>{number}</b><h3>{title}</h3><p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="awareness-principle">
        <ShieldCheck />
        <div>
          <span>RESPONSIBLE INTERPRETATION</span>
          <h2>Probability is not proof.</h2>
          <p>
            Satellite detections and vessel correlations support investigation;
            they do not independently establish legal responsibility. Results
            should be reviewed with additional operational and regulatory evidence.
          </p>
        </div>
      </section>

      <section className="awareness-cta">
        <div><span>OCEAN FORENSICS</span><h2>See how the evidence comes together.</h2></div>
        <Link href="/#investigation-intake">Open an investigation <span>→</span></Link>
      </section>

      <footer className="awareness-footer">
        <span>OCEAN FORENSICS · SIH 2026</span>
        <span>Marine spill awareness and investigation</span>
      </footer>
    </main>
  );
}
