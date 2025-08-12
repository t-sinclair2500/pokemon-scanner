"""
Confidence scoring combining ANN distance and ORB inliers.
"""


def confidence_from(distance: float, inliers: int) -> float:
    """Calculate confidence score from distance and inlier count.
    
    Args:
        distance: Cosine distance from ANN search (0.0 = perfect, 1.0 = worst)
        inliers: Number of ORB keypoint inliers (higher = better match)
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Distance score: smaller distance = higher score
    d_score = max(0.0, 1.0 - distance)
    
    # Inlier score: normalize to 0-1, cap at 60+ inliers
    i_score = min(1.0, inliers / 60.0)
    
    # Weighted combination: 60% distance, 40% inliers
    return 0.6 * d_score + 0.4 * i_score
