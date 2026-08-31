You are working on our Smart India Hackathon 2026 project.

PROJECT:
SIH 2026 — Problem Statement 26143
Title: Leveraging satellite imagery to determine Oil spills at sea along with AIS data correlations to identify vessel responsible for the spill.

PROJECT CONCEPT:
We are building a futuristic maritime intelligence and investigation web application called:

OCEAN FORENSICS
Tagline: “From satellite evidence to probable source.”

The purpose is NOT to build a generic dashboard.
The product should feel like a professional maritime investigation / intelligence platform.

IMPORTANT:
This is a 4-day hackathon demo, so prioritize a polished, believable, working end-to-end experience over dozens of unfinished features.

OFFICIAL CORE PROBLEM:
1. Detect and characterize an oil spill from satellite imagery.
2. Use oceanographic and meteorological information to trace the slick backward toward its probable origin in space and time.
3. Predict the future movement/spread of the slick.
4. Use historical AIS vessel data to correlate vessels with the spill.
5. Filter candidate vessels and rank them using factors such as proximity, timing, trajectory and behavioral anomalies.
6. Explain why the top-ranked vessel was selected.

CORE DEMO FLOW:
INPUT
→ SPILL DETECTION
→ SPILL CHARACTERIZATION
→ ORIGIN BACKTRACKING
→ FUTURE FORECAST
→ AIS VESSEL CORRELATION
→ TOP 3 VESSEL RANKING
→ “WHY THIS VESSEL?”
→ INCIDENT REPLAY
→ INVESTIGATION REPORT

FRONTEND GOAL:
Build a desktop-first web application that feels premium, futuristic and highly interactive.

Do NOT make:
- a generic admin dashboard
- a CRUD website
- a simple map with cards around it
- a chatbot pasted beside a map
- unnecessary login/signup flows
- a huge settings system
- random AI features unrelated to the PS

The core interaction is investigation.

TECH STACK:
- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- MapLibre or Mapbox for 2D geospatial visualization
- Three.js / React Three Fiber only where it improves the experience
- Recharts for charts if needed

Use clean, reusable components and a maintainable folder structure.

DESIGN LANGUAGE:
Think:
- maritime intelligence
- aerospace / defense command center
- modern scientific visualization
- premium dark UI
- glass/transparent panels used carefully
- strong typography
- subtle glow and motion
- restrained animations
- high information density without becoming cluttered

Do NOT overuse:
- neon effects
- gradients everywhere
- excessive rounded cards
- giant decorative 3D objects
- meaningless animations

The UI should look serious and credible.

MAIN APPLICATION STRUCTURE:

1. LANDING / ENTRY EXPERIENCE

Create a polished intro screen for Ocean Forensics.

Show:
- title
- short description
- “Launch Investigation” CTA
- small live-status style metadata
- subtle animated ocean/satellite visual background

Possible copy:
“Ocean Forensics”
“AI-powered maritime spill investigation and source attribution.”

After clicking Launch Investigation, enter the main workspace.

2. INCIDENT COMMAND CENTER

This is the main screen.

Layout:
- top navigation/header
- left incident panel
- center map / visualization
- right AI analysis panel
- bottom timeline

HEADER:
“OCEAN FORENSICS”
“INCIDENT #26143”
status badge such as “ANALYSIS READY”

LEFT PANEL:
Incident details:
- Incident ID
- Detection time
- Location
- Estimated area
- Confidence
- Severity

Layer toggles:
- Satellite
- Oil Spill
- AIS
- Wind
- Ocean Current
- Origin
- Forecast

CENTER:
Large interactive 2D map.

Display:
- satellite imagery layer
- oil spill polygon
- probable origin zone
- vessel trajectories
- selected candidate vessels
- wind/current directional indicators
- forecast region

RIGHT PANEL:
“AI INVESTIGATION”

Show:
- Spill detection confidence
- Probable origin confidence
- Forecast confidence
- Top candidate vessel
- attribution score

Bottom:
Timeline:
“12h AGO → NOW → +6h”
with play button and draggable slider.

3. SATELLITE ANALYSIS VIEW

Create a focused analysis mode.

Show:
- original satellite image
- detected oil spill mask overlay
- toggle original / processed
- opacity slider
- detected boundary
- area measurement
- confidence score

Primary CTA:
“Analyze Spill”

When triggered, animate the analysis steps:

Satellite image
→ preprocessing
→ AI segmentation
→ spill detected

Then reveal the results.

