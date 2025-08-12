"""
ORB keypoint matching and RANSAC re-ranking for card verification.
"""

import cv2
import numpy as np
from typing import List, Tuple


def orb_inliers(query_bgr: np.ndarray, cand_bgr: np.ndarray) -> int:
    """Count ORB keypoint inliers between query and candidate images.
    
    Args:
        query_bgr: Query image in BGR format
        cand_bgr: Candidate image in BGR format
        
    Returns:
        Number of inlier keypoints after RANSAC homography
    """
    orb = cv2.ORB_create(nfeatures=1000)
    
    # Detect keypoints and compute descriptors
    kp1, des1 = orb.detectAndCompute(query_bgr, None)
    kp2, des2 = orb.detectAndCompute(cand_bgr, None)
    
    if des1 is None or des2 is None:
        return 0
    
    # Match descriptors using brute force matcher
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)
    
    # Apply ratio test to filter good matches
    good = [m for m, n in matches if n and m.distance < 0.75 * n.distance]
    
    if len(good) < 8:
        return len(good)
    
    # Extract matched keypoints
    src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    
    # Find homography using RANSAC
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    
    return int(mask.sum()) if mask is not None else len(good)


def rerank_with_orb(query_bgr: np.ndarray, candidates: List[Tuple[str, str, float]], topk: int = 5) -> Tuple[str, int]:
    """Re-rank candidates using ORB keypoint matching.
    
    Args:
        query_bgr: Query image in BGR format
        candidates: List of (card_id, image_path, distance) tuples
        topk: Number of top candidates to re-rank
        
    Returns:
        Tuple of (best_card_id, inlier_count)
    """
    best = ("", -1)
    
    for cid, img_path, _dist in candidates[:topk]:
        cand = cv2.imread(img_path)
        if cand is None:
            continue
            
        inl = orb_inliers(query_bgr, cand)
        if inl > best[1]:
            best = (cid, inl)
    
    return best
