"""
Tests for the match module.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.match import AnnIndex, orb_inliers, rerank_with_orb, confidence_from


class TestAnnIndex:
    """Test AnnIndex class."""
    
    @patch('pandas.read_parquet')
    @patch('hnswlib.Index')
    def test_init(self, mock_index, mock_read_parquet):
        """Test AnnIndex initialization."""
        # Mock metadata as DataFrame
        mock_meta = Mock()
        mock_meta.__getitem__ = Mock(return_value=Mock(tolist=Mock(return_value=["card1", "card2", "card3"])))
        mock_read_parquet.return_value = mock_meta
        
        # Mock HNSW index
        mock_index_instance = Mock()
        mock_index.return_value = mock_index_instance
        
        index_dir = Path("/fake/index")
        ann_index = AnnIndex(index_dir)
        
        assert ann_index.index_dir == index_dir
        assert ann_index.row_to_id == {0: "card1", 1: "card2", 2: "card3"}
        mock_index_instance.load_index.assert_called_once_with(str(index_dir / "hnsw.bin"))
        mock_index_instance.set_ef.assert_called_once_with(64)
    
    @patch('pandas.read_parquet')
    @patch('hnswlib.Index')
    def test_search(self, mock_index, mock_read_parquet):
        """Test search functionality."""
        # Mock metadata as DataFrame
        mock_meta = Mock()
        mock_meta.__getitem__ = Mock(return_value=Mock(tolist=Mock(return_value=["card1", "card2"])))
        mock_read_parquet.return_value = mock_meta
        
        # Mock HNSW index
        mock_index_instance = Mock()
        mock_index_instance.knn_query.return_value = (np.array([[0, 1]]), np.array([[0.1, 0.8]]))
        mock_index.return_value = mock_index_instance
        
        index_dir = Path("/fake/index")
        ann_index = AnnIndex(index_dir)
        
        query_vec = np.random.rand(512)
        results = ann_index.search(query_vec, k=2)
        
        expected = [("card1", 0.1), ("card2", 0.8)]
        assert results == expected


class TestRerank:
    """Test ORB re-ranking functionality."""
    
    @patch('cv2.imread')
    @patch('cv2.ORB_create')
    def test_orb_inliers_basic(self, mock_orb_create, mock_imread):
        """Test ORB inlier counting with basic setup."""
        # Mock ORB
        mock_orb = Mock()
        mock_orb_create.return_value = mock_orb
        
        # Create mock keypoints with proper indices
        mock_kp1 = []
        mock_kp2 = []
        for i in range(10):
            kp1 = Mock()
            kp1.pt = (10 + i, 10 + i)
            mock_kp1.append(kp1)
            
            kp2 = Mock()
            kp2.pt = (20 + i, 20 + i)
            mock_kp2.append(kp2)
        
        # Mock keypoints and descriptors
        mock_orb.detectAndCompute.side_effect = [
            (mock_kp1, np.random.randint(0, 255, (10, 32))),
            (mock_kp2, np.random.randint(0, 255, (10, 32)))
        ]
        
        # Mock matcher
        with patch('cv2.BFMatcher') as mock_bf:
            mock_matcher = Mock()
            mock_bf.return_value = mock_matcher
            
            # Mock matches - need at least 8 good matches for homography
            mock_matches = []
            for i in range(10):
                match = Mock()
                match.distance = 10
                match.queryIdx = i
                match.trainIdx = i
                mock_matches.append([match, Mock(distance=50)])
            mock_matcher.knnMatch.return_value = mock_matches
            
            # Mock homography
            with patch('cv2.findHomography') as mock_homography:
                # Return mask with 2 True values
                mask = np.array([True, False, True, False, False, False, False, False, False, False])
                mock_homography.return_value = (np.eye(3), mask)
                
                query_img = np.random.randint(0, 255, (100, 100, 3))
                cand_img = np.random.randint(0, 255, (100, 100, 3))
                
                inliers = orb_inliers(query_img, cand_img)
                assert inliers == 2  # 2 True values in mask
    
    @patch('cv2.imread')
    def test_rerank_with_orb(self, mock_imread):
        """Test re-ranking with ORB."""
        # Mock image reading
        mock_imread.return_value = np.random.randint(0, 255, (100, 100, 3))
        
        # Mock orb_inliers function
        with patch('src.match.rerank.orb_inliers') as mock_orb_inliers:
            mock_orb_inliers.side_effect = [5, 15, 3]  # Different inlier counts
            
            query_img = np.random.randint(0, 255, (100, 100, 3))
            candidates = [
                ("card1", "/path1.jpg", 0.1),
                ("card2", "/path2.jpg", 0.2),
                ("card3", "/path3.jpg", 0.3)
            ]
            
            best_id, best_inliers = rerank_with_orb(query_img, candidates, topk=3)
            
            assert best_id == "card2"
            assert best_inliers == 15


class TestScore:
    """Test confidence scoring."""
    
    def test_confidence_from(self):
        """Test confidence calculation."""
        # Perfect match
        confidence = confidence_from(distance=0.0, inliers=60)
        assert confidence == pytest.approx(1.0, abs=0.01)
        
        # Good match
        confidence = confidence_from(distance=0.2, inliers=45)
        expected = 0.6 * (1.0 - 0.2) + 0.4 * (45 / 60.0)
        assert confidence == pytest.approx(expected, abs=0.01)
        
        # Poor match
        confidence = confidence_from(distance=0.8, inliers=10)
        expected = 0.6 * (1.0 - 0.8) + 0.4 * (10 / 60.0)
        assert confidence == pytest.approx(expected, abs=0.01)
        
        # Edge cases
        confidence = confidence_from(distance=1.0, inliers=0)
        assert confidence == 0.0
        
        confidence = confidence_from(distance=0.0, inliers=100)  # More than 60 inliers
        expected = 0.6 * 1.0 + 0.4 * 1.0
        assert confidence == pytest.approx(expected, abs=0.01)
