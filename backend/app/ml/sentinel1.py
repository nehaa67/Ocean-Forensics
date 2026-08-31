"""Sentinel-1 SAR GRD reader and exact radiometric calibration pipeline.

Implements the ESA Level-1 calibration specification:
    sigma0_linear = DN^2 / A_sigma^2
    sigma0_dB = 10 * log10(sigma0_linear) = 20 * log10(DN) - 20 * log10(A_sigma)

Followed by the exact training preprocessing contract:
    channel 0 = VV Sigma0 dB
    channel 1 = VH Sigma0 dB
    clipping: [-50.0, 5.0] dB
    normalization: (sigma0_dB + 50.0) / 55.0 -> float32 in [0.0, 1.0]
    tiling: 512x512 windows with reflect boundary padding.
"""

from __future__ import annotations

import os
import glob
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional, Tuple, Union

import numpy as np
import rasterio
from rasterio.windows import Window


# ============================================================
# CONSTANTS (From Training Contract)
# ============================================================

SAR_MIN_DB: float = -50.0
SAR_MAX_DB: float = 5.0
SAR_RANGE_DB: float = 55.0  # 5.0 - (-50.0)
DEFAULT_TILE_SIZE: int = 512
DEFAULT_STRIDE: int = 512


@dataclass
class TileData:
    """Metadata and raster tensor for a 512x512 inference tile."""
    tensor: np.ndarray  # Shape: (2, 512, 512), float32, [0.0, 1.0] (ch0=VV, ch1=VH)
    row_off: int
    col_off: int
    valid_height: int  # Unpadded height (<= 512)
    valid_width: int   # Unpadded width (<= 512)
    pad_h: int         # Reflected bottom pad pixels
    pad_w: int         # Reflected right pad pixels


# ============================================================
# 2D BILINEAR GRID INTERPOLATOR (Pure NumPy)
# ============================================================

def bilinear_interp_regular_grid(
    grid_y: np.ndarray,
    grid_x: np.ndarray,
    grid_z: np.ndarray,
    target_y: np.ndarray,
    target_x: np.ndarray,
) -> np.ndarray:
    """Bilinear interpolation over a 2D regular grid using pure NumPy.
    
    Args:
        grid_y: 1D array of strictly increasing row/line coordinates (N,)
        grid_x: 1D array of strictly increasing col/pixel coordinates (M,)
        grid_z: 2D array of grid values (N, M)
        target_y: 1D array of query row coordinates (H,)
        target_x: 1D array of query column coordinates (W,)

    Returns:
        2D array of interpolated values (H, W), float64
    """
    ty = np.asarray(target_y, dtype=np.float64)
    tx = np.asarray(target_x, dtype=np.float64)

    # Clip query coordinates to grid range
    ty_clipped = np.clip(ty, grid_y[0], grid_y[-1])
    tx_clipped = np.clip(tx, grid_x[0], grid_x[-1])

    # Find bounding box indices
    iy = np.searchsorted(grid_y, ty_clipped, side="right") - 1
    iy = np.clip(iy, 0, len(grid_y) - 2)

    ix = np.searchsorted(grid_x, tx_clipped, side="right") - 1
    ix = np.clip(ix, 0, len(grid_x) - 2)

    y0, y1 = grid_y[iy], grid_y[iy + 1]
    x0, x1 = grid_x[ix], grid_x[ix + 1]

    # Normalized weights
    wy = (ty_clipped - y0) / np.maximum(y1 - y0, 1e-12)
    wx = (tx_clipped - x0) / np.maximum(x1 - x0, 1e-12)

    # Corner values
    z00 = grid_z[iy[:, None], ix[None, :]]
    z01 = grid_z[iy[:, None], (ix + 1)[None, :]]
    z10 = grid_z[(iy + 1)[:, None], ix[None, :]]
    z11 = grid_z[(iy + 1)[:, None], (ix + 1)[None, :]]

    # Bilinear interpolation
    z0 = z00 * (1.0 - wx[None, :]) + z01 * wx[None, :]
    z1 = z10 * (1.0 - wx[None, :]) + z11 * wx[None, :]
    z = z0 * (1.0 - wy[:, None]) + z1 * wy[:, None]

    return z


# ============================================================
# SENTINEL-1 CALIBRATION PARSER
# ============================================================

