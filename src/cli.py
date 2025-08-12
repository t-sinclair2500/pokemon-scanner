"""Command-line interface for Pokemon Scanner - Focused on scanning and logging."""

import time
import asyncio
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
import cv2
import numpy as np

from .capture.camera import camera_capture
from .capture.warp import PerspectiveCorrector
from .ocr.extract import ocr_extractor
from .resolve.poketcg import PokemonTCGResolver
from .pricing.poketcg_prices import pokemon_pricer
from .store.cache import card_cache
from .store.writer import csv_writer
from .utils.log import configure_logging, get_logger
from .utils.config import settings

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console
console = Console()

app = typer.Typer(
    name="pokemon-scanner",
    help="Pokemon Card Scanner - Focused on accurate scanning and logging",
    add_completion=False
)


@app.command()
async def run(
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory for cards"),
    confidence_threshold: int = typer.Option(60, "--confidence", "-c", help="Minimum OCR confidence (0-100)"),
    max_cards: int = typer.Option(100, "--max-cards", "-m", help="Maximum number of cards per session")
):
    """One-pass loop: capture → warp → OCR → resolve → price → build_row → append → beep; loop until ESC."""
    
    console.print(Panel.fit(
        "[bold blue]Pokemon Card Scanner - RUN Mode[/bold blue]\n"
        "[dim]One-pass: capture → OCR → resolve → price → CSV[/dim]",
        border_style="blue"
    ))
    
    try:
        # Initialize components
        with console.status("[bold green]Initializing components...", spinner="dots"):
            if not camera_capture.initialize():
                console.print("[red]❌ Failed to initialize camera[/red]")
                raise typer.Exit(1)
            
            resolver = PokemonTCGResolver()
            warper = PerspectiveCorrector()
            console.print("[green]✓ Components initialized successfully[/green]")
        
        # CSV writer is already imported
        
        # Card processing loop
        card_count = 0
        successful_cards = 0
        
        console.print("\n[bold]Card Processing Instructions:[/bold]")
        console.print("• Hold a Pokemon card in front of the camera")
        console.print("• Press [bold]SPACE[/bold] to capture and process when ready")
        console.print("• Press [bold]ESC[/bold] to exit")
        console.print("• Ensure good lighting and steady hands")
        
        while card_count < max_cards:
            # Get preview frame
            frame = camera_capture.get_preview_frame()
            if frame is None:
                console.print("[yellow]⚠ No camera frame available[/yellow]")
                time.sleep(0.1)
                continue
            
            # Show preview with instructions
            preview_text = f"Card {card_count + 1}/{max_cards} | SPACE to capture & process | ESC to exit"
            cv2.putText(frame, preview_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show ROI boxes
            height, width = frame.shape[:2]
            
            # Name ROI (green)
            name_y1, name_y2 = int(height * 0.05), int(height * 0.14)
            name_x1, name_x2 = int(width * 0.08), int(width * 0.92)
            cv2.rectangle(frame, (name_x1, name_y1), (name_x2, name_y2), (0, 255, 0), 2)
            cv2.putText(frame, "NAME", (name_x1, name_y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Collector number ROI (blue)
            num_y1, num_y2 = int(height * 0.88), int(height * 0.98)
            num_x1, num_x2 = int(width * 0.05), int(width * 0.95)
            cv2.rectangle(frame, (num_x1, num_y1), (num_x2, num_y2), (255, 0, 0), 2)
            cv2.putText(frame, "NUMBER", (num_x1, num_y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # Display frame
            cv2.imshow("Pokemon Scanner - RUN Mode - Press SPACE to capture & process, ESC to exit", frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == 32:  # SPACE
                card_count += 1
                console.print(f"\n[bold]Processing card {card_count}...[/bold]")
                
                # Capture stable frame
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Capturing stable frame...", total=None)
                    
                    # Capture multiple frames for stability
                    stable_frame = camera_capture.capture_stable_frame(stabilization_frames=5)
                    if stable_frame is None:
                        console.print("[red]❌ Failed to capture frame[/red]")
                        continue
                    
                    progress.update(task, description="Detecting and warping card...")
                    
                    # Detect card region and warp
                    card_image = camera_capture.detect_card_region(stable_frame)
                    if card_image is None:
                        console.print("[red]❌ No card detected in frame[/red]")
                        continue
                    
                    # Warp to standard size
                    warped_image = warper.warp_card(card_image)
                    if warped_image is None:
                        console.print("[red]❌ Failed to warp card[/red]")
                        continue
                    
                    progress.update(task, description="Extracting text with OCR...")
                    
                    # Extract card info with timing
                    start_time = time.time()
                    card_info = ocr_extractor.extract_card_info(warped_image)
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    if card_info.confidence < confidence_threshold:
                        console.print(f"[yellow]⚠ Low confidence ({card_info.confidence:.1f}%) - consider rescanning[/yellow]")
                        continue
                    
                    progress.update(task, description="Resolving card data...")
                    
                    # Check cache first
                    cache_key = f"{card_info.name}_{card_info.collector_number}" if card_info.name and card_info.collector_number else card_info.name
                    cached_prices = card_cache.get_price_data_from_cache(cache_key, max_age_hours=settings.CACHE_EXPIRE_HOURS)
                    
                    if cached_prices:
                        console.print("[green]✓ Using cached pricing data[/green]")
                        price_data = cached_prices
                        best_card = None  # We don't have the full card data from cache
                    else:
                        # Resolve card data
                        try:
                            if card_info.collector_number:
                                query = f"number:{card_info.collector_number}"
                                if card_info.name:
                                    query += f" name:\"{card_info.name}\""
                            else:
                                query = f"name:\"{card_info.name}\""
                            
                            cards = await resolver.search_cards(query, limit=10)
                            if not cards:
                                console.print("[red]❌ No cards found[/red]")
                                continue
                            
                            # Find best match
                            best_card = resolver.find_best_match(cards, card_info)
                            if not best_card:
                                console.print("[red]❌ No suitable match found[/red]")
                                continue
                            
                            # Extract pricing
                            price_data = pokemon_pricer.extract_prices_from_card(best_card)
                            
                            # Cache the results
                            card_cache.upsert_card(best_card)
                            card_cache.upsert_prices(best_card.id, price_data)
                            
                        except Exception as e:
                            console.print(f"[red]❌ Error resolving card: {e}[/red]")
                            logger.error("Card resolution error", error=str(e))
                            continue
                    
                    progress.update(task, description="Writing to CSV...")
                    
                    # Build CSV row and write
                    try:
                        # Create a mock card dict if we don't have one from resolution
                        if not best_card:
                            best_card = {
                                'id': f"cached-{card_count}",
                                'name': card_info.name or '',
                                'number': card_info.collector_number or '',
                                'set': {'name': '', 'id': ''},
                                'rarity': ''
                            }
                        
                        row_data = csv_writer.build_row(
                            pokemon_card=best_card,
                            price_data=price_data,
                            source_image_path=f"images/card_{card_count}.jpg"
                        )
                        
                        csv_writer.write_row(row_data)
                        
                        # Save warped image
                        # Resolve output directory relative to project root
                        project_root = Path(__file__).parent.parent
                        image_path = project_root / output_dir / "images" / f"card_{card_count}.jpg"
                        image_path.parent.mkdir(parents=True, exist_ok=True)
                        cv2.imwrite(str(image_path), warped_image)
                        
                        successful_cards += 1
                        
                        # Display results
                        console.print(f"\n[green]✓ Card {card_count} processed successfully![/green]")
                        
                        # Create results table
                        table = Table(title=f"Card {card_count} Results")
                        table.add_column("Field", style="cyan")
                        table.add_column("Value", style="white")
                        
                        table.add_row("Card Name", card_info.name or "[red]Not detected[/red]")
                        table.add_row("Collector Number", card_info.collector_number or "[red]Not found[/red]")
                        table.add_row("OCR Confidence", f"{card_info.confidence:.1f}%")
                        table.add_row("Processing Time", f"{processing_time}ms")
                        table.add_row("Image Saved", f"card_{card_count}.jpg")
                        
                        if best_card and 'set' in best_card:
                            table.add_row("Resolved Name", best_card.get('name', ''))
                            table.add_row("Set", best_card.get('set', {}).get('name', ''))
                            table.add_row("Rarity", best_card.get('rarity', ''))
                        
                        console.print(table)
                        
                        # Beep notification
                        print("\a")  # System beep
                        
                    except Exception as e:
                        console.print(f"[red]❌ Error writing to CSV: {e}[/red]")
                        logger.error("CSV write error", error=str(e))
                        continue
                
                # Flash effect
                flash_frame = np.ones_like(frame) * 255
                cv2.imshow("Pokemon Scanner - RUN Mode - Press SPACE to capture & process, ESC to exit", flash_frame)
                cv2.waitKey(200)
        
        # Final summary
        console.print(f"\n[bold]Card Processing Session Complete[/bold]")
        console.print(f"Total cards: {card_count}")
        console.print(f"Successful cards: {successful_cards}")
        console.print(f"Success rate: {(successful_cards/card_count*100):.1f}%" if card_count > 0 else "N/A")
        
        # Show output location
        # Resolve output directory relative to project root
        project_root = Path(__file__).parent.parent
        output_path = project_root / output_dir
        if output_path.exists():
            csv_files = list(output_path.glob("*.csv"))
            image_files = list((output_path / "images").glob("*.jpg"))
            
            console.print(f"\n[bold]Output Files:[/bold]")
            console.print(f"CSV logs: {len(csv_files)} files")
            console.print(f"Images: {len(image_files)} files")
            console.print(f"Output directory: {output_path.absolute()}")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Card processing interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error during card processing: {e}[/red]")
        logger.error("Card processing error", error=str(e))
        raise typer.Exit(1)
    finally:
        # Cleanup
        camera_capture.release()
        cv2.destroyAllWindows()
        console.print("\n[green]✓ Camera released[/green]")


@app.command()
async def price(
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory for cards"),
    max_age_hours: int = typer.Option(24, "--max-age", "-a", help="Maximum cache age in hours")
):
    """Iterate NEW scans → resolve+price → write CSV → mark DONE; sleep ~150–250ms between cards to rate limit."""
    
    console.print(Panel.fit(
        "[bold blue]Pokemon Card Scanner - PRICE Mode[/bold blue]\n"
        "[dim]Batch processing: resolve → price → CSV[/dim]",
        border_style="blue"
    ))
    
    try:
        # Initialize components
        with console.status("[bold green]Initializing components...", spinner="dots"):
            resolver = PokemonTCGResolver()
            console.print("[green]✓ Components initialized successfully[/green]")
        
        # Get new scans from cache
        new_scans = card_cache.get_new_scans()
        if not new_scans:
            console.print("[yellow]⚠ No new scans to process[/yellow]")
            return
        
        console.print(f"[green]✓ Found {len(new_scans)} new scans to process[/green]")
        
        # Process each scan
        processed_count = 0
        successful_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for i, scan in enumerate(new_scans):
                progress.update(progress.add_task(f"Processing scan {i+1}/{len(new_scans)}...", total=None))
                
                try:
                    console.print(f"\n[bold]Processing scan {i+1}/{len(new_scans)}[/bold]")
                    console.print(f"Image: {scan['image_path']}")
                    
                    # Check if we have OCR data
                    if not scan['ocr_json'] or not scan['ocr_json'].get('name'):
                        console.print("[yellow]⚠ No OCR data available, marking as SKIPPED[/yellow]")
                        card_cache.update_scan_status(scan['id'], 'SKIPPED')
                        continue
                    
                    card_info = scan['ocr_json']
                    
                    # Check cache first
                    cache_key = f"{card_info.get('name')}_{card_info.get('collector_number')}" if card_info.get('name') and card_info.get('collector_number') else card_info.get('name')
                    cached_prices = card_cache.get_price_data_from_cache(cache_key, max_age_hours=max_age_hours)
                    
                    if cached_prices:
                        console.print("[green]✓ Using cached pricing data[/green]")
                        price_data = cached_prices
                        best_card = None  # We don't have the full card data from cache
                    else:
                        # Resolve card data
                        try:
                            if card_info.get('collector_number'):
                                query = f"number:{card_info['collector_number']}"
                                if card_info.get('name'):
                                    query += f" name:\"{card_info['name']}\""
                            else:
                                query = f"name:\"{card_info['name']}\""
                            
                            cards = await resolver.search_cards(query, limit=10)
                            if not cards:
                                console.print("[red]❌ No cards found[/red]")
                                card_cache.update_scan_status(scan['id'], 'NO_MATCH')
                                continue
                            
                            # Find best match
                            best_card = resolver.find_best_match(cards, card_info)
                            if not best_card:
                                console.print("[red]❌ No suitable match found[/red]")
                                card_cache.update_scan_status(scan['id'], 'NO_MATCH')
                                continue
                            
                            # Extract pricing
                            price_data = pokemon_pricer.extract_prices_from_card(best_card)
                            
                            # Cache the results
                            card_cache.upsert_card(best_card)
                            card_cache.upsert_prices(best_card.id, price_data)
                            
                        except Exception as e:
                            console.print(f"[red]❌ Error resolving card: {e}[/red]")
                            logger.error("Card resolution error", error=str(e))
                            card_cache.update_scan_status(scan['id'], 'ERROR')
                            continue
                    
                    # Build CSV row and write
                    try:
                        # Create a mock card dict if we don't have one from resolution
                        if not best_card:
                            best_card = {
                                'id': f"cached-{scan['id']}",
                                'name': card_info.get('name', ''),
                                'number': card_info.get('collector_number', ''),
                                'set': {'name': '', 'id': ''},
                                'rarity': ''
                            }
                        
                        row_data = csv_writer.build_row(
                            pokemon_card=best_card,
                            price_data=price_data,
                            source_image_path=scan['image_path']
                        )
                        
                        csv_writer.write_row(row_data)
                        
                        # Mark scan as completed
                        card_cache.update_scan_status(scan['id'], 'COMPLETED')
                        
                        successful_count += 1
                        
                        # Display results
                        console.print(f"[green]✓ Scan {i+1} processed successfully![/green]")
                        
                        # Create results table
                        table = Table(title=f"Scan {i+1} Results")
                        table.add_column("Field", style="cyan")
                        table.add_column("Value", style="white")
                        
                        table.add_row("Card Name", card_info.get('name') or "[red]Not detected[/red]")
                        table.add_row("Collector Number", card_info.get('collector_number') or "[red]Not found[/red]")
                        table.add_row("OCR Confidence", f"{card_info.get('confidence', 0):.1f}%")
                        
                        if best_card and 'set' in best_card:
                            table.add_row("Resolved Name", best_card.get('name', ''))
                            table.add_row("Set", best_card.get('set', {}).get('name', ''))
                            table.add_row("Rarity", best_card.get('rarity', ''))
                        
                        console.print(table)
                        
                    except Exception as e:
                        console.print(f"[red]❌ Error writing to CSV: {e}[/red]")
                        logger.error("CSV write error", error=str(e))
                        card_cache.update_scan_status(scan['id'], 'ERROR')
                        continue
                    
                    processed_count += 1
                    
                    # Rate limiting: sleep between cards
                    if i < len(new_scans) - 1:  # Don't sleep after last card
                        sleep_time = 0.2  # 200ms for ~5 QPS
                        console.print(f"[dim]Rate limiting: sleeping {sleep_time}s...[/dim]")
                        await asyncio.sleep(sleep_time)
                
                except Exception as e:
                    console.print(f"[red]❌ Unexpected error processing scan {i+1}: {e}[/red]")
                    logger.error("Unexpected scan processing error", scan_id=scan['id'], error=str(e))
                    card_cache.update_scan_status(scan['id'], 'ERROR')
                    continue
        
        # Final summary
        console.print(f"\n[bold]Batch Processing Complete[/bold]")
        console.print(f"Total scans: {len(new_scans)}")
        console.print(f"Processed: {processed_count}")
        console.print(f"Successful: {successful_count}")
        console.print(f"Success rate: {(successful_count/processed_count*100):.1f}%" if processed_count > 0 else "N/A")
        
        # Show output location
        # Resolve output directory relative to project root
        project_root = Path(__file__).parent.parent
        output_path = project_root / output_dir
        if output_path.exists():
            csv_files = list(output_path.glob("*.csv"))
            console.print(f"\n[bold]Output Files:[/bold]")
            console.print(f"CSV logs: {len(csv_files)} files")
            console.print(f"Output directory: {output_path.absolute()}")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Batch processing interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error during batch processing: {e}[/red]")
        logger.error("Batch processing error", error=str(e))
        raise typer.Exit(1)


@app.command()
def scan(
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory for scans"),
    confidence_threshold: int = typer.Option(50, "--confidence", "-c", help="Minimum OCR confidence (0-100)"),
    max_scans: int = typer.Option(100, "--max-scans", "-m", help="Maximum number of scans per session")
):
    """Scan Pokemon cards and log results with high accuracy."""
    
    console.print(Panel.fit(
        "[bold blue]Pokemon Card Scanner[/bold blue]\n"
        "[dim]Focus: Accurate scanning and logging[/dim]",
        border_style="blue"
    ))
    
    try:
        # Initialize camera
        with console.status("[bold green]Initializing camera...", spinner="dots"):
            if not camera_capture.initialize():
                console.print("[red]❌ Failed to initialize camera[/red]")
                raise typer.Exit(1)
        
        console.print("[green]✓ Camera initialized successfully[/green]")
        
        # Scan loop
        scan_count = 0
        successful_scans = 0
        
        console.print("\n[bold]Scanning Instructions:[/bold]")
        console.print("• Hold a Pokemon card in front of the camera")
        console.print("• Press [bold]SPACE[/bold] to capture when ready")
        console.print("• Press [bold]ESC[/bold] to exit")
        console.print("• Ensure good lighting and steady hands")
        
        while scan_count < max_scans:
            # Get preview frame
            frame = camera_capture.get_preview_frame()
            if frame is None:
                console.print("[yellow]⚠ No camera frame available[/yellow]")
                time.sleep(0.1)
                continue
            
            # Show preview with instructions
            preview_text = f"Scan {scan_count + 1}/{max_scans} | SPACE to capture | ESC to exit"
            cv2.putText(frame, preview_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show ROI boxes
            height, width = frame.shape[:2]
            
            # Name ROI (green)
            name_y1, name_y2 = int(height * 0.05), int(height * 0.14)
            name_x1, name_x2 = int(width * 0.08), int(width * 0.92)
            cv2.rectangle(frame, (name_x1, name_y1), (name_x2, name_y2), (0, 255, 0), 2)
            cv2.putText(frame, "NAME", (name_x1, name_y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Collector number ROI (blue)
            num_y1, num_y2 = int(height * 0.88), int(height * 0.98)
            num_x1, num_x2 = int(width * 0.05), int(width * 0.95)
            cv2.rectangle(frame, (num_x1, num_y1), (num_x2, num_y2), (255, 0, 0), 2)
            cv2.putText(frame, "NUMBER", (num_x1, num_y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # Display frame
            cv2.imshow("Pokemon Scanner - Press SPACE to capture, ESC to exit", frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == 32:  # SPACE
                scan_count += 1
                console.print(f"\n[bold]Capturing scan {scan_count}...[/bold]")
                
                # Capture stable frame
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Capturing stable frame...", total=None)
                    
                    # Capture multiple frames for stability
                    stable_frame = camera_capture.capture_stable_frame(stabilization_frames=5)
                    if stable_frame is None:
                        console.print("[red]❌ Failed to capture frame[/red]")
                        continue
                    
                    progress.update(task, description="Detecting card region...")
                    
                    # Detect card region
                    card_image = camera_capture.detect_card_region(stable_frame)
                    if card_image is None:
                        console.print("[red]❌ No card detected in frame[/red]")
                        continue
                    
                    progress.update(task, description="Extracting text with OCR...")
                    
                    # Extract card info with timing
                    start_time = time.time()
                    card_info = ocr_extractor.extract_card_info(card_image)
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    progress.update(task, description="Logging scan data...")
                    
                    # Save the image and insert scan into cache
                    image_filename = f"scan_{scan_count}.jpg"
                    # Resolve output directory relative to project root
                    project_root = Path(__file__).parent.parent
                    image_path = project_root / output_dir / "images" / image_filename
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(image_path), card_image)
                    
                    # Insert scan into cache with OCR data
                    scan_id = card_cache.insert_scan(
                        image_path=str(image_path),
                        ocr_json={
                            "name": card_info.name,
                            "collector_number": card_info.collector_number,
                            "confidence": card_info.confidence
                        }
                    )
                    
                    successful_scans += 1
                    
                    # Display results
                    console.print(f"\n[green]✓ Scan {scan_count} completed![/green]")
                    
                    # Create results table
                    table = Table(title=f"Scan {scan_count} Results")
                    table.add_column("Field", style="cyan")
                    table.add_column("Value", style="white")
                    
                    table.add_row("Card Name", card_info.name or "[red]Not detected[/red]")
                    table.add_row("Collector Number", card_info.collector_number or "[red]Not found[/red]")
                    table.add_row("OCR Confidence", f"{card_info.confidence:.1f}%")
                    table.add_row("Processing Time", f"{processing_time}ms")
                    table.add_row("Image Saved", image_filename)
                    table.add_row("Scan ID", scan_id)
                    
                    console.print(table)
                    
                    # Confidence feedback
                    if card_info.confidence >= 80:
                        console.print("[green]🎯 High confidence scan![/green]")
                    elif card_info.confidence >= 50:
                        console.print("[yellow]⚠ Medium confidence - consider rescanning[/yellow]")
                    else:
                        console.print("[red]❌ Low confidence - please rescan[/red]")
                    
                    # Recommendations
                    if not card_info.name:
                        console.print("[yellow]💡 Tip: Ensure the card name is clearly visible in the green box[/yellow]")
                    if not card_info.collector_number:
                        console.print("[yellow]💡 Tip: Make sure the collector number is visible in the blue box[/yellow]")
                    
                    console.print("[dim]💡 Use 'python -m src.cli price' to process this scan for pricing data[/dim]")
                
                # Flash effect
                flash_frame = np.ones_like(frame) * 255
                cv2.imshow("Pokemon Scanner - Press SPACE to capture, ESC to exit", flash_frame)
                cv2.waitKey(200)
        
        # Final summary
        console.print(f"\n[bold]Scanning Session Complete[/bold]")
        console.print(f"Total scans: {scan_count}")
        console.print(f"Successful scans: {successful_scans}")
        console.print(f"Success rate: {(successful_scans/scan_count*100):.1f}%" if scan_count > 0 else "N/A")
        
        # Show output location
        # Resolve output directory relative to project root
        project_root = Path(__file__).parent.parent
        output_path = project_root / output_dir
        if output_path.exists():
            csv_files = list(output_path.glob("*.csv"))
            image_files = list((output_path / "images").glob("*.jpg"))
            
            console.print(f"\n[bold]Output Files:[/bold]")
            console.print(f"CSV logs: {len(csv_files)} files")
            console.print(f"Images: {len(image_files)} files")
            console.print(f"Output directory: {output_path.absolute()}")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Scanning interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error during scanning: {e}[/red]")
        logger.error("Scanning error", error=str(e))
        raise typer.Exit(1)
    finally:
        # Cleanup
        camera_capture.release()
        cv2.destroyAllWindows()
        console.print("\n[green]✓ Camera released[/green]")


if __name__ == "__main__":
    app()