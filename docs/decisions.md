# Architecture Decisions

## Decision 001 — Modular Backend

### Decision
Use a modular FastAPI backend with separate API routes, schemas, services and utilities.

### Reason
The project contains several independent stages including AI detection, geometry, drift, AIS and attribution.

### Benefit
Individual components can be tested, replaced and expanded without rewriting the complete system.

---

## Decision 002 — Oil Mask as the AI Interface

### Decision
The segmentation model will communicate with the downstream pipeline through an oil-mask representation.

### Reason
The rest of the system needs the spatial location and shape of the detected spill rather than only a yes/no classification.

### Benefit
The segmentation architecture can be replaced later without changing geometry, drift, AIS or attribution.

---

## Decision 003 — Mock Detection During Prototype Development

### Decision
Use a temporary mock detector while the final segmentation model is being trained.

### Reason
Development of the rest of the system should not depend on completion of ML training.

### Replacement Plan
Mock detector → trained segmentation model.

The downstream interfaces remain unchanged.