class Sentinel1Calibration:
    """Parses Sentinel-1 Level-1 calibration XML and evaluates sigmaNought LUT."""

    def __init__(self, xml_path: Union[str, Path]):
        self.xml_path = Path(xml_path)
        if not self.xml_path.is_file():
            raise FileNotFoundError(f"Calibration XML file not found: {self.xml_path}")

        tree = ET.parse(self.xml_path)
        root = tree.getroot()

        vectors = root.findall(".//calibrationVector")
        if not vectors:
            raise ValueError(f"No calibration vectors found in {self.xml_path}")

        self.grid_lines = np.array([int(v.findtext("line")) for v in vectors], dtype=np.float64)
        self.grid_pixels = np.array(
            list(map(int, vectors[0].findtext("pixel").split())),
            dtype=np.float64,
        )
        self.sigma_matrix = np.array(
            [list(map(float, v.findtext("sigmaNought").split())) for v in vectors],
            dtype=np.float64,
        )

    def interpolate_lut(self, row_coords: np.ndarray, col_coords: np.ndarray) -> np.ndarray:
        """Interpolate sigmaNought calibration factor A_sigma for given line/pixel coords."""
        return bilinear_interp_regular_grid(
            self.grid_lines,
            self.grid_pixels,
            self.sigma_matrix,
            row_coords,
            col_coords,
        )

    def dn_to_sigma0_db(
        self,
        dn: np.ndarray,
        row_coords: np.ndarray,
        col_coords: np.ndarray,
        eps: float = 1e-7,
    ) -> np.ndarray:
        """Calibrate raw uint16 DN values to Sigma0 in dB.
        
        Formula:
            sigma0_linear = DN^2 / A_sigma^2
            sigma0_dB = 10 * log10(max(sigma0_linear, eps))
        """
        lut = self.interpolate_lut(row_coords, col_coords)
        dn_float = np.asarray(dn, dtype=np.float32)

        # Handle zero or negative DN safely
        valid_mask = dn_float > 0
        sigma0_linear = np.zeros_like(dn_float, dtype=np.float32)
        np.divide(
            dn_float ** 2,
            lut ** 2,
            out=sigma0_linear,
            where=valid_mask,
        )
        # Pixels with DN=0 get a very small positive epsilon
        sigma0_linear = np.maximum(sigma0_linear, eps)
        sigma0_db = 10.0 * np.log10(sigma0_linear)

        # Explicitly assign SAR_MIN_DB to zero-DN/nodata pixels
        sigma0_db[~valid_mask] = SAR_MIN_DB
        return sigma0_db


# ============================================================
# NORMALIZATION FUNCTION
# ============================================================

def normalize_sigma0_db(
    sigma0_db: np.ndarray,
    sar_min: float = SAR_MIN_DB,
    sar_max: float = SAR_MAX_DB,
) -> np.ndarray:
    """Applies exact training normalization to Sigma0 dB raster.
    
    1. Replace NaNs/Infs with min/max bounds.
    2. Clip to [sar_min, sar_max] ([-50.0, 5.0] dB).
    3. Scale linearly to [0.0, 1.0]: (x - sar_min) / (sar_max - sar_min).
    """
    arr = np.nan_to_num(
        sigma0_db,
        nan=sar_min,
        posinf=sar_max,
        neginf=sar_min,
    )
    arr = np.clip(arr, sar_min, sar_max)
    normalized = (arr - sar_min) / (sar_max - sar_min)
    return normalized.astype(np.float32)


# ============================================================
# SENTINEL-1 SAFE READER
# ============================================================

