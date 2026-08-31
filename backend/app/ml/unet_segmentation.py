"""PyTorch U-Net ResNet-18 SAR oil spill segmentation model implementation.

Loads the frozen checkpoint 'best_unet_resnet18_sar_finetuned.pth' and implements
inference on 2-band (VV + VH) calibrated tensors.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import segmentation_models_pytorch as smp

from backend.app.schemas.detection import OilProbabilityMask
from backend.app.ml.interface import SegmentationModel


DEFAULT_CHECKPOINT_PATH = Path("models/segmentation/best_unet_resnet18_sar_finetuned.pth")


class PyTorchSegmentationModel(SegmentationModel):
    """Frozen PyTorch U-Net ResNet-18 model for oil spill segmentation."""

    def __init__(
        self,
        checkpoint_path: Union[str, Path] = DEFAULT_CHECKPOINT_PATH,
        device: Optional[Union[str, torch.device]] = None,
        model_version: str = "unet-resnet18-sar-finetuned",
        preprocessing_version: str = "sentinel1-sigma0-db-v1",
    ):
        self.checkpoint_path = Path(checkpoint_path)
        if not self.checkpoint_path.is_file():
            raise FileNotFoundError(f"U-Net checkpoint file not found: {self.checkpoint_path}")

        self._model_version = model_version
        self._preprocessing_version = preprocessing_version

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # 1. Instantiate exact architecture from training notebook
        self.model = smp.Unet(
            encoder_name="resnet18",
            encoder_weights=None,
            in_channels=2,
            classes=1,
        )

        # 2. Load frozen weights
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
            self.metadata = {
                "epoch": checkpoint.get("epoch"),
                "val_loss": checkpoint.get("val_loss"),
                "val_dice": checkpoint.get("val_dice"),
                "learning_rate": checkpoint.get("learning_rate"),
            }
        elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
            self.metadata = {}
        elif isinstance(checkpoint, dict):
            state_dict = checkpoint
            self.metadata = {}
        else:
            raise ValueError(f"Unexpected checkpoint format in {self.checkpoint_path}")

        self.model.load_state_dict(state_dict, strict=True)
        self.model.to(self.device)
        self.model.eval()

        # Freeze all parameters
        for param in self.model.parameters():
            param.requires_grad = False

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def preprocessing_version(self) -> str:
        return self._preprocessing_version

    def predict_tile(
        self,
        tile_tensor_2_512_512: np.ndarray,
        threshold: float = 0.50,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Runs single-tile inference on a 2x512x512 normalized float32 array.
        
        Args:
            tile_tensor_2_512_512: np.ndarray (2, 512, 512) where ch0=VV, ch1=VH in [0, 1].
            threshold: Probability decision threshold (default: 0.50).

        Returns:
            Tuple of:
              - logits: np.ndarray (512, 512), float32
              - probabilities: np.ndarray (512, 512), float32 in [0, 1]
              - binary_mask: np.ndarray (512, 512), uint8 (0 or 1)
        """
        if tile_tensor_2_512_512.shape != (2, 512, 512):
            raise ValueError(f"Expected tile shape (2, 512, 512), got {tile_tensor_2_512_512.shape}")

        # Add batch dimension -> [1, 2, 512, 512]
        tensor = torch.from_numpy(tile_tensor_2_512_512).unsqueeze(0).float().to(self.device)

        with torch.no_grad():
            logits_tensor = self.model(tensor)
            probs_tensor = torch.sigmoid(logits_tensor)

        logits = logits_tensor[0, 0].cpu().numpy().astype(np.float32)
        probabilities = probs_tensor[0, 0].cpu().numpy().astype(np.float32)
        binary_mask = (probabilities >= threshold).astype(np.uint8)

        return logits, probabilities, binary_mask

    def predict(
        self,
        vv_raster: np.ndarray,
        vh_raster: np.ndarray,
        threshold: float = 0.5,
        mask_id: str = "unet_prediction",
        include_matrices: bool = True,
        **kwargs: Any,
    ) -> OilProbabilityMask:
        """Protocol-compliant prediction for arbitrary sized rasters (crops or full scenes)."""
        if vv_raster.shape != vh_raster.shape:
            raise ValueError(f"Shape mismatch: vv={vv_raster.shape}, vh={vh_raster.shape}")

        h, w = vv_raster.shape

        # If shape is already 512x512, evaluate directly
        if h == 512 and w == 512:
            stacked = np.stack([vv_raster, vh_raster], axis=0).astype(np.float32)
            _, probs, binary_mask = self.predict_tile(stacked, threshold=threshold)
            return OilProbabilityMask(
                mask_id=mask_id,
                shape=(512, 512),
                probability_map=probs.tolist() if include_matrices else None,
                binary_mask=binary_mask.tolist() if include_matrices else None,
                threshold_applied=threshold,
                model_confidence=1.0,
                model_version=self.model_version,
                preprocessing_version=self.preprocessing_version,
                provenance={
                    "checkpoint": str(self.checkpoint_path),
                    "device": str(self.device),
                    "tile_mode": "direct_single_tile",
                },
                quality_warnings=[],
            )

        # For non-512x512 shapes (e.g. tests or custom crops), tile with reflect padding
        prob_accum = np.zeros((h, w), dtype=np.float32)
        count_map = np.zeros((h, w), dtype=np.float32)

        for y in range(0, h, 512):
            valid_h = min(512, h - y)
            for x in range(0, w, 512):
                valid_w = min(512, w - x)
                tile_vv = vv_raster[y:y + valid_h, x:x + valid_w]
                tile_vh = vh_raster[y:y + valid_h, x:x + valid_w]
                tile = np.stack([tile_vv, tile_vh], axis=0)

                pad_h = 512 - valid_h
                pad_w = 512 - valid_w
                if pad_h > 0 or pad_w > 0:
                    tile = np.pad(tile, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")

                _, p, _ = self.predict_tile(tile, threshold=threshold)
                p_valid = p[:valid_h, :valid_w]
                prob_accum[y:y + valid_h, x:x + valid_w] += p_valid
                count_map[y:y + valid_h, x:x + valid_w] += 1.0

        full_prob = prob_accum / np.maximum(count_map, 1e-8)
        binary_mask = (full_prob >= threshold).astype(np.uint8)

        return OilProbabilityMask(
            mask_id=mask_id,
            shape=(h, w),
            probability_map=full_prob.tolist() if include_matrices else None,
            binary_mask=binary_mask.tolist() if include_matrices else None,
            threshold_applied=threshold,
            model_confidence=1.0,
            model_version=self.model_version,
            preprocessing_version=self.preprocessing_version,
            provenance={
                "checkpoint": str(self.checkpoint_path),
                "device": str(self.device),
                "tile_mode": "sliding_window_reflect",
            },
            quality_warnings=[],
        )
