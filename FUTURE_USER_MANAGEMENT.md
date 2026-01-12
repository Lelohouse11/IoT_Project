# Future: User Management Integration for Reward System

## What's Already Implemented

✅ **Reward System Foundation**
- `driver_profiles` table (independent from `users` table)
- `reward_service.py` - Streak calculations and points logic
- `reward_router.py` - API endpoints (`GET /api/rewards/{driver_id}`, `POST /api/rewards/{driver_id}/redeem`)
- `RewardsPanel.jsx` - Full UI with progress bars and redemption
- Integrated into `map_service.py` (port 8000)

✅ **Database**
- Schema created with `driver_profiles` table
- Test driver seeded (id=1)

## What Needs to Change (Reward System)

### Frontend
**File**: `drivers_side_pwa/src/components/RewardsPanel.jsx` (line ~34)
```javascript
// CHANGE THIS:
const driverId = 1  // Hardcoded test value

// TO THIS:
const driverId = extractUserIdFromToken()  // Extract from auth token
```

### Backend
**File**: `backend/reward_router.py`
- Add `@auth_required` decorator to both endpoints
- Validate that `current_user['id'] == driver_id` (prevent querying other drivers)

## Be Careful About

1. **Separate Tables**: `driver_profiles` is independent from `users` table
   - Decision needed: Keep separate or merge when implementing full user management?
   
2. **Hardcoded Test Driver**: Currently `driver_id=1` everywhere
   - Frontend: Extract from token
   - Tests: Update to use authenticated user
   - API calls: Will work automatically once endpoints are protected

3. **No Violation Tracking Yet**: Streaks won't reset until you integrate with violation system
   - Future: Call `reward_service.record_violation(driver_id, 'traffic')` when violations are recorded

## Integration Points

| Component | Current State | Integration Point |
|-----------|---------------|-------------------|
| `RewardsPanel.jsx` | Hardcoded driver_id=1 | Extract from auth token |
| `reward_router.py` | Public endpoints | Add @auth_required decorator |
| Violations → Streaks | Not integrated | Call record_violation() on violation events |
| Milestones → Points | Not implemented | Add auto-award logic (optional) |
3. Test with real authentication
4. Integrate violation tracking to reset streaks
5. Add milestone rewards (optional, high-impact feature)
