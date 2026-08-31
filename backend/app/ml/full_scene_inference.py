"""Full-scene memory-safe U-Net inference for Sentinel-1 GRD products."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import rasterio
from rasterio.windows import Window
from PIL import Image

from backend.app.ml.sentinel1 import Sentinel1Reader, SAR_MIN_DB, SAR_MAX_DB
from backend.app.ml.unet_segmentation import PyTorchSegmentationModel


def run_full_scene_inference(
    safe_dir: Optional[Union[str, Path]] = None,
    checkpoint_path: Union[str, Path] = Path("models/segmentation/best_unet_resnet18_sar_finetuned.pth"),
    output_dir: Union[str, Path] = Path("data/incidents/sanchi_20180120/outputs"),
    incident_id: str = "sanchi_20180120",
    tile_size: int = 512,
    stride: int = 512,
    threshold: float = 0.50,
    device: Optional[str] = None,
    log_interval: int = 100,
    safe_dir_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Executes memory-safe, stream-to-disk full-scene U-Net inference on a Sentinel-1 SAFE product."""
    target_safe = safe_dir if safe_dir is not None else safe_dir_path
    if target_safe is None:
        raise ValueError("safe_dir or safe_dir_path must be provided")
    safe_path = Path(target_safe)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prob_tif_path = out_dir / "sanchi_probability_map.tif"
    mask_tif_path = out_dir / "sanchi_oil_mask.tif"
    meta_json_path = out_dir / "sanchi_inference_metadata.json"
    preview_png_path = out_dir / "sanchi_detection_preview.png"

    # 1. Initialize Reader and Model
    print(f"Initializing Sentinel-1 Reader for: {safe_path.name}")
    reader = Sentinel1Reader(safe_path)
    height, width = reader.height, reader.width
    print(f"Scene dimensions: Height={height:,}, Width={width:,} ({height * width:,} pixels)")

    print(f"Loading frozen U-Net model from: {checkpoint_path}")
    model = PyTorchSegmentationModel(checkpoint_path=checkpoint_path, device=device)
    print(f"Inference device: {model.device}")

    # 2. Configure Output GeoTIFF Profiles
    # Tile size 512x512 with DEFLATE compression for compact, streaming GeoTIFF
    profile_prob = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": reader.crs,
        "transform": reader.transform,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "nodata": None,
    }

    profile_mask = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint8",
        "crs": reader.crs,
        "transform": reader.transform,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "nodata": None,
    }

    total_rows = (height + stride - 1) // stride
    total_cols = (width + stride - 1) // stride
    total_tiles = total_rows * total_cols
    print(f"Total 512x512 tiles to process: {total_tiles} ({total_rows} rows x {total_cols} cols)")

    # 3. Stream Inference Window-by-Window
    start_time = time.time()
    tiles_processed = 0
    total_oil_pixels = 0
    total_scene_pixels = height * width

    prob_min = 1.0
    prob_max = 0.0
    prob_sum = 0.0

    # Reservoir sample for calculating accurate distribution percentiles without storing all pixels
    sample_pool = []
    max_sample_size = 500_000

    # Downsampled buffer for preview image (scale by ~1/16)
    preview_scale = 16
    preview_h = (height + preview_scale - 1) // preview_scale
    preview_w = (width + preview_scale - 1) // preview_scale
    preview_prob = np.zeros((preview_h, preview_w), dtype=np.float32)

    with rasterio.open(prob_tif_path, "w", **profile_prob) as dst_prob, \
         rasterio.open(mask_tif_path, "w", **profile_mask) as dst_mask:

        for y in range(0, height, stride):
            valid_h = min(tile_size, height - y)
            for x in range(0, width, stride):
                valid_w = min(tile_size, width - x)

                # Read and calibrate only the valid tile
                calibrated_tile = reader.read_calibrated_window(
                    col_off=x,
                    row_off=y,
                    width=valid_w,
                    height=valid_h,
                )

                pad_h = tile_size - valid_h
                pad_w = tile_size - valid_w

                if pad_h > 0 or pad_w > 0:
                    calibrated_tile = np.pad(
                        calibrated_tile,
                        ((0, 0), (0, pad_h), (0, pad_w)),
                        mode="reflect",
                    )

                # Model inference
                _, probs, _ = model.predict_tile(calibrated_tile, threshold=threshold)

                # Unpad to valid dimension
                probs_valid = probs[:valid_h, :valid_w]
                mask_valid = (probs_valid >= threshold).astype(np.uint8)

                # Write directly to disk GeoTIFF
                win = Window(col_off=x, row_off=y, width=valid_w, height=valid_h)
                dst_prob.write(probs_valid, 1, window=win)
                dst_mask.write(mask_valid, 1, window=win)

                # Statistics update
                p_min = float(probs_valid.min())
                p_max = float(probs_valid.max())
                prob_min = min(prob_min, p_min)
                prob_max = max(prob_max, p_max)
                prob_sum += float(probs_valid.sum())
                total_oil_pixels += int(mask_valid.sum())

                # Collect downsampled preview pixels
                py_start = y // preview_scale
                py_end = min((y + valid_h) // preview_scale, preview_h)
                px_start = x // preview_scale
                px_end = min((x + valid_w) // preview_scale, preview_w)
                if py_end > py_start and px_end > px_start:
                    # Subsample step
                    sub = probs_valid[::preview_scale, ::preview_scale]
                    sub_h = min(sub.shape[0], py_end - py_start)
                    sub_w = min(sub.shape[1], px_end - px_start)
                    preview_prob[py_start:py_start + sub_h, px_start:px_start + sub_w] = sub[:sub_h, :sub_w]

                # Sample for percentiles
                if len(sample_pool) < max_sample_size:
                    sample_indices = np.random.choice(probs_valid.size, size=min(300, probs_valid.size), replace=False)
                    sample_pool.extend(probs_valid.ravel()[sample_indices].tolist())

                tiles_processed += 1
                if tiles_processed % log_interval == 0 or tiles_processed == total_tiles:
                    elapsed = time.time() - start_time
                    fps = tiles_processed / elapsed
                    eta = (total_tiles - tiles_processed) / fps if fps > 0 else 0
                    print(f"[{tiles_processed}/{total_tiles}] tiles ({tiles_processed / total_tiles * 100:.1f}%) | "
                          f"Speed: {fps:.2f} tiles/s | ETA: {eta / 60:.1f} min | Oil Pixels: {total_oil_pixels:,}")

    total_duration = time.time() - start_time
    prob_mean = prob_sum / total_scene_pixels
    oil_percentage = (total_oil_pixels / total_scene_pixels) * 100.0

    sample_arr = np.array(sample_pool, dtype=np.float32)
    percentiles = {
        "p10": float(np.percentile(sample_arr, 10)),
        "p25": float(np.percentile(sample_arr, 25)),
        "p50": float(np.percentile(sample_arr, 50)),
        "p75": float(np.percentile(sample_arr, 75)),
        "p90": float(np.percentile(sample_arr, 90)),
        "p95": float(np.percentile(sample_arr, 95)),
        "p99": float(np.percentile(sample_arr, 99)),
    }

    # 4. Generate Downsampled Preview PNG
    # Convert preview probability map to RGB colormap
    preview_img_data = (np.clip(preview_prob, 0.0, 1.0) * 255).astype(np.uint8)
    preview_img = Image.fromarray(preview_img_data, mode="L")
    preview_img.save(preview_png_path)

    # 5. Metadata Record
    metadata = {
        "incident_id": incident_id,
        "model_filename": Path(checkpoint_path).name,
        "model_checkpoint_path": str(checkpoint_path),
        "model_architecture": "segmentation_models_pytorch.Unet(resnet18, in_channels=2, classes=1)",
        "model_metadata": model.metadata,
        "input_channels": ["VV", "VH"],
        "tile_size": tile_size,
        "stride": stride,
        "threshold_applied": threshold,
        "calibration_method": "ESA Level-1 Radiometric LUT Interpolation (sigma0 = DN^2 / A_sigma^2)",
        "normalization_formula": "clip(sigma0_dB, -50.0, 5.0) -> (x + 50.0) / 55.0",
        "scene_dimensions": {
            "height": height,
            "width": width,
            "total_pixels": total_scene_pixels,
        },
        "crs": str(reader.crs),
        "transform": [float(v) for v in reader.transform][:6],
        "number_of_tiles_total": total_tiles,
        "number_of_tiles_processed": tiles_processed,
        "missing_or_failed_tiles": 0,
        "inference_device": str(model.device),
        "inference_duration_seconds": round(total_duration, 2),
        "inference_duration_minutes": round(total_duration / 60, 2),
        "predicted_oil_pixel_count": total_oil_pixels,
        "predicted_oil_percentage": round(oil_percentage, 5),
        "probability_statistics": {
            "min": round(prob_min, 6),
            "max": round(prob_max, 6),
            "mean": round(prob_mean, 6),
            "percentiles": percentiles,
        },
        "output_files": {
            "probability_map": str(prob_tif_path),
            "oil_mask": str(mask_tif_path),
            "preview_png": str(preview_png_path),
            "metadata_json": str(meta_json_path),
        },
    }

    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Full-scene inference complete in {total_duration / 60:.2f} minutes.")
    return metadata
