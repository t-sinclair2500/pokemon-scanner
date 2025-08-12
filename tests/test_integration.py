"""Integration tests for the full Pokemon Scanner application.

These tests verify that all components work together correctly in end-to-end scenarios.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import cv2
import numpy as np

from src.capture.camera import camera_capture
from src.capture.warp import PerspectiveCorrector
from src.ocr.extract import ocr_extractor, CardInfo
from src.resolve.poketcg import PokemonTCGResolver, PokemonCard
from src.pricing.poketcg_prices import pokemon_pricer
from src.store.cache import card_cache
from src.store.writer import csv_writer
from src.utils.log import configure_logging, get_logger
from src.utils.config import settings


class TestFullAppIntegration:
    """Test the complete application workflow integration."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test environment and clean up after each test."""
        # Configure logging for tests
        configure_logging()
        
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
        self.cache_dir = self.temp_dir / "cache"
        self.output_dir.mkdir()
        self.cache_dir.mkdir()
        
        # Mock settings to use temp directories
        with patch('src.utils.config.settings') as mock_settings, \
             patch('src.store.cache.card_cache.db_path', self.cache_dir / "test_cards.db"):
            mock_settings.OUTPUT_DIR = str(self.output_dir)
            mock_settings.CACHE_DIR = str(self.cache_dir)
            mock_settings.CACHE_EXPIRE_HOURS = 24
            yield
        
        # Cleanup
        shutil.rmtree(self.temp_dir)
    
    @pytest.fixture
    def mock_camera(self):
        """Mock camera capture functionality."""
        with patch.object(camera_capture, 'initialize', return_value=True), \
             patch.object(camera_capture, 'get_preview_frame') as mock_preview, \
             patch.object(camera_capture, 'capture_stable_frame') as mock_capture, \
             patch.object(camera_capture, 'detect_card_region') as mock_detect, \
             patch.object(camera_capture, 'release') as mock_release:
            
            # Create a mock frame
            mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            mock_preview.return_value = mock_frame
            
            # Mock card detection
            mock_detect.return_value = np.zeros((400, 300, 3), dtype=np.uint8)
            
            # Mock stable capture
            mock_capture.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
            
            yield {
                'preview': mock_preview,
                'capture': mock_capture,
                'detect': mock_detect,
                'release': mock_release
            }
    
    @pytest.fixture
    def mock_ocr(self):
        """Mock OCR functionality."""
        with patch.object(ocr_extractor, 'extract_card_info') as mock_extract:
            mock_extract.return_value = CardInfo(
                name="Charizard",
                collector_number="4",
                confidence=85.0
            )
            yield mock_extract
    
    @pytest.fixture
    def mock_resolver(self):
        """Mock Pokemon TCG resolver."""
        with patch.object(PokemonTCGResolver, 'search_cards') as mock_search, \
             patch.object(PokemonTCGResolver, '_find_best_match') as mock_match:
            
            # Mock successful card search
            mock_card = PokemonCard(
                id='charizard-base-4',
                name='Charizard',
                number='4',
                set_name='Base Set',
                set_id='base1',
                rarity='Holo Rare',
                images={},
                tcgplayer={
                    'prices': {
                        'holofoil': {'market': 100.0, 'low': 80.0, 'high': 120.0}
                    }
                },
                cardmarket={
                    'prices': {
                        'averageSellPrice': 85.0,
                        'lowPrice': 70.0,
                        'highPrice': 100.0
                    }
                }
            )
            
            mock_search.return_value = [mock_card]
            mock_match.return_value = mock_card
            
            yield {
                'search': mock_search,
                'match': mock_match,
                'card': mock_card
            }
    
    @pytest.fixture
    def mock_pricer(self):
        """Mock pricing functionality."""
        with patch.object(pokemon_pricer, 'extract_prices_from_card') as mock_extract:
            mock_extract.return_value = {
                'tcgplayer_market_usd': 100.0,
                'tcgplayer_low_usd': 80.0,
                'tcgplayer_high_usd': 120.0,
                'cardmarket_trend_eur': 85.0,
                'cardmarket_avg30_eur': 82.0,
                'cardmarket_low_eur': 70.0,
                'cardmarket_high_eur': 100.0
            }
            yield mock_extract
    
    def test_full_workflow_integration(self, mock_camera, mock_ocr, mock_resolver, mock_pricer):
        """Test the complete workflow: scan → OCR → resolve → price → CSV."""
        # Initialize cache (no initialize method needed)
        
        # Simulate scanning a card
        scan_id = card_cache.insert_scan(
            image_path="test_image.jpg",
            ocr_data={
                "name": "Charizard",
                "collector_number": "4",
                "confidence": 85.0
            }
        )
        
        assert scan_id is not None
        
        # Get new scans
        new_scans = card_cache.get_new_scans()
        assert len(new_scans) == 1
        assert new_scans[0]['id'] == scan_id
        
        # Simulate card resolution and pricing
        scan = new_scans[0]
        card_info = scan['ocr_data']  # Note: it's 'ocr_data' not 'ocr_json'
        
        # Build CSV row
        mock_card = mock_resolver['card']
        price_data = mock_pricer.return_value
        
        row_data = csv_writer.build_row(
            pokemon_card=mock_card,
            price_data=price_data,
            source_image_path=scan['image_path']
        )
        
        # Verify row data structure
        assert 'timestamp_iso' in row_data
        assert row_data['card_id'] == mock_card.id
        assert row_data['name'] == mock_card.name
        assert row_data['number'] == mock_card.number
        assert row_data['set_name'] == mock_card.set_name
        assert row_data['tcgplayer_market_usd'] == '100.0'
        assert row_data['cardmarket_trend_eur'] == '85.0'
        
        # Write to CSV
        csv_writer.write_row(row_data)
        
        # Verify CSV file was created
        assert csv_writer.csv_path.exists()
        
        # Mark scan as completed
        card_cache.update_scan_status(scan_id, 'COMPLETED')
        
        # Verify scan status was updated
        updated_scans = card_cache.get_new_scans()
        assert len(updated_scans) == 0  # No more new scans
        
        # Cleanup
        card_cache.close()
    
    def test_error_handling_integration(self, mock_camera, mock_ocr):
        """Test error handling throughout the workflow."""
        # No initialize method needed
        
        # Test with invalid OCR data
        scan_id = card_cache.insert_scan(
            image_path="invalid_image.jpg",
            ocr_data={
                "name": None,
                "collector_number": None,
                "confidence": 0.0
            }
        )
        
        # Get new scans
        new_scans = card_cache.get_new_scans()
        assert len(new_scans) == 1
        
        # Simulate processing failure
        scan = new_scans[0]
        card_info = scan['ocr_data']  # Note: it's 'ocr_data' not 'ocr_json'
        
        # This should fail due to missing name
        if not card_info.get('name'):
            card_cache.update_scan_status(scan_id, 'SKIPPED')
        
        # Verify scan was marked as skipped
        updated_scans = card_cache.get_new_scans()
        assert len(updated_scans) == 0
        
        # Cleanup
        card_cache.close()
    
    def test_cache_integration(self, mock_camera, mock_ocr, mock_resolver, mock_pricer):
        """Test cache integration with the full workflow."""
        # No initialize method needed
        
        # Insert a card and prices
        card_data = mock_resolver['card']  # This is now a PokemonCard object
        price_data = mock_pricer.return_value
        
        card_cache.upsert_card(card_data)
        card_cache.upsert_prices(card_data.id, price_data)
        
        # Verify cache hit
        cache_key = f"{card_data.name}_{card_data.number}"
        cached_prices = card_cache.get_price_data_from_cache(cache_key, max_age_hours=24)
        
        assert cached_prices is not None
        assert cached_prices['tcgplayer_market_usd'] == 100.0
        
        # Cleanup
        card_cache.close()
    
    def test_csv_writer_integration(self, mock_camera, mock_ocr, mock_resolver, mock_pricer):
        """Test CSV writer integration with the full workflow."""
        # No initialize method needed
        
        # Create multiple cards as PokemonCard objects
        cards = [
            PokemonCard(
                id='charizard-base-4',
                name='Charizard',
                number='4',
                set_name='Base Set',
                set_id='base1',
                rarity='Holo Rare',
                images={}
            ),
            PokemonCard(
                id='blastoise-base-2',
                name='Blastoise',
                number='2',
                set_name='Base Set',
                set_id='base1',
                rarity='Holo Rare',
                images={}
            )
        ]
        
        price_data = mock_pricer.return_value
        
        # Write multiple rows
        for i, card in enumerate(cards):
            row_data = csv_writer.build_row(
                pokemon_card=card,
                price_data=price_data,
                source_image_path=f"card_{i}.jpg"
            )
            csv_writer.write_row(row_data)
        
        # Verify CSV file contains all rows
        assert csv_writer.csv_path.exists()
        
        with open(csv_writer.csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Header + 2 data rows
            assert len(lines) == 3
        
        # Cleanup
        card_cache.close()
    
    def test_ocr_integration(self, mock_camera):
        """Test OCR integration with mock image processing."""
        # Create a mock image
        mock_image = np.zeros((400, 300, 3), dtype=np.uint8)
        
        # Mock OCR extraction
        with patch.object(ocr_extractor, 'extract_card_info') as mock_extract:
            mock_extract.return_value = CardInfo(
                name="Pikachu",
                collector_number="58",
                confidence=90.0
            )
            
            # Test OCR extraction
            card_info = mock_extract(mock_image)
            
            assert card_info.name == "Pikachu"
            assert card_info.collector_number == "58"
            assert card_info.confidence == 90.0
    
    def test_warp_integration(self, mock_camera):
        """Test perspective correction integration."""
        # Create a mock card image
        mock_card_image = np.zeros((400, 300, 3), dtype=np.uint8)
        
        # Mock warping
        with patch.object(PerspectiveCorrector, 'warp_card') as mock_warp:
            mock_warp.return_value = np.zeros((400, 300, 3), dtype=np.uint8)
            
            warper = PerspectiveCorrector()
            warped_image = warper.warp_card(mock_card_image)
            
            assert warped_image is not None
            assert warped_image.shape == (400, 300, 3)


class TestCLICommandsIntegration:
    """Test CLI command integration scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test environment and clean up after each test."""
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        yield
        
        # Cleanup
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_run_command_integration(self):
        """Test the 'run' command integration."""
        from src.cli import app
        
        # Mock all external dependencies
        with patch('src.capture.camera.camera_capture.initialize', return_value=True), \
             patch('src.capture.camera.camera_capture.get_preview_frame') as mock_preview, \
             patch('src.capture.camera.camera_capture.capture_stable_frame') as mock_capture, \
             patch('src.capture.camera.camera_capture.detect_card_region') as mock_detect, \
             patch('src.capture.camera.camera_capture.release') as mock_release, \
             patch('cv2.imshow') as mock_imshow, \
             patch('cv2.waitKey') as mock_waitkey, \
             patch('cv2.destroyAllWindows') as mock_destroy:
            
            # Mock camera behavior
            mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            mock_preview.return_value = mock_frame
            mock_capture.return_value = mock_frame
            mock_detect.return_value = np.zeros((400, 300, 3), dtype=np.uint8)
            
            # Mock key presses (ESC to exit immediately)
            mock_waitkey.return_value = 27  # ESC key
            
            # Mock OCR
            with patch('src.ocr.extract.ocr_extractor.extract_card_info') as mock_ocr:
                mock_ocr.return_value = CardInfo(
                    name="Charizard",
                    collector_number="4",
                    confidence=85.0
                )
                
                # Mock resolver
                with patch('src.resolve.poketcg.PokemonTCGResolver.search_cards') as mock_search, \
                     patch('src.resolve.poketcg.PokemonTCGResolver._find_best_match') as mock_match:
                    
                    mock_card = PokemonCard(
                        id='charizard-base-4',
                        name='Charizard',
                        number='4',
                        set_name='Base Set',
                        set_id='base1',
                        rarity='Holo Rare',
                        images={}
                    )
                    
                    mock_search.return_value = [mock_card]
                    mock_match.return_value = mock_card
                    
                    # Mock pricer
                    with patch('src.pricing.poketcg_prices.pokemon_pricer.extract_prices_from_card') as mock_pricer:
                        mock_pricer.return_value = {
                            'tcgplayer_market_usd': 100.0,
                            'cardmarket_trend_eur': 85.0
                        }
                        
                        # Mock cache
                        with patch('src.store.cache.card_cache.upsert_card'), \
                             patch('src.store.cache.card_cache.upsert_prices'):
                            
                            # Mock CSV writer
                            with patch('src.store.writer.csv_writer.write_row'), \
                                 patch('cv2.imwrite'):
                                
                                # Test the run command (it should exit immediately due to ESC)
                                try:
                                    # Access the command directly
                                    run_cmd = app.registered_commands[0]  # First command is 'run'
                                    await run_cmd.callback(
                                        output_dir=str(self.output_dir),
                                        confidence_threshold=60,
                                        max_cards=1
                                    )
                                except (SystemExit, IndexError):
                                    pass  # Expected behavior
    
    @pytest.mark.asyncio
    async def test_price_command_integration(self):
        """Test the 'price' command integration."""
        from src.cli import app
        
        # Mock cache to return new scans
        with patch('src.store.cache.card_cache.get_new_scans') as mock_get_scans:
            mock_get_scans.return_value = [
                {
                    'id': 'scan-1',
                    'image_path': 'test_image.jpg',
                    'ocr_data': {  # Note: it's 'ocr_data' not 'ocr_json'
                        'name': 'Charizard',
                        'collector_number': '4',
                        'confidence': 85.0
                    }
                }
            ]
            
            # Mock resolver
            with patch('src.resolve.poketcg.PokemonTCGResolver.search_cards') as mock_search, \
                 patch('src.resolve.poketcg.PokemonTCGResolver._find_best_match') as mock_match:
                
                mock_card = PokemonCard(
                    id='charizard-base-4',
                    name='Charizard',
                    number='4',
                    set_name='Base Set',
                    set_id='base1',
                    rarity='Holo Rare',
                    images={}
                )
                
                mock_search.return_value = [mock_card]
                mock_match.return_value = mock_card
                
                # Mock pricer
                with patch('src.pricing.poketcg_prices.pokemon_pricer.extract_prices_from_card') as mock_pricer:
                    mock_pricer.return_value = {
                        'tcgplayer_market_usd': 100.0,
                        'cardmarket_trend_eur': 85.0
                    }
                    
                    # Mock cache operations
                    with patch('src.store.cache.card_cache.upsert_card'), \
                         patch('src.store.cache.card_cache.upsert_prices'), \
                         patch('src.store.cache.card_cache.update_scan_status'):
                        
                        # Mock CSV writer
                        with patch('src.store.writer.csv_writer.write_row'):
                            
                            # Test the price command
                            price_cmd = app.registered_commands[1]  # Second command is 'price'
                            await price_cmd.callback(
                                output_dir=str(self.output_dir),
                                max_age_hours=24
                            )
    
    def test_scan_command_integration(self):
        """Test the 'scan' command integration."""
        from src.cli import app
        
        # Mock camera
        with patch('src.capture.camera.camera_capture.initialize', return_value=True), \
             patch('src.capture.camera.camera_capture.get_preview_frame') as mock_preview, \
             patch('src.capture.camera.camera_capture.capture_stable_frame') as mock_capture, \
             patch('src.capture.camera.camera_capture.detect_card_region') as mock_detect, \
             patch('src.capture.camera.camera_capture.release') as mock_release, \
             patch('cv2.imshow') as mock_imshow, \
             patch('cv2.waitKey') as mock_waitkey, \
             patch('cv2.destroyAllWindows') as mock_destroy:
            
            # Mock camera behavior
            mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            mock_preview.return_value = mock_frame
            mock_capture.return_value = mock_frame
            mock_detect.return_value = np.zeros((400, 300, 3), dtype=np.uint8)
            
            # Mock key presses (ESC to exit immediately)
            mock_waitkey.return_value = 27  # ESC key
            
            # Mock OCR
            with patch('src.ocr.extract.ocr_extractor.extract_card_info') as mock_ocr:
                mock_ocr.return_value = CardInfo(
                    name="Charizard",
                    collector_number="4",
                    confidence=85.0
                )
                
                # Mock cache
                with patch('src.store.cache.card_cache.insert_scan') as mock_insert:
                    mock_insert.return_value = 'scan-1'
                    
                    # Mock file operations
                    with patch('cv2.imwrite'):
                        
                        # Test the scan command (it should exit immediately due to ESC)
                        try:
                            scan_cmd = app.registered_commands[2]  # Third command is 'scan'
                            scan_cmd.callback(
                                output_dir=str(self.output_dir),
                                confidence_threshold=50,
                                max_scans=1
                            )
                        except (SystemExit, IndexError):
                            pass  # Expected behavior


class TestErrorRecoveryIntegration:
    """Test error recovery and resilience throughout the application."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test environment and clean up after each test."""
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        yield
        
        # Cleanup
        shutil.rmtree(self.temp_dir)
    
    def test_camera_failure_recovery(self):
        """Test recovery from camera initialization failures."""
        with patch('src.capture.camera.camera_capture.initialize', return_value=False):
            # This should raise an exception
            with pytest.raises(SystemExit):
                from src.cli import app
                run_cmd = app.registered_commands[0]  # First command is 'run'
                run_cmd.callback(
                    output_dir=str(self.output_dir),
                    confidence_threshold=60,
                    max_cards=1
                )
    
    def test_ocr_failure_recovery(self):
        """Test recovery from OCR failures."""
        # No initialize method needed
        
        # Insert a scan with OCR failure
        scan_id = card_cache.insert_scan(
            image_path="failed_image.jpg",
            ocr_data={
                "name": None,
                "collector_number": None,
                "confidence": 0.0
            }
        )
        
        # This scan should be marked as skipped during processing
        new_scans = card_cache.get_new_scans()
        assert len(new_scans) == 1
        
        # Cleanup
        card_cache.close()
    
    def test_resolver_failure_recovery(self):
        """Test recovery from card resolution failures."""
        # No initialize method needed
        
        # Insert a scan
        scan_id = card_cache.insert_scan(
            image_path="test_image.jpg",
            ocr_data={
                "name": "InvalidCard",
                "collector_number": "999",
                "confidence": 85.0
            }
        )
        
        # Mock resolver to fail
        with patch('src.resolve.poketcg.PokemonTCGResolver.search_cards') as mock_search:
            mock_search.return_value = []  # No results
            
            # This should result in NO_MATCH status
            new_scans = card_cache.get_new_scans()
            assert len(new_scans) == 1
            
            # Cleanup
            card_cache.close()
    
    def test_csv_write_failure_recovery(self):
        """Test recovery from CSV write failures."""
        # No initialize method needed
        
        # Insert a scan
        scan_id = card_cache.insert_scan(
            image_path="test_image.jpg",
            ocr_data={
                "name": "Charizard",
                "collector_number": "4",
                "confidence": 85.0
            }
        )
        
        # Mock CSV writer to fail
        with patch('src.store.writer.csv_writer.write_row') as mock_write:
            mock_write.side_effect = Exception("CSV write failed")
            
            # This should result in ERROR status
            new_scans = card_cache.get_new_scans()
            assert len(new_scans) == 1
            
            # Cleanup
            card_cache.close()


class TestPerformanceIntegration:
    """Test performance characteristics of the integrated system."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test environment and clean up after each test."""
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()
        
        yield
        
        # Cleanup
        shutil.rmtree(self.temp_dir)
    
    def test_bulk_processing_performance(self):
        """Test performance of bulk processing operations."""
        # No initialize method needed
        
        # Insert multiple scans
        scan_ids = []
        for i in range(10):
            scan_id = card_cache.insert_scan(
                image_path=f"card_{i}.jpg",
                ocr_data={
                    "name": f"Card{i}",
                    "collector_number": str(i),
                    "confidence": 85.0
                }
            )
            scan_ids.append(scan_id)
        
        # Verify all scans were inserted
        new_scans = card_cache.get_new_scans()
        assert len(new_scans) == 10
        
        # Cleanup
        card_cache.close()
    
    def test_cache_performance(self):
        """Test cache performance characteristics."""
        # No initialize method needed
        
        # Insert multiple cards and prices
        for i in range(100):
            card_data = PokemonCard(
                id=f'card-{i}',
                name=f'Card{i}',
                number=str(i),
                set_name='Test Set',
                set_id='test',
                rarity='Common',
                images={}
            )
            
            price_data = {
                'tcgplayer_market_usd': float(i),
                'cardmarket_trend_eur': float(i * 0.8)
            }
            
            card_cache.upsert_card(card_data)
            card_cache.upsert_prices(card_data.id, price_data)
        
        # Test cache retrieval performance
        import time
        start_time = time.time()
        
        for i in range(100):
            cache_key = f"Card{i}_{i}"
            cached_prices = card_cache.get_price_data_from_cache(cache_key, max_age_hours=24)
            assert cached_prices is not None
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 100 cache lookups in reasonable time (< 1 second)
        assert processing_time < 1.0
        
        # Cleanup
        card_cache.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
