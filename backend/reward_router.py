"""Reward router providing endpoints for driver reward data."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend import reward_service

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


class RewardResponse(BaseModel):
    """Response model for reward data."""
    current_points: int
    traffic_streak_days: int
    parking_streak_days: int
    traffic_progress_pct: int  # 0-100% progress toward 30-day milestone
    parking_progress_pct: int  # 0-100% progress toward 30-day milestone


@router.get("/{driver_id}", response_model=RewardResponse)
def get_driver_rewards(driver_id: int):
    """
    Get reward data for a specific driver.
    
    TODO: Add @auth_required decorator when user management is implemented.
    Current endpoint is public for testing purposes.
    
    Args:
        driver_id (int): The ID of the driver in driver_profiles table
        
    Returns:
        RewardResponse: Driver's current points, streak days, and milestone progress
        
    Raises:
        HTTPException: If driver not found (404)
    """
    if driver_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver_id")
    
    rewards = reward_service.get_driver_rewards(driver_id)
    
    if "error" in rewards:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=rewards["error"])
    
    return RewardResponse(**rewards)


class RedeemRequest(BaseModel):
    """Request model for redeeming rewards."""
    points_to_redeem: int


@router.post("/{driver_id}/redeem")
def redeem_rewards(driver_id: int, request: RedeemRequest):
    """
    Redeem rewards for a driver (deduct points).
    
    TODO: Add @auth_required decorator when user management is implemented.
    TODO: Add validation to ensure driver has enough points.
    TODO: Add reward history tracking when implementing full reward catalog.
    
    Args:
        driver_id (int): The ID of the driver
        request (RedeemRequest): Contains points_to_redeem
        
    Returns:
        dict: Updated reward data and confirmation
        
    Raises:
        HTTPException: If driver not found (404) or invalid points (400)
    """
    if driver_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver_id")
    
    if request.points_to_redeem <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Points to redeem must be positive")
    
    # Get current reward data
    rewards = reward_service.get_driver_rewards(driver_id)
    if "error" in rewards:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=rewards["error"])
    
    # Check if driver has enough points
    if rewards["current_points"] < request.points_to_redeem:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient points. Current: {rewards['current_points']}, Required: {request.points_to_redeem}"
        )
    
    # Deduct points (negative delta)
    success = reward_service.update_driver_points(driver_id, -request.points_to_redeem)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to redeem points")
    
    # Fetch updated reward data
    updated_rewards = reward_service.get_driver_rewards(driver_id)
    
    return {
        "success": True,
        "message": f"Successfully redeemed {request.points_to_redeem} points",
        "rewards": RewardResponse(**updated_rewards)
    }
