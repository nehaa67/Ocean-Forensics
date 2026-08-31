from datetime import datetime
import numpy as np

from backend.app.schemas import (
    SentinelScene,
    WindField,
    CurrentField,
    AISRecord,
    VesselTrack,
    OilProbabilityMask,
    DetectionResult,
    SpillGeometry,
    SourceZone,
    AttributionCandidate,
    InvestigationResult,
)


def test_sentinel_scene_schema():
    scene = SentinelScene(
        scene_id="S1B_IW_GRDH_1SDV_20180120T092853_20180120T092918_009253_010962_4338",
        acquisition_timestamp="2018-01-20T09:28:53Z",
        crs_epsg=4326,
        transform=(10.0, 0.0, 125.0, 0.0, -10.0, 30.0),
        bbox=(124.0, 29.0, 126.0, 31.0),
        resolution_m=(10.0, 10.0),
        source_metadata={"satellite": "Sentinel-1B", "mode": "IW"},
    )
    assert scene.scene_id.startswith("S1B_IW_GRDH")
    assert scene.crs_epsg == 4326
    assert scene.bbox[0] == 124.0


def test_environment_schemas():
    wind = WindField(
        u=4.5,
        v=-2.1,
        speed_m_s=5.0,
        direction_deg=115.0,
        timestamp="2018-01-20T09:00:00Z",
        source="ERA5",
    )
    assert wind.u == 4.5
    assert wind.source == "ERA5"

    current = CurrentField(
        u=0.3,
        v=0.1,
        speed_m_s=0.316,
        direction_deg=71.5,
        timestamp="2018-01-20T09:00:00Z",
        source="HYCOM",
    )
    assert current.u == 0.3
    assert current.source == "HYCOM"


def test_ais_schemas():
    record = AISRecord(
        vessel_id="412345678",
        latitude=29.5,
        longitude=125.2,
        timestamp="2018-01-20T09:30:00Z",
        speed=12.5,
        heading=85.0,
        vessel_name="TEST_CARRIER",
    )
    assert record.vessel_id == "412345678"
    assert record.speed == 12.5

    track = VesselTrack(
        vessel_id="412345678",
        first_timestamp="2018-01-20T08:00:00Z",
        last_timestamp="2018-01-20T10:00:00Z",
        distance_m=1250.0,
        time_delta_s=7200.0,
        average_speed_m_s=6.4,
        heading_variance_deg=2.1,
        records=[record],
    )
    assert len(track.records) == 1
    assert track.distance_m == 1250.0


def test_oil_probability_mask_schema():
    prob_matrix = [[0.1, 0.9], [0.0, 0.8]]
    binary_matrix = [[0, 1], [0, 1]]
    mask = OilProbabilityMask(
        mask_id="mask_001",
        shape=(2, 2),
        probability_map=prob_matrix,
        binary_mask=binary_matrix,
        threshold_applied=0.5,
        model_confidence=0.98,
        model_version="unet-resnet18-v1",
        preprocessing_version="sar-standard-v1",
    )
    assert mask.mask_id == "mask_001"
    assert mask.shape == (2, 2)
    assert mask.binary_mask[0][1] == 1


def test_spill_geometry_schema():
    geom = SpillGeometry(
        has_oil=True,
        polygon={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        area_m2=150000.0,
        centroid=(0.5, 0.5),
        bbox=(0.0, 0.0, 1.0, 1.0),
        perimeter_m=1600.0,
        pixel_count=150,
        crs_epsg=3857,
    )
    assert geom.has_oil is True
    assert geom.area_m2 == 150000.0
    assert geom.centroid == (0.5, 0.5)


def test_source_zone_schema():
    source = SourceZone(
        estimated_origin=(125.15, 29.45),
        estimated_spill_time="2018-01-20T06:00:00Z",
        drift_direction="backward",
        duration_hours=3.5,
        timestep_seconds=600.0,
        effective_velocity_m_s={"vx": -0.4, "vy": -0.2},
        uncertainty_radius_m=3000.0,
        crs_epsg=4326,
    )
    assert source.estimated_origin == (125.15, 29.45)
    assert source.drift_direction == "backward"


def test_attribution_candidate_schema():
    candidate = AttributionCandidate(
        vessel_id="V_SANCHI_SUSPECT",
        overall_score=0.92,
        spatial_proximity=0.95,
        temporal_proximity=0.90,
        trajectory_consistency=0.88,
        heading_consistency=0.93,
        explanations={
            "spatial": "Vessel trajectory intersected estimated origin zone within 450 m.",
            "temporal": "Observation coincided with estimated release time within 15 minutes.",
        },
    )
    assert candidate.vessel_id == "V_SANCHI_SUSPECT"
    assert candidate.overall_score == 0.92


def test_investigation_result_schema():
    inv = InvestigationResult(
        incident_id="SANCHI-2018-01-20",
        status="completed",
        environment={"wind_u": 3.0, "current_u": 0.5},
        candidates=[],
        provenance={"pipeline_version": "v1.0.0"},
    )
    assert inv.incident_id == "SANCHI-2018-01-20"
    assert inv.status == "completed"
