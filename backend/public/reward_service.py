"""Reward service for calculating streaks and points for drivers."""

from datetime import datetime
from backend.shared import database


def get_driver_rewards(driver_id: int):
    """Fetch driver reward data and calculate streaks."""
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
    
    # Check and award milestone points automatically
    check_and_award_milestones(driver_id, traffic_streak_days, 'traffic')
    check_and_award_milestones(driver_id, parking_streak_days, 'parking')
    
    # Re-fetch current_points after potential milestone awards
    updated_result = database.fetch_all(
        "SELECT current_points FROM driver_profiles WHERE id = %s",
        (driver_id,)
    )
    if updated_result:
        current_points = updated_result[0].get('current_points', 0) or 0
    
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
    """Calculate days since violation occurred."""
    if violation_datetime is None:
        return 0
    
    # Ensure we're working with a datetime object
    if isinstance(violation_datetime, str):
        try:
            violation_datetime = datetime.fromisoformat(violation_datetime.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return 0
    
    now = datetime.now()
    
    # Handle timezone-aware datetime to avoid comparison errors
    if violation_datetime.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=violation_datetime.tzinfo)
    elif violation_datetime.tzinfo is None and now.tzinfo is not None:
        violation_datetime = violation_datetime.replace(tzinfo=now.tzinfo)
    
    delta = now - violation_datetime
    days = delta.days
    
    # Return at least 0 days (no negative streaks)
    return max(0, days)


def calculate_milestone_progress(days_since_violation):
    """Calculate progress toward next 30-day milestone as percentage."""
    if days_since_violation < 0:
        return 0
    
    progress = (days_since_violation % 30) / 30.0 * 100
    return int(round(progress))


def update_driver_points(driver_id: int, points_delta: int):
    """Update driver's points by adding/subtracting delta."""
    query = """
        UPDATE driver_profiles
        SET current_points = current_points + %s
        WHERE id = %s
    """
    
    cursor = database.execute_query(query, (points_delta, driver_id))
    return cursor is not None


def record_violation(driver_id: int, violation_type: str):
    """Record violation and reset corresponding streak."""
    if violation_type not in ['traffic', 'parking']:
        return False
    
    column = 'last_traffic_violation' if violation_type == 'traffic' else 'last_parking_violation'
    
    # Update violation timestamp (resets streak)
    query = f"""
        UPDATE driver_profiles
        SET {column} = CURRENT_TIMESTAMP
        WHERE id = %s
    """
    cursor = database.execute_query(query, (driver_id,))
    
    # Clear milestone awards for this streak type (allows re-earning milestones)
    if cursor is not None:
        clear_query = """
            DELETE FROM milestone_awards
            WHERE driver_id = %s AND streak_type = %s
        """
        database.execute_query(clear_query, (driver_id, violation_type))
    
    return cursor is not None


def check_and_award_milestones(driver_id: int, streak_days: int, streak_type: str):
    """Check and award milestone points if not already awarded."""
    if streak_type not in ['traffic', 'parking']:
        return
    
    # Define milestone points
    milestones = {
        'traffic': {7: 15, 30: 75},
        'parking': {7: 20, 30: 100}
    }
    
    # Check each milestone
    for milestone_days, points in milestones[streak_type].items():
        if streak_days >= milestone_days:
            # Check if already awarded
            if not is_milestone_awarded(driver_id, streak_type, milestone_days):
                # Award points
                if update_driver_points(driver_id, points):
                    # Record the award
                    record_milestone_award(driver_id, streak_type, milestone_days, points)


def is_milestone_awarded(driver_id: int, streak_type: str, milestone_days: int):
    """Check if milestone already awarded."""
    query = """
        SELECT id FROM milestone_awards
        WHERE driver_id = %s AND streak_type = %s AND milestone_days = %s
    """
    result = database.fetch_all(query, (driver_id, streak_type, milestone_days))
    return len(result) > 0


def record_milestone_award(driver_id: int, streak_type: str, milestone_days: int, points_awarded: int):
    """Record milestone award for driver."""
    query = """
        INSERT INTO milestone_awards (driver_id, streak_type, milestone_days, points_awarded)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE awarded_at = CURRENT_TIMESTAMP
    """
    cursor = database.execute_query(query, (driver_id, streak_type, milestone_days, points_awarded))
    return cursor is not None


def fetch_rewards_catalog():
    """Fetch all available rewards from catalog."""
    query = """
        SELECT id, name, description, points_cost, category, available
        FROM rewards_catalog
        WHERE available = TRUE
        ORDER BY points_cost ASC
    """
    
    results = database.fetch_all(query)
    return results if results else []


def redeem_reward(driver_id: int, reward_id: int):
    """Process reward redemption for driver."""
    # Fetch the reward details
    reward_query = """
        SELECT id, name, points_cost, available
        FROM rewards_catalog
        WHERE id = %s AND available = TRUE
    """
    reward_result = database.fetch_all(reward_query, (reward_id,))
    
    if not reward_result:
        return {
            "success": False,
            "message": "Reward not found or unavailable"
        }
    
    reward = reward_result[0]
    points_cost = reward['points_cost']
    reward_name = reward['name']
    
    # Fetch driver's current points
    driver_query = """
        SELECT current_points
        FROM driver_profiles
        WHERE id = %s
    """
    driver_result = database.fetch_all(driver_query, (driver_id,))
    
    if not driver_result:
        return {
            "success": False,
            "message": "Driver not found"
        }
    
    current_points = driver_result[0]['current_points']
    
    # Check if driver has enough points
    if current_points < points_cost:
        return {
            "success": False,
            "message": f"Insufficient points. You have {current_points}, but need {points_cost} points."
        }
    
    # Deduct points from driver
    new_points = current_points - points_cost
    update_query = """
        UPDATE driver_profiles
        SET current_points = %s
        WHERE id = %s
    """
    database.execute_query(update_query, (new_points, driver_id))
    
    return {
        "success": True,
        "message": f"Successfully redeemed {reward_name}!",
        "remaining_points": new_points,
        "reward_name": reward_name
    }

