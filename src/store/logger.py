"""Data logging for Pokemon card scans."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

from ..ocr.extract import CardInfo, OCRResult
from ..utils.config import settings
from ..utils.log import LoggerMixin


class CardDataLogger(LoggerMixin):
    """Logs card scan data with images and OCR results."""

    def __init__(self):
        self.output_dir = Path("output")
        self.images_dir = self.output_dir / "images"
        self.logs_dir = self.output_dir / "logs"

        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # CSV file for card data
        self.csv_file = (
            self.output_dir / f"card_scans_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        self.csv_columns = [
            "timestamp_iso",
            "scan_id",
            "image_filename",
            "card_name",
            "collector_number",
            "ocr_confidence",
            "processing_time_ms",
            "status",
            "notes",
        ]

        # Initialize CSV file
        self._init_csv()

        self.logger.info(
            "Card data logger initialized",
            output_dir=str(self.output_dir),
            csv_file=str(self.csv_file),
        )

    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist."""
        if not self.csv_file.exists():
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_columns)
                writer.writeheader()
            self.logger.info("CSV file created", file=str(self.csv_file))

    def log_card_scan(
        self,
        card_image: Any,
        card_info: CardInfo,
        processing_time_ms: int,
        scan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log a card scan with image and OCR results."""
        try:
            # Generate scan ID if not provided
            if not scan_id:
                scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"

            # Save image
            image_filename = f"{scan_id}.jpg"
            image_path = self.images_dir / image_filename

            # Ensure image is in correct format
            if hasattr(card_image, "shape"):  # numpy array
                cv2.imwrite(str(image_path), card_image)
            else:
                self.logger.warning("Invalid image format, skipping image save")
                image_filename = "no_image"

            # Prepare CSV row
            csv_row = {
                "timestamp_iso": datetime.now().isoformat(),
                "scan_id": scan_id,
                "image_filename": image_filename,
                "card_name": card_info.name or "",
                "collector_number": card_info.collector_number or "",
                "ocr_confidence": round(card_info.confidence, 2),
                "processing_time_ms": processing_time_ms,
                "status": "completed" if card_info.confidence > 0 else "failed",
                "notes": self._generate_notes(card_info),
            }

            # Write to CSV
            with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_columns)
                writer.writerow(csv_row)

            # Save detailed log
            self._save_detailed_log(scan_id, card_info, csv_row)

            self.logger.info(
                "Card scan logged successfully",
                scan_id=scan_id,
                card_name=card_info.name,
                collector_number=card_info.collector_number,
                confidence=card_info.confidence,
                image_filename=image_filename,
            )

            return {
                "scan_id": scan_id,
                "image_filename": image_filename,
                "csv_row": csv_row,
                "status": "success",
            }

        except Exception as e:
            self.logger.error("Failed to log card scan", error=str(e))
            return {"scan_id": scan_id or "unknown", "status": "error", "error": str(e)}

    def _generate_notes(self, card_info: CardInfo) -> str:
        """Generate notes about the scan."""
        notes = []

        if not card_info.name:
            notes.append("No name extracted")
        if not card_info.collector_number:
            notes.append("No collector number found")

        if card_info.ocr_result:
            ocr = card_info.ocr_result
            if ocr.preprocessing_steps:
                for field, steps in ocr.preprocessing_steps.items():
                    if isinstance(steps, dict) and "method" in steps:
                        notes.append(f"{field}: {steps['method']}")

        if card_info.confidence < 50:
            notes.append("Low confidence scan")
        elif card_info.confidence < 80:
            notes.append("Medium confidence scan")
        else:
            notes.append("High confidence scan")

        return "; ".join(notes) if notes else "Normal scan"

    def _save_detailed_log(
        self, scan_id: str, card_info: CardInfo, csv_row: Dict[str, Any]
    ):
        """Save detailed log with OCR results and preprocessing info."""
        try:
            log_data = {
                "scan_id": scan_id,
                "timestamp": csv_row["timestamp_iso"],
                "card_info": {
                    "name": card_info.name,
                    "collector_number": card_info.collector_number,
                    "confidence": card_info.confidence,
                },
                "ocr_result": None,
                "csv_data": csv_row,
            }

            if card_info.ocr_result:
                log_data["ocr_result"] = {
                    "raw_text": card_info.ocr_result.raw_text,
                    "preprocessing_steps": card_info.ocr_result.preprocessing_steps,
                }

            log_filename = f"{scan_id}_details.json"
            log_path = self.logs_dir / log_filename

            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(
                "Failed to save detailed log", scan_id=scan_id, error=str(e)
            )

    def get_scan_summary(self) -> Dict[str, Any]:
        """Get summary of all scans."""
        try:
            if not self.csv_file.exists():
                return {"total_scans": 0, "scans": []}

            scans = []
            with open(self.csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    scans.append(row)

            # Calculate statistics
            total_scans = len(scans)
            successful_scans = len([s for s in scans if s["status"] == "completed"])
            failed_scans = total_scans - successful_scans

            # Average confidence
            confidences = [
                float(s["ocr_confidence"]) for s in scans if s["ocr_confidence"]
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "total_scans": total_scans,
                "successful_scans": successful_scans,
                "failed_scans": failed_scans,
                "average_confidence": round(avg_confidence, 2),
                "scans": scans[-10:],  # Last 10 scans
            }

        except Exception as e:
            self.logger.error("Failed to get scan summary", error=str(e))
            return {"error": str(e)}

    def export_summary_csv(self, filename: Optional[str] = None) -> str:
        """Export a summary CSV with all scans."""
        if not filename:
            filename = f"scan_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        summary_path = self.output_dir / filename

        try:
            summary = self.get_scan_summary()
            if "error" in summary:
                raise Exception(summary["error"])

            with open(summary_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_columns)
                writer.writeheader()
                for scan in summary["scans"]:
                    writer.writerow(scan)

            self.logger.info("Summary CSV exported", file=str(summary_path))
            return str(summary_path)

        except Exception as e:
            self.logger.error("Failed to export summary CSV", error=str(e))
            raise


# Global singleton
card_data_logger = CardDataLogger()
