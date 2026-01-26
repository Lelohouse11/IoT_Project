"""Report router providing endpoints for driver-submitted accident reports."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from backend.public import report_service

router = APIRouter(prefix="/pwa/reports", tags=["reports"])


class AccidentReportRequest(BaseModel):
    """Request model for accident report submission."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    severity: str = Field(..., pattern="^(minor|medium|major)$", description="Severity level")
    description: str = Field(..., min_length=1, max_length=500, description="Accident description")


class AccidentReportResponse(BaseModel):
    """Response model for successful report submission."""
    success: bool
    report_id: str
    message: str


@router.post("", response_model=AccidentReportResponse, status_code=status.HTTP_201_CREATED)
def submit_accident_report(report: AccidentReportRequest):
    """Submit driver-reported accident to Orion Context Broker."""
    try:
        report_id = report_service.submit_accident_report(
            latitude=report.latitude,
            longitude=report.longitude,
            severity=report.severity,
            description=report.description
        )
        
        return AccidentReportResponse(
            success=True,
            report_id=report_id,
            message="Report submitted successfully. Thank you for helping keep our roads safe!"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit report: {str(e)}"
        )
