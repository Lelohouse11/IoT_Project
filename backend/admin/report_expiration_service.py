"""Scheduled service to automatically clear expired driver-reported accidents."""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from apscheduler.schedulers.background import BackgroundScheduler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.public import report_service

# Expiration time in seconds (30 minutes)
EXPIRATION_TIME_SECONDS = 30 * 60

# Track report metadata for clearing {report_id: (timestamp, lat, lng, severity, description)}
report_metadata: Dict[str, tuple] = {}

scheduler = BackgroundScheduler()


def check_and_clear_expired_reports():
    """
    Check for driver-reported accidents that are older than 30 minutes
    and mark them as cleared in Orion.
    
    This function is called periodically by the APScheduler.
    """
    now = datetime.now(timezone.utc).timestamp()
    expired_reports = []
    
    # Find all reports that have exceeded the expiration time
    for report_id, timestamp in list(report_service.active_reports.items()):
        age_seconds = now - timestamp
        
        if age_seconds >= EXPIRATION_TIME_SECONDS:
            expired_reports.append(report_id)
    
    # Clear each expired report
    for report_id in expired_reports:
        if report_id in report_metadata:
            _, lat, lng, severity, description = report_metadata[report_id]
            
            success = report_service.clear_accident_report(
                report_id=report_id,
                latitude=lat,
                longitude=lng,
                severity=severity,
                description=description
            )
            
            if success:
                # Clean up metadata tracking
                report_metadata.pop(report_id, None)
                print(f"[expiration] Successfully cleared expired report {report_id}")
            else:
                print(f"[expiration] Failed to clear report {report_id}, will retry next cycle")
        else:
            # Metadata missing - just remove from active reports
            report_service.active_reports.pop(report_id, None)
            print(f"[expiration] Removed {report_id} from active reports (no metadata found)")
    
    if expired_reports:
        print(f"[expiration] Processed {len(expired_reports)} expired report(s)")


def track_report_metadata(report_id: str, latitude: float, longitude: float, severity: str, description: str):
    """
    Store report metadata needed for clearing operations.
    
    Args:
        report_id: The unique report ID
        latitude: Report location latitude
        longitude: Report location longitude
        severity: Report severity level
        description: Report description
    """
    timestamp = datetime.now(timezone.utc).timestamp()
    report_metadata[report_id] = (timestamp, latitude, longitude, severity, description)


def start_expiration_scheduler():
    """
    Start the background scheduler that checks for expired reports every 5 minutes.
    
    Should be called once during application startup.
    """
    # Run the check every 5 minutes
    scheduler.add_job(
        check_and_clear_expired_reports,
        trigger='interval',
        minutes=5,
        id='clear_expired_reports',
        replace_existing=True
    )
    
    scheduler.start()
    print("[expiration] Report expiration scheduler started (runs every 5 minutes)")


def stop_expiration_scheduler():
    """
    Stop the background scheduler.
    
    Should be called during application shutdown.
    """
    if scheduler.running:
        scheduler.shutdown()
        print("[expiration] Report expiration scheduler stopped")
