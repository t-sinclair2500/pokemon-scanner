"""Simple notification system with audio feedback."""

import sys
import subprocess
from typing import Optional

from ..utils.log import get_logger


class SimpleNotifier:
    """Simple notification system with beep and status messages."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def beep(self) -> bool:
        """Play system beep sound."""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], 
                             capture_output=True, check=False)
                return True
            else:
                # Fallback to terminal bell
                print("\a", end="", flush=True)
                return True
        except Exception as e:
            self.logger.debug("Error playing beep", error=str(e))
            return False
    
    def status_toast(self, message: str, level: str = "info"):
        """Display status message (no-op fallback if no GUI available)."""
        # In a real GUI application, this would show a toast notification
        # For CLI, we just log it
        if level == "success":
            self.logger.info(f"SUCCESS: {message}")
        elif level == "error":
            self.logger.error(f"ERROR: {message}")
        elif level == "warning":
            self.logger.warning(f"WARNING: {message}")
        else:
            self.logger.info(f"INFO: {message}")


# Global singleton
notifier = SimpleNotifier()