"""Image embedding using OpenCLIP."""

from typing import Tuple
import numpy as np
import torch
import cv2
import open_clip
from src.core.constants import EMBED_MODEL, EMBED_PRETRAINED


class Embedder:
    def __init__(self, device: str | None = None):
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = device
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(EMBED_MODEL, pretrained=EMBED_PRETRAINED, device=self.device)
        self.tokenizer = open_clip.get_tokenizer(EMBED_MODEL)

    def embed_image(self, bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        from PIL import Image
        pil = Image.fromarray(rgb)
        with torch.no_grad():
            img = self.preprocess(pil).unsqueeze(0).to(self.device)
            feats = self.model.encode_image(img)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.cpu().numpy().astype("float32")  # (1, D)
