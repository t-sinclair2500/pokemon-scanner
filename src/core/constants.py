from typing import Final, List

CSV_HEADER: Final[List[str]] = [
    "timestamp_iso","card_id","name","number","set_name","set_id","rarity",
    "tcgplayer_market_usd","cardmarket_trend_eur","cardmarket_avg30_eur",
    "pricing_updatedAt_tcgplayer","pricing_updatedAt_cardmarket",
    "source_image_path","price_sources"
]

# Visual match defaults
EMBED_MODEL: Final[str] = "ViT-B-32"
EMBED_PRETRAINED: Final[str] = "openai"
ANN_SPACE: Final[str] = "cosine"
ANN_TOPK: Final[int] = 10
ANN_RERANK_TOPK: Final[int] = 5

# Confidence thresholds
CONFIDENCE_ACCEPT: Final[float] = 0.85
CONFIDENCE_REVIEW: Final[float] = 0.70

# Warp target size (w, h)
WARP_W: Final[int] = 900
WARP_H: Final[int] = 1260

# OCR fallback ROIs (normalized y1,y2,x1,x2)
ROI_NAME = (0.05, 0.14, 0.08, 0.92)
ROI_NUMBER = (0.88, 0.98, 0.05, 0.95)

RATE_LIMIT_QPS: Final[float] = 5.0
BACKOFF_S = [0.2, 1.0, 3.0]
