"""Reward router providing endpoints for driver reward data."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List
from backend import reward_service

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


class RewardResponse(BaseModel):
    """Response model for reward data."""
    current_points: int
    traffic_streak_days: int
    parking_streak_days: int
    traffic_progress_pct: int  # 0-100% progress toward 30-day milestone
    parking_progress_pct: int  # 0-100% progress toward 30-day milestone


class RewardCatalogItem(BaseModel):
    """Response model for reward catalog items."""
    id: int
    name: str
    description: str
    points_cost: int
    category: str
    available: bool


@router.get("/catalog", response_model=List[RewardCatalogItem])
def get_rewards_catalog():
    """
    Get all available rewards from the catalog.
    
    Returns:
        List[RewardCatalogItem]: List of available rewards
    """
    catalog = reward_service.fetch_rewards_catalog()
    return catalog


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
    """Request model for redeeming a specific reward."""
    reward_id: int


@router.post("/{driver_id}/redeem")
def redeem_rewards(driver_id: int, request: RedeemRequest):
    """
    Redeem a specific reward for a driver.
    
    TODO: Add @auth_required decorator when user management is implemented.
    
    Args:
        driver_id (int): The ID of the driver
        request (RedeemRequest): Contains reward_id to redeem
        
    Returns:
        dict: Result with success status, message, and remaining points
        
    Raises:
        HTTPException: If driver not found (404), reward not found (404), or insufficient points (400)
    """
    if driver_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid driver_id")
    
    if request.reward_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reward_id")
    
    # Process the redemption
    result = reward_service.redeem_reward(driver_id, request.reward_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result
