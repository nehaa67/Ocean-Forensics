# Ocean Forensics — Architecture

## Project Goal

Ocean Forensics is an AI-assisted marine oil-spill investigation system.

The system is designed to:

1. Detect and segment suspected oil spills from satellite imagery.
2. Characterize the detected spill geometrically.
3. Estimate probable spill origin and movement using environmental data.
4. Analyze vessel traffic using AIS.
5. Rank potential vessels using explainable evidence.
6. Present the investigation through a visual interface.

## High-Level Pipeline

Satellite Imagery
        ↓
Segmentation Model
        ↓
Oil Mask
        ↓
Geometry
        ↓
Wind + Ocean Currents
        ↓
Drift / Hindcasting
        ↓
Probable Origin
        ↓
AIS Vessel Tracks
        ↓
Attribution
        ↓
Investigation Result
        ↓
Frontend

## Development Strategy

The final segmentation model is being developed separately.

During prototype development, a mock detection component will provide a structurally identical oil-mask output.

The downstream pipeline will be implemented as real processing so that the mock detector can later be replaced by the trained model without redesigning the system.

## Design Principle

Each major component is isolated behind a service/interface.

This allows future replacement or improvement of:

- Segmentation model
- AIS data source
- Environmental data source
- Drift engine
- Attribution algorithm
- Frontend

without requiring a complete rewrite of the application.