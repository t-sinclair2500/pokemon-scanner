"""Tests for the Vision Embedder module."""

import numpy as np
import pytest
from src.vision.embedder import Embedder


class TestEmbedder:
    """Test cases for the Embedder class."""

    def test_embedder_initialization(self):
        """Test that Embedder initializes correctly."""
        embedder = Embedder()
        assert embedder.device in ["mps", "cuda", "cpu"]
        assert embedder.model is not None
        assert embedder.preprocess is not None
        assert embedder.tokenizer is not None

    def test_embed_image_random(self):
        """Test embedding with random image data."""
        embedder = Embedder()
        # Create a random BGR image
        img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        feats = embedder.embed_image(img)
        
        # Check output shape and type
        assert feats.shape == (1, 512)  # ViT-B-32 produces 512-dimensional vectors
        assert feats.dtype == np.float32
        
        # Check normalization (L2 norm should be close to 1.0)
        norm = np.linalg.norm(feats)
        assert np.isclose(norm, 1.0, atol=1e-6)

    def test_embed_image_consistency(self):
        """Test that embedding the same image produces consistent results."""
        embedder = Embedder()
        img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        
        # Get embeddings for the same image twice
        feats1 = embedder.embed_image(img)
        feats2 = embedder.embed_image(img)
        
        # Should be identical
        np.testing.assert_array_almost_equal(feats1, feats2)

    def test_embed_image_different_sizes(self):
        """Test that embedding works with different image sizes."""
        embedder = Embedder()
        
        # Test different image sizes
        sizes = [(100, 100), (224, 224), (480, 640), (1024, 768)]
        
        for h, w in sizes:
            img = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
            feats = embedder.embed_image(img)
            
            assert feats.shape == (1, 512)
            assert feats.dtype == np.float32
            
            # Check normalization
            norm = np.linalg.norm(feats)
            assert np.isclose(norm, 1.0, atol=1e-6)

    def test_device_selection(self):
        """Test that device selection works correctly."""
        # Test explicit device selection
        embedder_cpu = Embedder(device="cpu")
        assert embedder_cpu.device == "cpu"
        
        # Test that we can still embed images
        img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        feats = embedder_cpu.embed_image(img)
        assert feats.shape == (1, 512)
