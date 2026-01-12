"""Reward service for calculating streaks and points for drivers."""

from datetime import datetime
from backend import database


def get_driver_rewards(driver_id: int):
    """
    Fetch driver reward data from the database and calculate streaks.
    
    Args:
        driver_id (int): The ID of the driver in driver_profiles table
        
    Returns:
        dict: Contains current_points, traffic_streak_days, parking_streak_days,
              traffic_progress_pct (0-100 toward 30-day milestone),
              parking_progress_pct (0-100 toward 30-day milestone)
    """
    query = """
        SELECT id, current_points, last_traffic_violation, last_parking_violation
        FROM driver_profiles
        WHERE id = %s
    """
    
    result = database.fetch_all(query, (driver_id,))
    
    if not result:
        # Return default data if driver not found
        return {
            "error": "Driver not found",
            "current_points": 0,
            "traffic_streak_days": 0,
            "parking_streak_days": 0,
            "traffic_progress_pct": 0,
            "parking_progress_pct": 0
        }
    
    driver = result[0]
    current_points = driver.get('current_points', 0) or 0
    
    # Parse violation timestamps
    last_traffic_violation = driver.get('last_traffic_violation')
    last_parking_violation = driver.get('last_parking_violation')
    
    # Calculate days since each violation
    traffic_streak_days = calculate_days_since(last_traffic_violation)
    parking_streak_days = calculate_days_since(last_parking_violation)
    
    # Calculate progress toward 30-day milestone (0-100%)
    # Formula: (days_since_violation % 30) / 30 * 100
    traffic_progress_pct = calculate_milestone_progress(traffic_streak_days)
    parking_progress_pct = calculate_milestone_progress(parking_streak_days)
    
    return {
        "current_points": current_points,
        "traffic_streak_days": traffic_streak_days,
        "parking_streak_days": parking_streak_days,
        "traffic_progress_pct": traffic_progress_pct,
        "parking_progress_pct": parking_progress_pct
    }


def calculate_days_since(violation_datetime):
    """
    Calculate the number of days since a violation occurred.
    
    Args:
        violation_datetime: datetime object from database
        
    Returns:
        int: Number of days since violation (0 if violation is today or in the future)
    """
    if violation_datetime is None:
        return 0
    
    # Ensure we're working with a datetime object
    if isinstance(violation_datetime, str):
        try:
            violation_datetime = datetime.fromisoformat(violation_datetime.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return 0
    
    now = datetime.now()
    
    # Handle timezone-aware datetime
    if violation_datetime.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=violation_datetime.tzinfo)
    elif violation_datetime.tzinfo is None and now.tzinfo is not None:
        violation_datetime = violation_datetime.replace(tzinfo=now.tzinfo)
    
    delta = now - violation_datetime
    days = delta.days
    
    # Return at least 0 days (no negative streaks)
    return max(0, days)


def calculate_milestone_progress(days_since_violation):
    """
    Calculate progress toward the next 30-day milestone as a percentage (0-100).
    
    Formula: (days_since_violation % 30) / 30 * 100
    
    Args:
        days_since_violation (int): Number of days since a violation
        
    Returns:
        int: Progress percentage (0-100) toward the next milestone
    """
    if days_since_violation < 0:
        return 0
    
    progress = (days_since_violation % 30) / 30.0 * 100
    return int(round(progress))


def update_driver_points(driver_id: int, points_delta: int):
    """
    Update a driver's points by adding/subtracting the given delta.
    
    Args:
        driver_id (int): The ID of the driver
        points_delta (int): The amount to add (positive) or subtract (negative)
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    query = """
        UPDATE driver_profiles
        SET current_points = current_points + %s
        WHERE id = %s
    """
    
    cursor = database.execute_query(query, (points_delta, driver_id))
    return cursor is not None


def record_violation(driver_id: int, violation_type: str):
    """
    Record a violation for a driver (traffic or parking) and reset the corresponding streak.
    
    Args:
        driver_id (int): The ID of the driver
        violation_type (str): Either 'traffic' or 'parking'
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    if violation_type not in ['traffic', 'parking']:
        return False
    
    column = 'last_traffic_violation' if violation_type == 'traffic' else 'last_parking_violation'
    query = f"""
        UPDATE driver_profiles
        SET {column} = CURRENT_TIMESTAMP
        WHERE id = %s
    """
    
    cursor = database.execute_query(query, (driver_id,))
    return cursor is not None
