"""Command-line interface for Pokemon Scanner - Focused on scanning and logging."""

import asyncio
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .capture.camera import camera_capture
from .capture.warp import PerspectiveCorrector
from .ocr.extract import ocr_extractor
from .pricing.poketcg_prices import pokemon_pricer
from .resolve.poketcg import PokemonTCGResolver
from .store.cache import card_cache
from .store.writer import csv_writer
from .utils.config import settings
from .utils.log import configure_logging, get_logger
from .ocr.extract import CardInfo

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console
console = Console()

app = typer.Typer(
    name="pokemon-scanner",
    help="Pokemon Card Scanner - Focused on accurate scanning and logging",
    add_completion=False,
)


@app.command()
async def run(
    output_dir: str = typer.Option(
        "output", "--output", "-o", help="Output directory for cards"
    ),
    confidence_threshold: int = typer.Option(
        60, "--confidence", "-c", help="Minimum OCR confidence (0-100)"
    ),
    max_cards: int = typer.Option(
        100, "--max-cards", "-m", help="Maximum number of cards per session"
    ),
):
    """One-pass loop: capture → warp → OCR → resolve → price → build_row → append → beep; loop until ESC."""

    console.print(
        Panel.fit(
            "[bold blue]Pokemon Card Scanner - RUN Mode[/bold blue]\n"
            "[dim]One-pass: capture → OCR → resolve → price → CSV[/dim]",
            border_style="blue",
        )
    )

    try:
        # Initialize components
        resolver, warper = await _initialize_run_components()

        # Card processing loop
        card_count = 0
        successful_cards = 0

        _display_run_instructions()

        while card_count < max_cards:
            # Get preview frame
            frame = camera_capture.get_preview_frame()
            if frame is None:
                console.print("[yellow]⚠ No camera frame available[/yellow]")
                time.sleep(0.1)
                continue

            # Prepare and display frame
            _prepare_run_frame(frame, card_count, max_cards)

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == 32:  # SPACE
                card_count += 1
                if await _process_run_card(card_count, confidence_threshold, output_dir, warper, resolver):
                    successful_cards += 1

                # Flash effect
                _show_run_flash_effect(frame)

        # Show final summary
        _show_run_summary(card_count, successful_cards, output_dir)

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


async def _initialize_run_components() -> Tuple[PokemonTCGResolver, PerspectiveCorrector]:
    """Initialize the run mode components."""
    with console.status("[bold green]Initializing components...", spinner="dots"):
        if not camera_capture.initialize():
            console.print("[red]❌ Failed to initialize camera[/red]")
            raise typer.Exit(1)

        resolver = PokemonTCGResolver()
        warper = PerspectiveCorrector()
        console.print("[green]✓ Components initialized successfully[/green]")
        return resolver, warper


def _display_run_instructions() -> None:
    """Display run mode instructions to the user."""
    console.print("\n[bold]Card Processing Instructions:[/bold]")
    console.print("• Hold a Pokemon card in front of the camera")
    console.print("• Press [bold]SPACE[/bold] to capture and process when ready")
    console.print("• Press [bold]ESC[/bold] to exit")
    console.print("• Ensure good lighting and steady hands")


