"""Apify integration for TCGPlayer sold listings and market data."""

import aiohttp
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics

from ..utils import get_logger, LoggerMixin, settings
from ..resolve import PokemonCard


@dataclass
class SoldListing:
    """Represents a sold listing from TCGPlayer."""
    title: str
    condition: str
    price: float
    sold_date: datetime
    seller: str
    shipping: Optional[float] = None
    total_price: Optional[float] = None
    
    def __post_init__(self):
        if self.total_price is None:
            self.total_price = self.price + (self.shipping or 0)


@dataclass
class MarketAnalysis:
    """Market analysis based on sold listings."""
    card_name: str
    condition: str
    total_sales: int
    average_price: float
    median_price: float
    price_range: Dict[str, float]
    recent_sales: List[SoldListing]
    trend: str  # 'up', 'down', 'stable'
    confidence: float  # 0-1, based on sample size
    analysis_date: datetime


class ApifyTCGPlayerScraper(LoggerMixin):
    """Scrapes TCGPlayer sold listings using Apify actors."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.api_token = settings.apify_api_token
        self.actor_id = settings.apify_actor_id
        self.base_url = "https://api.apify.com/v2"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Cache for scraping results
        self._results_cache: Dict[str, MarketAnalysis] = {}
        self._cache_duration = timedelta(hours=6)  # Shorter cache for sold data
    
    async def initialize_session(self):
        """Initialize aiohttp session."""
        if self.session is None:
            connector = aiohttp.TCPConnector(limit=5, limit_per_host=3)
            timeout = aiohttp.ClientTimeout(total=300)  # Longer timeout for scraping
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
    
    async def close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def is_configured(self) -> bool:
        """Check if Apify is properly configured."""
        return bool(self.api_token and self.actor_id)
    
    async def get_sold_listings(self, card: PokemonCard, condition: str = "Near Mint",
                               days_back: int = 30) -> Optional[MarketAnalysis]:
        """Get sold listings for a card from TCGPlayer via Apify."""
        if not self.is_configured():
            self.logger.warning("Apify not configured, skipping sold listings")
            return None
        
        # Check cache first
        cache_key = f"{card.id}_{condition}_{days_back}"
        if cache_key in self._results_cache:
            cached_data = self._results_cache[cache_key]
            if datetime.now() - cached_data.analysis_date < self._cache_duration:
                self.logger.info("Using cached sold listings", card_id=card.id)
                return cached_data
        
        context = self.log_operation(
            "get_sold_listings",
            card_id=card.id,
            card_name=card.name,
            condition=condition,
            days_back=days_back
        )
        
        try:
            await self.initialize_session()
            
            # Start Apify actor run
            run_id = await self._start_actor_run(card, condition, days_back)
            
            if not run_id:
                self.logger.error("Failed to start Apify actor")
                return None
            
            # Wait for completion and get results
            results = await self._wait_for_results(run_id)
            
            if results:
                # Parse and analyze the results
                analysis = self._analyze_sold_listings(card.name, condition, results)
                
                if analysis:
                    # Cache the results
                    self._results_cache[cache_key] = analysis
                    
                    self.log_success(
                        context,
                        sales_found=analysis.total_sales,
                        average_price=analysis.average_price,
                        trend=analysis.trend
                    )
                    
                    return analysis
            
            self.logger.warning("No sold listings found", card_name=card.name)
            return None
        
        except Exception as e:
            self.log_error(context, e)
            return None
    
    async def _start_actor_run(self, card: PokemonCard, condition: str, days_back: int) -> Optional[str]:
        """Start an Apify actor run for scraping."""
        try:
            url = f"{self.base_url}/acts/{self.actor_id}/runs"
            
            # Build search query for TCGPlayer
            search_query = f"{card.name} {card.set_name}".strip()
            
            input_data = {
                "searchQuery": search_query,
                "condition": condition,
                "daysBack": days_back,
                "maxResults": 100,
                "includeSoldListings": True,
                "includeActiveListings": False
            }
            
            params = {"token": self.api_token}
            
            async with self.session.post(url, json=input_data, params=params) as response:
                if response.status == 201:
                    data = await response.json()
                    run_id = data.get("data", {}).get("id")
                    self.logger.info("Started Apify actor run", run_id=run_id)
                    return run_id
                else:
                    self.logger.error("Failed to start actor", status=response.status)
                    return None
        
        except Exception as e:
            self.logger.error("Error starting Apify actor", error=str(e))
            return None
    
    async def _wait_for_results(self, run_id: str, max_wait_time: int = 180) -> Optional[List[Dict]]:
        """Wait for Apify actor run to complete and return results."""
        try:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check run status
                status_url = f"{self.base_url}/actor-runs/{run_id}"
                params = {"token": self.api_token}
                
                async with self.session.get(status_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("data", {}).get("status")
                        
                        if status == "SUCCEEDED":
                            # Get results
                            return await self._fetch_run_results(run_id)
                        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                            self.logger.error("Apify run failed", run_id=run_id, status=status)
                            return None
                        elif status in ["READY", "RUNNING"]:
                            # Still running, wait and check again
                            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                                self.logger.error("Apify run timeout", run_id=run_id)
                                return None
                            
                            await asyncio.sleep(5)  # Wait 5 seconds before checking again
                        else:
                            self.logger.warning("Unknown Apify status", status=status)
                            await asyncio.sleep(5)
                    else:
                        self.logger.error("Error checking run status", status=response.status)
                        return None
        
        except Exception as e:
            self.logger.error("Error waiting for results", error=str(e))
            return None
    
    async def _fetch_run_results(self, run_id: str) -> Optional[List[Dict]]:
        """Fetch results from completed Apify run."""
        try:
            url = f"{self.base_url}/actor-runs/{run_id}/dataset/items"
            params = {"token": self.api_token, "format": "json"}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error("Error fetching results", status=response.status)
                    return None
        
        except Exception as e:
            self.logger.error("Error fetching Apify results", error=str(e))
            return None
    
    def _analyze_sold_listings(self, card_name: str, condition: str, 
                              raw_data: List[Dict]) -> Optional[MarketAnalysis]:
        """Analyze sold listings data and create market analysis."""
        try:
            # Parse sold listings
            sold_listings = []
            
            for item in raw_data:
                if not item.get('isSold', False):
                    continue
                
                try:
                    listing = SoldListing(
                        title=item.get('title', ''),
                        condition=item.get('condition', condition),
                        price=float(item.get('price', 0)),
                        sold_date=self._parse_date(item.get('soldDate')),
                        seller=item.get('seller', ''),
                        shipping=float(item.get('shipping', 0)) if item.get('shipping') else None
                    )
                    
                    if listing.price > 0:  # Valid price
                        sold_listings.append(listing)
                
                except (ValueError, TypeError) as e:
                    self.logger.debug("Error parsing listing", error=str(e))
                    continue
            
            if len(sold_listings) < 3:  # Need minimum sample size
                self.logger.warning("Insufficient sold listings", count=len(sold_listings))
                return None
            
            # Calculate statistics
            prices = [listing.total_price or listing.price for listing in sold_listings]
            
            average_price = statistics.mean(prices)
            median_price = statistics.median(prices)
            
            price_range = {
                'min': min(prices),
                'max': max(prices),
                'q1': statistics.quantiles(prices, n=4)[0] if len(prices) >= 4 else min(prices),
                'q3': statistics.quantiles(prices, n=4)[2] if len(prices) >= 4 else max(prices)
            }
            
            # Determine trend (simple analysis based on recent vs older sales)
            trend = self._calculate_trend(sold_listings)
            
            # Confidence based on sample size
            confidence = min(len(sold_listings) / 20, 1.0)  # Max confidence at 20+ sales
            
            # Get recent sales (last 10)
            recent_sales = sorted(sold_listings, key=lambda x: x.sold_date, reverse=True)[:10]
            
            return MarketAnalysis(
                card_name=card_name,
                condition=condition,
                total_sales=len(sold_listings),
                average_price=average_price,
                median_price=median_price,
                price_range=price_range,
                recent_sales=recent_sales,
                trend=trend,
                confidence=confidence,
                analysis_date=datetime.now()
            )
        
        except Exception as e:
            self.logger.error("Error analyzing sold listings", error=str(e))
            return None
    
    def _calculate_trend(self, sold_listings: List[SoldListing]) -> str:
        """Calculate price trend from sold listings."""
        if len(sold_listings) < 6:
            return 'stable'
        
        try:
            # Sort by date
            sorted_listings = sorted(sold_listings, key=lambda x: x.sold_date)
            
            # Compare recent half vs older half
            midpoint = len(sorted_listings) // 2
            older_prices = [l.total_price or l.price for l in sorted_listings[:midpoint]]
            newer_prices = [l.total_price or l.price for l in sorted_listings[midpoint:]]
            
            older_avg = statistics.mean(older_prices)
            newer_avg = statistics.mean(newer_prices)
            
            # Calculate percentage change
            change_pct = ((newer_avg - older_avg) / older_avg) * 100
            
            if change_pct > 10:
                return 'up'
            elif change_pct < -10:
                return 'down'
            else:
                return 'stable'
        
        except Exception:
            return 'stable'
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date string from scraped data."""
        if not date_str:
            return datetime.now()
        
        try:
            # Try different date formats
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.split('T')[0] if 'T' in date_str else date_str, fmt)
                except ValueError:
                    continue
            
            # If all else fails, return current time
            return datetime.now()
        
        except Exception:
            return datetime.now()
    
    def get_market_summary(self, analysis: MarketAnalysis) -> Dict[str, Any]:
        """Get a summary of market analysis."""
        return {
            'card_name': analysis.card_name,
            'condition': analysis.condition,
            'total_sales': analysis.total_sales,
            'average_price': f"${analysis.average_price:.2f}",
            'median_price': f"${analysis.median_price:.2f}",
            'price_range': f"${analysis.price_range['min']:.2f} - ${analysis.price_range['max']:.2f}",
            'trend': analysis.trend,
            'confidence': f"{analysis.confidence * 100:.1f}%",
            'recent_sales_count': len(analysis.recent_sales),
            'analysis_date': analysis.analysis_date.isoformat()
        }
    
    # Synchronous wrapper methods
    def get_sold_listings_sync(self, card: PokemonCard, condition: str = "Near Mint",
                              days_back: int = 30) -> Optional[MarketAnalysis]:
        """Synchronous wrapper for get_sold_listings."""
        return asyncio.run(self.get_sold_listings(card, condition, days_back))


# Global scraper instance
apify_scraper = ApifyTCGPlayerScraper()
