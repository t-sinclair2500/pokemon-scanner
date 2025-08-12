"""Build local visual search index from pokemontcg.io."""

import aiohttp
import asyncio
import pandas as pd
import os
import hnswlib
import numpy as np
import cv2
from pathlib import Path
from typer import Typer
from src.utils.config import Settings, ensure_dirs
from src.vision.embedder import Embedder
from src.utils.log import configure_logging, get_logger

app = Typer()
API = "https://api.pokemontcg.io/v2/cards"


async def fetch_cards(api_key: str | None) -> list[dict]:
    """Fetch all English Pokemon cards from the API."""
    headers = {"X-Api-Key": api_key} if api_key else {}
    async with aiohttp.ClientSession(headers=headers) as s:
        page = 1
        perPage = 250
        out = []
        while True:
            async with s.get(API, params={"page": page, "pageSize": perPage, "q": "language:en"}) as r:
                r.raise_for_status()
                j = await r.json()
                data = j.get("data", [])
                if not data:
                    break
                out.extend(data)
                page += 1
        return out


def build_index(cards: list[dict], index_dir: Path):
    """Build the visual search index from downloaded cards."""
    em = Embedder()
    ids, vecs = [], []
    img_dir = index_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    
    for c in cards:
        cid = c["id"]
        url = c["images"]["large"]
        img_path = img_dir / f"{cid}.jpg"
        
        if not img_path.exists():
            import requests
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            img_path.write_bytes(r.content)
        
        bgr = cv2.imread(str(img_path))
        if bgr is None:
            continue
        
        vec = em.embed_image(bgr)[0]
        ids.append(cid)
        vecs.append(vec)
    
    if not ids:
        return
    
    vecs = np.vstack(vecs).astype("float32")
    dim = vecs.shape[1]
    
    index = hnswlib.Index(space="cosine", dim=dim)
    index.init_index(max_elements=len(ids), M=32, ef_construction=200)
    index.add_items(vecs, np.arange(len(ids)))
    index.set_ef(64)
    index.save_index(str(index_dir / "hnsw.bin"))
    
    # Create metadata DataFrame
    meta_data = []
    for c in cards:
        img_path = index_dir / "images" / f'{c["id"]}.jpg'
        if img_path.exists():
            meta_data.append({
                "card_id": c["id"],
                "name": c["name"],
                "number": c.get("number", ""),
                "set_id": c["set"]["id"],
                "set_name": c["set"]["name"],
                "rarity": c.get("rarity", ""),
                "image_path": str(img_path)
            })
    
    pd.DataFrame(meta_data).to_parquet(index_dir / "meta.parquet")


@app.command()
def main():
    """Main CLI entrypoint for building the reference index."""
    s = Settings()
    ensure_dirs(s)
    configure_logging()
    log = get_logger("build_index")
    
    idx = Path(s.INDEX_DIR)
    idx.mkdir(parents=True, exist_ok=True)
    
    cards = asyncio.run(fetch_cards(s.POKEMON_TCG_API_KEY))
    log.info("cards_downloaded", count=len(cards))
    
    build_index(cards, idx)
    log.info("index_built", index=str(idx))


if __name__ == "__main__":
    app()