class Sentinel1Reader:
    """Memory-safe windowed reader and preprocessor for Sentinel-1 GRD SAFE products."""

    def __init__(
        self,
        safe_dir: Union[str, Path],
        vv_tif: Optional[Union[str, Path]] = None,
        vh_tif: Optional[Union[str, Path]] = None,
        vv_cal_xml: Optional[Union[str, Path]] = None,
        vh_cal_xml: Optional[Union[str, Path]] = None,
    ):
        self.safe_dir = Path(safe_dir)

        # Auto-discover measurement TIFFs if not explicitly passed
        if vv_tif is None or vh_tif is None:
            meas_vv = glob.glob(str(self.safe_dir / "measurement" / "*vv*.tiff"))
            meas_vh = glob.glob(str(self.safe_dir / "measurement" / "*vh*.tiff"))
            if not meas_vv or not meas_vh:
                raise FileNotFoundError(f"Could not locate VV/VH TIFFs in {self.safe_dir / 'measurement'}")
            self.vv_tif = Path(meas_vv[0])
            self.vh_tif = Path(meas_vh[0])
        else:
            self.vv_tif = Path(vv_tif)
            self.vh_tif = Path(vh_tif)

        # Auto-discover calibration XMLs if not explicitly passed
        if vv_cal_xml is None or vh_cal_xml is None:
            cal_vv = glob.glob(str(self.safe_dir / "annotation" / "calibration" / "*vv*.xml"))
            cal_vh = glob.glob(str(self.safe_dir / "annotation" / "calibration" / "*vh*.xml"))
            if not cal_vv or not cal_vh:
                raise FileNotFoundError(f"Could not locate calibration XMLs in {self.safe_dir / 'annotation/calibration'}")
            self.vv_cal_xml = Path(cal_vv[0])
            self.vh_cal_xml = Path(cal_vh[0])
        else:
            self.vv_cal_xml = Path(vv_cal_xml)
            self.vh_cal_xml = Path(vh_cal_xml)

        # Initialize calibration parsers
        self.vv_calibration = Sentinel1Calibration(self.vv_cal_xml)
        self.vh_calibration = Sentinel1Calibration(self.vh_cal_xml)

        # Inspect dimensions from VV metadata without loading rasters
        with rasterio.open(self.vv_tif) as src:
            self.height: int = src.height
            self.width: int = src.width
            self.dtype = src.dtypes[0]
            self.transform = src.transform
            self.crs = src.crs

    def read_window_raw_dn(
        self,
        col_off: int,
        row_off: int,
        width: int,
        height: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Read raw uint16 Digital Numbers for a specific window."""
        win = Window(col_off, row_off, width, height)
        with rasterio.open(self.vv_tif) as src_vv:
            dn_vv = src_vv.read(1, window=win)
        with rasterio.open(self.vh_tif) as src_vh:
            dn_vh = src_vh.read(1, window=win)
        return dn_vv, dn_vh

    def read_calibrated_window(
        self,
        col_off: int,
        row_off: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Reads, radiometrically calibrates, and normalizes a window.
        
        Returns:
            np.ndarray of shape (2, height, width), float32 in [0.0, 1.0]
            Channel 0: Normalized VV Sigma0
            Channel 1: Normalized VH Sigma0
        """
        dn_vv, dn_vh = self.read_window_raw_dn(col_off, row_off, width, height)
        row_coords = np.arange(row_off, row_off + height, dtype=np.float64)
        col_coords = np.arange(col_off, col_off + width, dtype=np.float64)

        # Radiometric calibration to dB
        sigma0_vv_db = self.vv_calibration.dn_to_sigma0_db(dn_vv, row_coords, col_coords)
        sigma0_vh_db = self.vh_calibration.dn_to_sigma0_db(dn_vh, row_coords, col_coords)

        # Normalization to [0.0, 1.0]
        norm_vv = normalize_sigma0_db(sigma0_vv_db)
        norm_vh = normalize_sigma0_db(sigma0_vh_db)

        # Stack into [2, H, W]
        stacked = np.stack([norm_vv, norm_vh], axis=0).astype(np.float32)
        return stacked

    def generate_512_tiles(
        self,
        tile_size: int = DEFAULT_TILE_SIZE,
        stride: int = DEFAULT_STRIDE,
        mode: str = "reflect",
    ) -> Generator[TileData, None, None]:
        """Memory-safely yields 512x512 tiles across the full Sentinel-1 scene.
        
        Applies reflect padding when tiles touch scene boundaries and records padding metadata.
        """
        for y in range(0, self.height, stride):
            valid_h = min(tile_size, self.height - y)
            for x in range(0, self.width, stride):
                valid_w = min(tile_size, self.width - x)

                # Read and calibrate only the valid window
                tile = self.read_calibrated_window(
                    col_off=x,
                    row_off=y,
                    width=valid_w,
                    height=valid_h,
                )

                pad_h = tile_size - valid_h
                pad_w = tile_size - valid_w

                if pad_h > 0 or pad_w > 0:
                    tile = np.pad(
                        tile,
                        ((0, 0), (0, pad_h), (0, pad_w)),
                        mode=mode,
                    )

                yield TileData(
                    tensor=tile.astype(np.float32),
                    row_off=y,
                    col_off=x,
                    valid_height=valid_h,
                    valid_width=valid_w,
                    pad_h=pad_h,
                    pad_w=pad_w,
                )
