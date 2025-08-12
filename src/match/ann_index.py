"""
ANN index loader and searcher using HNSW.
"""

import hnswlib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple


class AnnIndex:
    """HNSW index loader and searcher for card embeddings."""
    
    def __init__(self, index_dir: Path):
        """Initialize the ANN index from directory.
        
        Args:
            index_dir: Path to directory containing hnsw.bin and meta.parquet
        """
        self.index_dir = index_dir
        self.meta = pd.read_parquet(index_dir / "meta.parquet")
        self.row_to_id = {i: cid for i, cid in enumerate(self.meta["card_id"].tolist())}
        
        # Load HNSW index
        self.index = hnswlib.Index(space="cosine", dim=512)
        self.index.load_index(str(index_dir / "hnsw.bin"))
        self.index.set_ef(64)
    
    def search(self, vec: np.ndarray, k: int) -> List[Tuple[str, float]]:
        """Search for k nearest neighbors.
        
        Args:
            vec: Query vector (512-dimensional)
            k: Number of results to return
            
        Returns:
            List of (card_id, distance) tuples
        """
        labels, dists = self.index.knn_query(vec, k=k)
        return [(self.row_to_id[int(l)], float(d)) for l, d in zip(labels[0], dists[0])]