def _prepare_run_frame(frame: np.ndarray, card_count: int, max_cards: int) -> None:
    """Prepare and display the run frame with overlay information."""
    # Show preview with instructions
    preview_text = f"Card {card_count + 1}/{max_cards} | SPACE to capture & process | ESC to exit"
    cv2.putText(
        frame,
        preview_text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    # Show ROI boxes
    _draw_run_roi_boxes(frame)

    # Display frame
    cv2.imshow(
        "Pokemon Scanner - RUN Mode - Press SPACE to capture & process, ESC to exit",
        frame,
    )


def _draw_run_roi_boxes(frame: np.ndarray) -> None:
    """Draw ROI boxes on the run frame."""
    height, width = frame.shape[:2]

    # Name ROI (green)
    name_y1, name_y2 = int(height * 0.05), int(height * 0.14)
    name_x1, name_x2 = int(width * 0.08), int(width * 0.92)
    cv2.rectangle(frame, (name_x1, name_y1), (name_x2, name_y2), (0, 255, 0), 2)
    cv2.putText(
        frame,
        "NAME",
        (name_x1, name_y1 - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        2,
    )

    # Collector number ROI (blue)
    num_y1, num_y2 = int(height * 0.88), int(height * 0.98)
    num_x1, num_x2 = int(width * 0.05), int(width * 0.95)
    cv2.rectangle(frame, (num_x1, num_y1), (num_x2, num_y2), (255, 0, 0), 2)
    cv2.putText(
        frame,
        "NUMBER",
        (num_x1, num_y1 - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 0, 0),
        2,
    )


async def _process_run_card(
    card_count: int, confidence_threshold: int, output_dir: str, 
    warper: PerspectiveCorrector, resolver: PokemonTCGResolver
) -> bool:
    """Process a single card in run mode. Returns True if successful."""
    console.print(f"\n[bold]Processing card {card_count}...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Capturing stable frame...", total=None)

        # Capture stable frame
        stable_frame = _capture_run_stable_frame(progress, task)
        if stable_frame is None:
            return False

        # Detect and warp card
        warped_image = _detect_and_warp_run_card(progress, task, stable_frame, warper)
        if warped_image is None:
            return False

        # Extract card info
        card_info, processing_time = _extract_run_card_info(progress, task, warped_image)
        if card_info is None or card_info.confidence < confidence_threshold:
            if card_info and card_info.confidence < confidence_threshold:
                console.print(
                    f"[yellow]⚠ Low confidence ({card_info.confidence:.1f}%) - consider rescanning[/yellow]"
                )
            return False

        # Resolve and price card
        best_card, price_data = await _resolve_and_price_run_card(progress, task, card_info, resolver)
        if best_card is None and price_data is None:
            return False

        # Write to CSV and save image
        if _write_run_csv_and_save_image(progress, task, card_count, card_info, best_card,
                                         price_data, warped_image, output_dir):
            _display_run_results(card_count, card_info, processing_time, best_card)
            _beep_notification()
            return True

    return False


def _capture_run_stable_frame(progress, task) -> Optional[np.ndarray]:
    """Capture a stable frame for run mode processing."""
    stable_frame = camera_capture.capture_stable_frame(stabilization_frames=5)
    if stable_frame is None:
        console.print("[red]❌ Failed to capture frame[/red]")
        return None
    return stable_frame


def _detect_and_warp_run_card(progress, task, stable_frame: np.ndarray,
                              warper: PerspectiveCorrector) -> Optional[np.ndarray]:
    """Detect and warp the card in run mode."""
    progress.update(task, description="Detecting and warping card...")

    # Detect card region
    card_image = camera_capture.detect_card_region(stable_frame)
    if card_image is None:
        console.print("[red]❌ No card detected in frame[/red]")
        return None

    # Warp to standard size
    warped_image = warper.warp_card(card_image)
    if warped_image is None:
        console.print("[red]❌ Failed to warp card[/red]")
        return None

    return warped_image


def _extract_run_card_info(progress, task, warped_image: np.ndarray) -> Tuple[Optional[CardInfo], int]:
    """Extract card information using OCR in run mode."""
    progress.update(task, description="Extracting text with OCR...")
    
    start_time = time.time()
    card_info = ocr_extractor.extract_card_info(warped_image)
    processing_time = int((time.time() - start_time) * 1000)
    
    return card_info, processing_time


async def _resolve_and_price_run_card(progress, task, card_info: CardInfo,
                                      resolver: PokemonTCGResolver) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Resolve and price a card in run mode."""
    progress.update(task, description="Resolving card data...")

    # Check cache first
    cache_key = _build_run_cache_key(card_info)
    cached_prices = card_cache.get_price_data_from_cache(
        cache_key, max_age_hours=settings.CACHE_EXPIRE_HOURS
    )

    if cached_prices:
        console.print("[green]✓ Using cached pricing data[/green]")
        return None, cached_prices

    # Resolve card data
    try:
        best_card, price_data = await _resolve_run_card(card_info, resolver)
        if best_card is None:
            return None, None

        # Cache the results
        card_cache.upsert_card(best_card)
        card_cache.upsert_prices(best_card.id, price_data)

        return best_card, price_data

    except Exception as e:
        console.print(f"[red]❌ Error resolving card: {e}[/red]")
        logger.error("Card resolution error", error=str(e))
        return None, None


def _build_run_cache_key(card_info: CardInfo) -> str:
    """Build cache key for run mode."""
    if card_info.name and card_info.collector_number:
        return f"{card_info.name}_{card_info.collector_number}"
    return card_info.name or ""


async def _resolve_run_card(card_info: CardInfo, resolver: PokemonTCGResolver) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Resolve a card in run mode."""
    # Build search query
    if card_info.collector_number:
        query = f"number:{card_info.collector_number}"
        if card_info.name:
            query += f' name:"{card_info.name}"'
    else:
        query = f'name:"{card_info.name}"'

    # Search for cards
    cards = await resolver.search_cards(query, limit=10)
    if not cards:
        console.print("[red]❌ No cards found[/red]")
        return None, None

    # Find best match
    best_card = resolver.find_best_match(cards, card_info)
    if not best_card:
        console.print("[red]❌ No suitable match found[/red]")
        return None, None

    # Extract pricing
    price_data = pokemon_pricer.extract_prices_from_card(best_card)
    return best_card, price_data


def _write_run_csv_and_save_image(progress, task, card_count: int, card_info: CardInfo,
                                  best_card: Optional[Dict], price_data: Dict,
                                  warped_image: np.ndarray, output_dir: str) -> bool:
    """Write CSV row and save image for run mode."""
    progress.update(task, description="Writing to CSV...")

    try:
        # Create a mock card dict if we don't have one from resolution
        if not best_card:
            best_card = _create_run_mock_card(card_count, card_info)

        # Build CSV row
        row_data = csv_writer.build_row(
            pokemon_card=best_card,
            price_data=price_data,
            source_image_path=f"images/card_{card_count}.jpg",
        )

        csv_writer.write_row(row_data)

        # Save warped image
        _save_run_image(card_count, warped_image, output_dir)

        return True

    except Exception as e:
        console.print(f"[red]❌ Error writing to CSV: {e}[/red]")
        logger.error("CSV write error", error=str(e))
        return False


def _create_run_mock_card(card_count: int, card_info: CardInfo) -> Dict:
    """Create a mock card dict for run mode cached pricing data."""
    return {
        "id": f"cached-{card_count}",
        "name": card_info.name or "",
        "number": card_info.collector_number or "",
        "set": {"name": "", "id": ""},
        "rarity": "",
    }


def _save_run_image(card_count: int, warped_image: np.ndarray, output_dir: str) -> None:
    """Save the warped image in run mode."""
    project_root = Path(__file__).parent.parent
    image_path = (
        project_root
        / output_dir
        / "images"
        / f"card_{card_count}.jpg"
    )
    image_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(image_path), warped_image)


def _display_run_results(card_count: int, card_info: CardInfo, processing_time: int, best_card: Optional[Dict]) -> None:
    """Display results for a processed run card."""
    console.print(f"\n[green]✓ Card {card_count} processed successfully![/green]")

    # Create results table
    table = Table(title=f"Card {card_count} Results")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row(
        "Card Name", card_info.name or "[red]Not detected[/red]"
    )
    table.add_row(
        "Collector Number",
        card_info.collector_number or "[red]Not found[/red]",
    )
    table.add_row("OCR Confidence", f"{card_info.confidence:.1f}%")
    table.add_row("Processing Time", f"{processing_time}ms")
    table.add_row("Image Saved", f"card_{card_count}.jpg")

    if best_card and "set" in best_card:
        table.add_row("Resolved Name", best_card.get("name", ""))
        table.add_row(
            "Set", best_card.get("set", {}).get("name", "")
        )
        table.add_row("Rarity", best_card.get("rarity", ""))

    console.print(table)


def _beep_notification() -> None:
    """Play a beep notification."""
    print("\a")  # System beep


def _show_run_flash_effect(frame: np.ndarray) -> None:
    """Show a flash effect after processing a run card."""
    flash_frame = np.ones_like(frame) * 255
    cv2.imshow(
        "Pokemon Scanner - RUN Mode - Press SPACE to capture & process, ESC to exit",
        flash_frame,
    )
    cv2.waitKey(200)


def _show_run_summary(card_count: int, successful_cards: int, output_dir: str) -> None:
    """Show the final run summary."""
    console.print("\n[bold]Card Processing Session Complete[/bold]")
    console.print(f"Total cards: {card_count}")
    console.print(f"Successful cards: {successful_cards}")
    console.print(
        f"Success rate: {(successful_cards / card_count * 100):.1f}%"
        if card_count > 0
        else "N/A"
    )

    # Show output location
    project_root = Path(__file__).parent.parent
    output_path = project_root / output_dir
    if output_path.exists():
        csv_files = list(output_path.glob("*.csv"))
        image_files = list((output_path / "images").glob("*.jpg"))

        console.print("\n[bold]Output Files:[/bold]")
        console.print(f"CSV logs: {len(csv_files)} files")
        console.print(f"Images: {len(image_files)} files")
        console.print(f"Output directory: {output_path.absolute()}")


@app.command()
async def price(
    output_dir: str = typer.Option(
        "output", "--output", "-o", help="Output directory for cards"
    ),
    max_age_hours: int = typer.Option(
        24, "--max-age", "-a", help="Maximum cache age in hours"
    ),
):
    """Iterate NEW scans → resolve+price → write CSV → mark DONE; sleep ~150–250ms between cards to rate limit."""

    console.print(
        Panel.fit(
            "[bold blue]Pokemon Card Scanner - PRICE Mode[/bold blue]\n"
            "[dim]Batch processing: resolve → price → CSV[/dim]",
            border_style="blue",
        )
    )

    try:
        # Initialize components
        resolver = await _initialize_pricing_components()

        # Get new scans from cache
        new_scans = card_cache.get_new_scans()
        if not new_scans:
            console.print("[yellow]⚠ No new scans to process[/yellow]")
            return

        console.print(f"[green]✓ Found {len(new_scans)} new scans to process[/green]")

        # Process each scan
        processed_count, successful_count = await _process_all_scans(
            new_scans, resolver, max_age_hours
        )

        # Show final summary
        _show_pricing_summary(new_scans, processed_count, successful_count, output_dir)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Batch processing interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error during batch processing: {e}[/red]")
        logger.error("Batch processing error", error=str(e))
        raise typer.Exit(1)


async def _initialize_pricing_components() -> PokemonTCGResolver:
    """Initialize the pricing components."""
    with console.status("[bold green]Initializing components...", spinner="dots"):
        resolver = PokemonTCGResolver()
        console.print("[green]✓ Components initialized successfully[/green]")
        return resolver


async def _process_all_scans(
    new_scans: List[Dict], resolver: PokemonTCGResolver, max_age_hours: int
) -> Tuple[int, int]:
    """Process all scans and return counts."""
    processed_count = 0
    successful_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for i, scan in enumerate(new_scans):
            progress.update(
                progress.add_task(
                    f"Processing scan {i + 1}/{len(new_scans)}...", total=None
                )
            )

            try:
                if await _process_single_scan(i, scan, resolver, max_age_hours):
                    successful_count += 1
                processed_count += 1

                # Rate limiting: sleep between cards
                if i < len(new_scans) - 1:  # Don't sleep after last card
                    await _apply_rate_limiting()

            except Exception as e:
                console.print(
                    f"[red]❌ Unexpected error processing scan {i + 1}: {e}[/red]"
                )
                logger.error(
                    "Unexpected scan processing error",
                    scan_id=scan["id"],
                    error=str(e),
                )
                card_cache.update_scan_status(scan["id"], "ERROR")
                continue

    return processed_count, successful_count


async def _process_single_scan(
    i: int, scan: Dict, resolver: PokemonTCGResolver, max_age_hours: int
) -> bool:
    """Process a single scan. Returns True if successful."""
    console.print(f"\n[bold]Processing scan {i + 1}[/bold]")
    console.print(f"Image: {scan['image_path']}")

    # Check if we have OCR data
    if not _has_valid_ocr_data(scan):
        console.print(
            "[yellow]⚠ No OCR data available, marking as SKIPPED[/yellow]"
        )
        card_cache.update_scan_status(scan["id"], "SKIPPED")
        return False

    card_info = scan["ocr_json"]

    # Check cache first
    cached_prices = _check_price_cache(card_info, max_age_hours)
    if cached_prices:
        console.print("[green]✓ Using cached pricing data[/green]")
        price_data = cached_prices
        best_card = None  # We don't have the full card data from cache
    else:
        # Resolve card data
        best_card, price_data = await _resolve_and_price_card(
            card_info, resolver, scan["id"]
        )
        if best_card is None:
            return False

    # Build CSV row and write
    if _write_csv_row(scan, best_card, price_data, card_info, i):
        # Mark scan as completed
        card_cache.update_scan_status(scan["id"], "COMPLETED")
        _display_scan_results(i, card_info, best_card)
        return True

    return False


def _has_valid_ocr_data(scan: Dict) -> bool:
    """Check if scan has valid OCR data."""
    return scan["ocr_json"] and scan["ocr_json"].get("name")


def _check_price_cache(card_info: Dict, max_age_hours: int) -> Optional[Dict]:
    """Check if pricing data exists in cache."""
    cache_key = _build_cache_key(card_info)
    return card_cache.get_price_data_from_cache(cache_key, max_age_hours=max_age_hours)


def _build_cache_key(card_info: Dict) -> str:
    """Build cache key from card info."""
    if card_info.get("name") and card_info.get("collector_number"):
        return f"{card_info.get('name')}_{card_info.get('collector_number')}"
    return card_info.get("name", "")


async def _resolve_and_price_card(
    card_info: Dict, resolver: PokemonTCGResolver, scan_id: str
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Resolve card data and extract pricing."""
    try:
        # Build search query
        query = _build_search_query(card_info)

        # Search for cards
        cards = await resolver.search_cards(query, limit=10)
        if not cards:
            console.print("[red]❌ No cards found[/red]")
            card_cache.update_scan_status(scan_id, "NO_MATCH")
            return None, None

        # Find best match
        best_card = resolver.find_best_match(cards, card_info)
        if not best_card:
            console.print("[red]❌ No suitable match found[/red]")
            card_cache.update_scan_status(scan_id, "NO_MATCH")
            return None, None

        # Extract pricing
        price_data = pokemon_pricer.extract_prices_from_card(best_card)

        # Cache the results
        card_cache.upsert_card(best_card)
        card_cache.upsert_prices(best_card.id, price_data)

        return best_card, price_data

    except Exception as e:
        console.print(f"[red]❌ Error resolving card: {e}[/red]")
        logger.error("Card resolution error", error=str(e))
        card_cache.update_scan_status(scan_id, "ERROR")
        return None, None


def _build_search_query(card_info: Dict) -> str:
    """Build search query from card info."""
    if card_info.get("collector_number"):
        query = f"number:{card_info['collector_number']}"
        if card_info.get("name"):
            query += f" name:\"{card_info['name']}\""
    else:
        query = f"name:\"{card_info['name']}\""
    return query


def _write_csv_row(
    scan: Dict, best_card: Optional[Dict], price_data: Dict, card_info: Dict, i: int
) -> bool:
    """Write CSV row for the scan. Returns True if successful."""
    try:
        # Create a mock card dict if we don't have one from resolution
        if not best_card:
            best_card = _create_mock_card(scan["id"], card_info)

        row_data = csv_writer.build_row(
            pokemon_card=best_card,
            price_data=price_data,
            source_image_path=scan["image_path"],
        )

        csv_writer.write_row(row_data)
        return True

    except Exception as e:
        console.print(f"[red]❌ Error writing to CSV: {e}[/red]")
        logger.error("CSV write error", error=str(e))
        card_cache.update_scan_status(scan["id"], "ERROR")
        return False


def _create_mock_card(scan_id: str, card_info: Dict) -> Dict:
    """Create a mock card dict for cached pricing data."""
    return {
        "id": f"cached-{scan_id}",
        "name": card_info.get("name", ""),
        "number": card_info.get("collector_number", ""),
        "set": {"name": "", "id": ""},
        "rarity": "",
    }


def _display_scan_results(i: int, card_info: Dict, best_card: Optional[Dict]) -> None:
    """Display results for a processed scan."""
    console.print(f"[green]✓ Scan {i + 1} processed successfully![/green]")

    # Create results table
    table = Table(title=f"Scan {i + 1} Results")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row(
        "Card Name",
        card_info.get("name") or "[red]Not detected[/red]",
    )
    table.add_row(
        "Collector Number",
        card_info.get("collector_number") or "[red]Not found[/red]",
    )
    table.add_row(
        "OCR Confidence", f"{card_info.get('confidence', 0):.1f}%"
    )

    if best_card and "set" in best_card:
        table.add_row("Resolved Name", best_card.get("name", ""))
        table.add_row(
            "Set", best_card.get("set", {}).get("name", "")
        )
        table.add_row("Rarity", best_card.get("rarity", ""))

    console.print(table)


async def _apply_rate_limiting() -> None:
    """Apply rate limiting between card processing."""
    sleep_time = 0.2  # 200ms for ~5 QPS
    console.print(f"[dim]Rate limiting: sleeping {sleep_time}s...[/dim]")
    await asyncio.sleep(sleep_time)


def _show_pricing_summary(
    new_scans: List[Dict], processed_count: int, successful_count: int, output_dir: str
) -> None:
    """Show the final pricing summary."""
    console.print("\n[bold]Batch Processing Complete[/bold]")
    console.print(f"Total scans: {len(new_scans)}")
    console.print(f"Processed: {processed_count}")
    console.print(f"Successful: {successful_count}")
    console.print(
        f"Success rate: {(successful_count / processed_count * 100):.1f}%"
        if processed_count > 0
        else "N/A"
    )

    # Show output location
    project_root = Path(__file__).parent.parent
    output_path = project_root / output_dir
    if output_path.exists():
        csv_files = list(output_path.glob("*.csv"))
        console.print("\n[bold]Output Files:[/bold]")
        console.print(f"CSV logs: {len(csv_files)} files")
        console.print(f"Output directory: {output_path.absolute()}")


@app.command()
def scan(
    output_dir: str = typer.Option(
        "output", "--output", "-o", help="Output directory for scans"
    ),
    confidence_threshold: int = typer.Option(
        50, "--confidence", "-c", help="Minimum OCR confidence (0-100)"
    ),
    max_scans: int = typer.Option(
        100, "--max-scans", "-m", help="Maximum number of scans per session"
    ),
):
    """Scan Pokemon cards and log results with high accuracy."""

    console.print(
        Panel.fit(
            "[bold blue]Pokemon Card Scanner[/bold blue]\n"
            "[dim]Focus: Accurate scanning and logging[/dim]",
            border_style="blue",
        )
    )

    try:
        # Initialize camera
        if not _initialize_camera():
            raise typer.Exit(1)

        # Scan loop
        scan_count = 0
        successful_scans = 0

        _display_scanning_instructions()

        while scan_count < max_scans:
            # Get preview frame
            frame = camera_capture.get_preview_frame()
            if frame is None:
                console.print("[yellow]⚠ No camera frame available[/yellow]")
                time.sleep(0.1)
                continue

            # Prepare and display frame
            _prepare_frame_for_display(frame, scan_count, max_scans)

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == 32:  # SPACE
                scan_count += 1
                if _process_scan(scan_count, output_dir, confidence_threshold):
                    successful_scans += 1

                # Flash effect
                _show_flash_effect(frame)

        # Show final summary
        _show_scan_summary(scan_count, successful_scans, output_dir)

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


def _initialize_camera() -> bool:
    """Initialize the camera for scanning."""
    with console.status("[bold green]Initializing camera...", spinner="dots"):
        if not camera_capture.initialize():
            console.print("[red]❌ Failed to initialize camera[/red]")
            return False

    console.print("[green]✓ Camera initialized successfully[/green]")
    return True


def _display_scanning_instructions() -> None:
    """Display scanning instructions to the user."""
    console.print("\n[bold]Scanning Instructions:[/bold]")
    console.print("• Hold a Pokemon card in front of the camera")
    console.print("• Press [bold]SPACE[/bold] to capture when ready")
    console.print("• Press [bold]ESC[/bold] to exit")
    console.print("• Ensure good lighting and steady hands")


def _prepare_frame_for_display(frame: np.ndarray, scan_count: int, max_scans: int) -> None:
    """Prepare and display the frame with overlay information."""
    # Show preview with instructions
    preview_text = (
        f"Scan {scan_count + 1}/{max_scans} | SPACE to capture | ESC to exit"
    )
    cv2.putText(
        frame,
        preview_text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    # Show ROI boxes
    _draw_roi_boxes(frame)

    # Display frame
    cv2.imshow("Pokemon Scanner - Press SPACE to capture, ESC to exit", frame)


def _draw_roi_boxes(frame: np.ndarray) -> None:
    """Draw ROI boxes on the frame."""
    height, width = frame.shape[:2]

    # Name ROI (green)
    name_y1, name_y2 = int(height * 0.05), int(height * 0.14)
    name_x1, name_x2 = int(width * 0.08), int(width * 0.92)
    cv2.rectangle(frame, (name_x1, name_y1), (name_x2, name_y2), (0, 255, 0), 2)
    cv2.putText(
        frame,
        "NAME",
        (name_x1, name_y1 - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        2,
    )

    # Collector number ROI (blue)
    num_y1, num_y2 = int(height * 0.88), int(height * 0.98)
    num_x1, num_x2 = int(width * 0.05), int(width * 0.95)
    cv2.rectangle(frame, (num_x1, num_y1), (num_x2, num_y2), (255, 0, 0), 2)
    cv2.putText(
        frame,
        "NUMBER",
        (num_x1, num_y1 - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 0, 0),
        2,
    )


def _process_scan(scan_count: int, output_dir: str, confidence_threshold: int) -> bool:
    """Process a single scan. Returns True if successful."""
    console.print(f"\n[bold]Capturing scan {scan_count}...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Capturing stable frame...", total=None)

        # Capture stable frame
        stable_frame = _capture_stable_frame(progress, task)
        if stable_frame is None:
            return False

        # Detect card region
        card_image = _detect_card_region(progress, task, stable_frame)
        if card_image is None:
            return False

        # Extract card info
        card_info, processing_time = _extract_card_info(progress, task, card_image)
        if card_info is None:
            return False

        # Log scan data
        _log_scan_data(progress, task, scan_count, card_info, card_image, output_dir, processing_time)

        # Display results and feedback
        _display_scan_results_scan_mode(scan_count, card_info, processing_time)

    return True


def _capture_stable_frame(progress, task) -> Optional[np.ndarray]:
    """Capture a stable frame for processing."""
    stable_frame = camera_capture.capture_stable_frame(stabilization_frames=5)
    if stable_frame is None:
        console.print("[red]❌ Failed to capture frame[/red]")
        return None
    return stable_frame


def _detect_card_region(progress, task, stable_frame: np.ndarray) -> Optional[np.ndarray]:
    """Detect the card region in the frame."""
    progress.update(task, description="Detecting card region...")
    card_image = camera_capture.detect_card_region(stable_frame)
    if card_image is None:
        console.print("[red]❌ No card detected in frame[/red]")
        return None
    return card_image


def _extract_card_info(progress, task, card_image: np.ndarray) -> Tuple[Optional[CardInfo], int]:
    """Extract card information using OCR."""
    progress.update(task, description="Extracting text with OCR...")
    
    start_time = time.time()
    card_info = ocr_extractor.extract_card_info(card_image)
    processing_time = int((time.time() - start_time) * 1000)
    
    return card_info, processing_time


def _log_scan_data(progress, task, scan_count: int, card_info: CardInfo, 
                   card_image: np.ndarray, output_dir: str, processing_time: int) -> None:
    """Log the scan data to file and cache."""
    progress.update(task, description="Logging scan data...")

    # Save the image
    image_filename = f"scan_{scan_count}.jpg"
    project_root = Path(__file__).parent.parent
    image_path = project_root / output_dir / "images" / image_filename
    image_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(image_path), card_image)

    # Insert scan into cache with OCR data
    _ = card_cache.insert_scan(
        image_path=str(image_path),
        ocr_json={
            "name": card_info.name,
            "collector_number": card_info.collector_number,
            "confidence": card_info.confidence,
        },
    )


def _display_scan_results_scan_mode(scan_count: int, card_info: CardInfo, processing_time: int) -> None:
    """Display the scan results and provide feedback."""
    # Display results
    console.print(f"\n[green]✓ Scan {scan_count} completed![/green]")

    # Create results table
    table = Table(title=f"Scan {scan_count} Results")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row(
        "Card Name", card_info.name or "[red]Not detected[/red]"
    )
    table.add_row(
        "Collector Number",
        card_info.collector_number or "[red]Not found[/red]",
    )
    table.add_row("OCR Confidence", f"{card_info.confidence:.1f}%")
    table.add_row("Processing Time", f"{processing_time}ms")
    table.add_row("Image Saved", f"scan_{scan_count}.jpg")
    table.add_row("Scan ID", "Generated")

    console.print(table)

    # Confidence feedback
    _show_confidence_feedback(card_info)

    # Recommendations
    _show_recommendations(card_info)

    console.print(
        "[dim]💡 Use 'python -m src.cli price' to process this scan for pricing data[/dim]"
    )


def _show_confidence_feedback(card_info: CardInfo) -> None:
    """Show confidence-based feedback to the user."""
    if card_info.confidence >= 80:
        console.print("[green]🎯 High confidence scan![/green]")
    elif card_info.confidence >= 50:
        console.print(
            "[yellow]⚠ Medium confidence - consider rescanning[/yellow]"
        )
    else:
        console.print("[red]❌ Low confidence - please rescan[/red]")


def _show_recommendations(card_info: CardInfo) -> None:
    """Show recommendations based on scan results."""
    if not card_info.name:
        console.print(
            "[yellow]💡 Tip: Ensure the card name is clearly visible in the green box[/yellow]"
        )
    if not card_info.collector_number:
        console.print(
            "[yellow]💡 Tip: Make sure the collector number is visible in the blue box[/yellow]"
        )


def _show_flash_effect(frame: np.ndarray) -> None:
    """Show a flash effect after capturing a scan."""
    flash_frame = np.ones_like(frame) * 255
    cv2.imshow(
        "Pokemon Scanner - Press SPACE to capture, ESC to exit", flash_frame
    )
    cv2.waitKey(200)


def _show_scan_summary(scan_count: int, successful_scans: int, output_dir: str) -> None:
    """Show the final scan summary."""
    console.print("\n[bold]Scanning Session Complete[/bold]")
    console.print(f"Total scans: {scan_count}")
    console.print(f"Successful scans: {successful_scans}")
    console.print(
        f"Success rate: {(successful_scans / scan_count * 100):.1f}%"
        if scan_count > 0
        else "N/A"
    )

    # Show output location
    project_root = Path(__file__).parent.parent
    output_path = project_root / output_dir
    if output_path.exists():
        csv_files = list(output_path.glob("*.csv"))
        image_files = list((output_path / "images").glob("*.jpg"))

        console.print("\n[bold]Output Files:[/bold]")
        console.print(f"CSV logs: {len(csv_files)} files")
        console.print(f"Images: {len(image_files)} files")
        console.print(f"Output directory: {output_path.absolute()}")


if __name__ == "__main__":
    app()
