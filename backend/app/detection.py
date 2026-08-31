from backend.app.schemas.detection import DetectionResult

def detect_from_mask(mask_id: str, confidence: float = 1.0) -> DetectionResult:
    """Prototype detection logic.
    Returns a DetectionResult indicating a detected oil spill.
    """
    return DetectionResult(
        detected=True,
        confidence=confidence,
        mask_id=mask_id,
        detection_mode="prototype",
    )
