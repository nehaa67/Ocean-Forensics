# 🌊 Ocean Forensics

### Detecting oil spills from satellite imagery and tracing them back to vessels using AIS data.

Ocean Forensics is a project built to help investigate oil spills at sea.

The basic idea is simple: **use satellite imagery to find a possible oil spill, then use AIS (Automatic Identification System) data to understand which vessels were nearby and could be connected to the incident.**

Instead of looking at satellite images and vessel data separately, the project brings them together so that an investigator can go from a detected spill to the vessels that were operating in the area around that time.

---

## 💡 What Problem Are We Solving?

Finding an oil spill is only the first step. One of the harder questions is:

> **Which vessel might have caused it?**

The ocean is huge, and vessels are constantly moving. By the time a spill is noticed, the vessel responsible may already be somewhere else.

Ocean Forensics tries to connect these two pieces of information:

**Satellite imagery → Where is the spill?**

**AIS data → Which vessels were there?**

**Geospatial + movement analysis → Which vessel is most likely connected?**

---

## 🔍 How It Works

The project follows roughly this workflow:

```text
        Satellite Imagery
               │
               ▼
        Spill Detection
               │
               ▼
       Spill Location &
          Geometry
               │
               ▼
       ┌───────────────┐
       │   AIS Data    │
       └───────────────┘
               │
               ▼
       Vessel Tracking
               │
               ▼
     Spatial & Time Analysis
               │
               ▼
       Vessel Attribution
               │
               ▼
        Risk Assessment
               │
               ▼
       Investigation Report
