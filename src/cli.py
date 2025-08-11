"""Command-line interface for Pokemon Scanner - Focused on scanning and logging."""

import time
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
from .ocr.extract import ocr_extractor
from .store.logger import card_data_logger
from .store.writer import enhanced_csv_writer
from .utils.log import configure_logging, get_logger

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
                    
                    # Log the scan
                    log_result = card_data_logger.log_card_scan(
                        card_image=card_image,
                        card_info=card_info,
                        processing_time_ms=processing_time
                    )
                    
                    if log_result["status"] == "success":
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
                        table.add_row("Image Saved", log_result["image_filename"])
                        table.add_row("Scan ID", log_result["scan_id"])
                        
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
                        
                    else:
                        console.print(f"[red]❌ Failed to log scan: {log_result.get('error', 'Unknown error')}[/red]")
                
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
        output_path = Path(output_dir)
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


@app.command()
def summary(
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory to analyze")
):
    """Show summary of all scanned cards."""
    
    try:
        output_path = Path(output_dir)
        if not output_path.exists():
            console.print(f"[red]❌ Output directory not found: {output_path}[/red]")
            raise typer.Exit(1)
        
        # Get scan summary
        summary_data = card_data_logger.get_scan_summary()
        
        if "error" in summary_data:
            console.print(f"[red]❌ Error getting summary: {summary_data['error']}[/red]")
            raise typer.Exit(1)
        
        # Display summary
        console.print(Panel.fit(
            f"[bold blue]Scan Summary[/bold blue]\n"
            f"Total Scans: {summary_data['total_scans']}\n"
            f"Successful: {summary_data['successful_scans']}\n"
            f"Failed: {summary_data['failed_scans']}\n"
            f"Avg Confidence: {summary_data['average_confidence']}%",
            border_style="blue"
        ))
        
        if summary_data['scans']:
            # Recent scans table
            table = Table(title="Recent Scans")
            table.add_column("Scan ID", style="cyan")
            table.add_column("Card Name", style="white")
            table.add_column("Collector #", style="white")
            table.add_column("Confidence", style="white")
            table.add_column("Status", style="white")
            table.add_column("Timestamp", style="dim")
            
            for scan in summary_data['scans'][-10:]:  # Last 10
                confidence_color = "green" if float(scan["ocr_confidence"]) >= 80 else "yellow" if float(scan["ocr_confidence"]) >= 50 else "red"
                status_color = "green" if scan["status"] == "completed" else "red"
                
                table.add_row(
                    scan["scan_id"],
                    scan["card_name"] or "[red]None[/red]",
                    scan["collector_number"] or "[red]None[/red]",
                    f"[{confidence_color}]{scan['ocr_confidence']}%[/{confidence_color}]",
                    f"[{status_color}]{scan['status']}[/{status_color}]",
                    scan["timestamp_iso"][:19]  # Truncate microseconds
                )
            
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory"),
    filename: str = typer.Option(None, "--filename", "-f", help="Custom filename for export")
):
    """Export scan data to CSV."""
    
    try:
        export_path = card_data_logger.export_summary_csv(filename)
        console.print(f"[green]✓ Scan data exported to: {export_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Export failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def excel(
    filename: str = typer.Option(None, "--filename", "-f", help="Custom filename for Excel export")
):
    """Export scan data to Excel format."""
    
    try:
        with console.status("[bold green]Exporting to Excel...", spinner="dots"):
            excel_path = enhanced_csv_writer.export_to_excel(filename)
        
        console.print(f"[green]✓ Scan data exported to Excel: {excel_path}[/green]")
        console.print("[dim]Excel file contains: Scans, Details, and Summary sheets[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Excel export failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show comprehensive statistics about scan data."""
    
    try:
        stats_data = enhanced_csv_writer.get_statistics()
        
        if "error" in stats_data:
            console.print(f"[red]❌ {stats_data['error']}[/red]")
            return
        
        if "message" in stats_data:
            console.print(f"[yellow]⚠ {stats_data['message']}[/yellow]")
            return
        
        # Display statistics
        console.print(Panel.fit(
            f"[bold blue]Scan Statistics[/bold blue]\n"
            f"Total Scans: {stats_data['total_scans']}\n"
            f"Success Rate: {stats_data['success_rate']}%\n"
            f"Average Confidence: {stats_data['confidence']['average']}%\n"
            f"Average Processing Time: {stats_data['processing_time']['average_ms']}ms\n"
            f"Unique Cards: {stats_data['cards']['unique_names']} names, {stats_data['cards']['unique_numbers']} numbers",
            border_style="blue"
        ))
        
        # Confidence breakdown
        if stats_data['confidence']['minimum'] > 0:
            console.print(f"\n[bold]Confidence Range:[/bold]")
            console.print(f"  Minimum: {stats_data['confidence']['minimum']}%")
            console.print(f"  Maximum: {stats_data['confidence']['maximum']}%")
        
        # Last scan info
        if stats_data['last_scan']:
            console.print(f"\n[bold]Last Scan:[/bold] {stats_data['last_scan'][:19]}")
        
    except Exception as e:
        console.print(f"[red]❌ Error getting statistics: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def backup(
    backup_name: str = typer.Option(None, "--name", "-n", help="Custom backup name")
):
    """Create a backup of all scan data."""
    
    try:
        with console.status("[bold green]Creating backup...", spinner="dots"):
            backup_path = enhanced_csv_writer.backup_data(backup_name)
        
        console.print(f"[green]✓ Backup created: {backup_path}[/green]")
        console.print("[dim]Backup includes: CSV files, images, and logs[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Backup failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()