Do not fake a long loading animation.
Keep it around 1–2 seconds unless actual backend inference is connected.

4. SPILL CHARACTERIZATION

Show:
- spill polygon
- area
- perimeter
- estimated age if data exists
- confidence
- severity

Use a clean scientific visualization.

5. ORIGIN BACKTRACKING

Create a dedicated interaction.

CTA:
“RECONSTRUCT ORIGIN”

When clicked:
- show the current spill
- animate the slick backward through time
- display directional movement
- gradually reveal the probable origin area

At the end:
“PROBABLE ORIGIN”
with:
- coordinates
- confidence
- time estimate

Important:
Use terminology like “probable origin” rather than claiming exact certainty.

6. FUTURE FORECAST

CTA:
“FORECAST SPREAD”

Show:
- current spill boundary
- future projected regions
- timeline
- predicted movement direction
- confidence

Example:
+2h
+4h
+6h

The future region should visually expand/move.

7. AIS VESSEL INTELLIGENCE

Create a vessel investigation panel.

Show:
- vessel tracks on map
- vessel IDs/names
- time range
- distance from probable origin
- candidate filtering

Show a staged process visually:

47 vessels detected
↓
spatial filter
↓
temporal filter
↓
trajectory filter
↓
17 candidates
↓
Top 3 ranked

Do not make fake progress bars that imply real computation if it is not connected.

8. VESSEL ATTRIBUTION

Create a very polished ranking panel:

TOP CANDIDATES

1. MV OCEAN STAR — 87%
2. MT BLUE HORIZON — 61%
3. MV SEA WIND — 43%

Clicking a vessel should open a detailed evidence drawer/panel.

Show:
- proximity score
- timing score
- trajectory score
- origin consistency
- behavioral anomaly
- overall attribution score

Use a visual evidence breakdown.

9. “WHY THIS VESSEL?”

This must be one of the strongest frontend interactions.

Example:

VESSEL:
MV OCEAN STAR

ATTRIBUTION SCORE:
87%

Evidence:
✓ Within relevant spatial zone
✓ Present during estimated spill window
✓ Trajectory intersects reconstructed origin corridor
✓ Direction consistent with inferred drift
⚠ Mild behavioral anomaly

Add a compact map visualization showing the vessel trajectory relative to the probable origin.

The purpose is explainability, not just a random AI score.

10. INCIDENT REPLAY

This is the main WOW feature.

Build an immersive timeline.

Controls:
- play
- pause
- rewind
- speed
- draggable timeline

The map should animate:
- vessel movement
- spill appearance
- spill movement
- origin reconstruction
- current direction
- forecast region

Narrative:
T-12h
→ vessels moving
→ spill appears
→ spill drifts
→ origin reconstruction
→ candidate ranking
→ NOW
→ future forecast

Make the replay smooth and visually impressive.

11. 3D VIEW

3D is OPTIONAL and must not damage the core product.

Provide:
“2D ANALYSIS”
and
“3D INCIDENT”

3D can show:
- ocean surface
- subtle depth
- vessel models
- spill area
- trajectory lines
- origin point
- forecast area

Keep it simple.

DO NOT spend huge effort manually modelling an ocean.
Use lightweight procedural/simple geometry.

The 2D analysis view must remain the authoritative analytical view.

12. INVESTIGATION REPORT

Create a polished report screen/modal.

Show:
- Incident
- Spill detected
- Location
- Area
- Probable origin
- Predicted spread
- Top candidate vessel
- Attribution score
- Supporting evidence
- Confidence

Add:
“Generate Investigation Report”

For the demo this can produce a well-formatted report view or printable report.

DATA / DEMO ASSUMPTIONS:

We will initially use a preloaded demo incident so the entire flow is deterministic.

The primary demo path should be:
“LOAD DEMO INCIDENT”

Also support these secondary entry points:
- Upload Satellite Image + Coordinates
- Enter Coordinates

But do NOT make these more important than the preloaded demo.

The UI should clearly distinguish:
- real/reference data
- simulated demo data

If AIS is synthetic, display a small badge:
“Synthetic AIS — Demonstration Dataset”

Do not falsely present synthetic data as real vessel evidence.

DATA-DRIVEN DESIGN:

Assume the backend will eventually expose objects such as:

Incident:
{
  id,
  latitude,
  longitude,
  detectedAt,
  areaKm2,
  confidence,
  severity
}

Spill:
{
  polygon,
  area,
  perimeter,
  confidence,
  estimatedAge
}

Origin:
{
  latitude,
  longitude,
  confidence,
  timestamp
}

Forecast:
{
  time,
  polygon,
  direction,
  confidence
}

Vessel:
{
  id,
  name,
  latitude,
  longitude,
  track,
  speed,
  heading,
  attributionScore
}

Evidence:
{
  proximity,
  timing,
  trajectoryMatch,
  originConsistency,
  behavioralAnomaly
}

For now, if backend endpoints do not exist:
- create a clean mock-data layer
- centralize demo data
- keep the UI architecture ready to replace mocks with API data later
- NEVER scatter hardcoded values across components

API PREPARATION:

Design the frontend service layer so later we can connect to FastAPI.

Suggested service modules:
- incidentService
- spillService
- vesselService
- forecastService
- attributionService
- replayService

Use typed interfaces/models.

Do not tightly couple UI components to raw fetch calls.

UX REQUIREMENTS:

- Responsive enough for laptop screens
- Desktop-first
- Keyboard-friendly where possible
- Tooltips for unfamiliar icons
- Loading states
- Empty states
- Error states
- Smooth transitions
- Clear hierarchy
- No unnecessary page reloads
- Preserve selected incident state across views

IMPORTANT HACKATHON RULE:

We have very limited time.

Prioritize:
P0:
- command center
- map
- spill visualization
- vessel tracks
- candidate ranking
- why-this-vessel panel
- timeline
- incident replay

P1:
- origin animation
- forecast visualization
- report

P2:
- 3D
- extra animations
- advanced analytics

Do not spend time on things that don't contribute to the judge demo.

FUTURE BACKEND INTEGRATION:

Assume backend:
Python + FastAPI
Possible database:
PostgreSQL/PostGIS
ML:
Python/PyTorch
GIS:
GeoPandas/Shapely/Rasterio

Frontend must remain independent of these implementation details.

CODE QUALITY:

- TypeScript strictness where practical
- reusable components
- clear naming
- no giant 1000-line component
- no duplicate UI logic
- comments only where genuinely useful
- use environment variables for API base URLs
- no API keys committed to the repo
- clean README for local frontend setup

GITHUB:

Our repository is:
https://github.com/prem-03829/SIH-2026-PS-26143

Use the EXISTING local repository/workspace if already cloned.

Do NOT initialize a new unrelated git repository.
Do NOT delete or overwrite existing work.
First inspect the current project structure.

If git remote is missing, set origin to:
https://github.com/prem-03829/SIH-2026-PS-26143

If the repo is already connected, keep the existing remote.

Use a normal Git workflow:
- create a feature branch for your work if appropriate
- make small meaningful commits
- keep changes easy to review
- do not force-push
- do not rewrite history
- do not commit secrets, .env files, API keys or node_modules

Before making major changes:
1. inspect the existing repo
2. understand whether a frontend already exists
3. reuse existing components where sensible
4. avoid replacing working functionality without reason

GIT COMMIT STYLE:
Examples:
feat(frontend): create ocean forensics command center
feat(map): add spill and AIS layers
feat(replay): add incident timeline playback
style(ui): refine investigation workspace
fix(map): correct vessel trail rendering

FINAL DEVELOPMENT ORDER:

PHASE 1
Inspect repo and existing frontend.

PHASE 2
Set up/clean the frontend architecture.

PHASE 3
Build the main Ocean Forensics command center.

PHASE 4
Implement map + spill + AIS mock visualization.

PHASE 5
Implement attribution ranking + evidence panel.

PHASE 6
Implement timeline + incident replay.

PHASE 7
Implement origin backtracking and future forecast visuals.

PHASE 8
Polish UI/animations/responsiveness.

PHASE 9
Add optional 3D only after the 2D flow is stable.

PHASE 10
Run build/lint/tests, fix issues, and prepare the repo for team collaboration.

MOST IMPORTANT:
Do not build a generic dashboard.
Do not overengineer.
Do not add random features.
Build a beautiful, serious, investigation-focused maritime intelligence product.

The ideal final experience is:

DETECT
→ CHARACTERIZE
→ BACKTRACK
→ FORECAST
→ CORRELATE
→ RANK
→ EXPLAIN
→ REPLAY
→ REPORT

Start by inspecting the existing repository and tell me:
1. current stack
2. current folder structure
3. what already exists
4. what should be reused
5. your proposed frontend implementation plan

Then begin implementation incrementally.