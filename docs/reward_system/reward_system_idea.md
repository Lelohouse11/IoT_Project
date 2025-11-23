# Streak-Based Reward System  
*(Smart Mobility – Driver Identification & Rewards)*  

## Driver Identification  

- Simple login via **email + password**.  
- Each user has a **unique user_id**.  
- Users can optionally register one or more **license plates**.  
- Only users with a registered plate can participate in the **reward system**.  
- Orion Context Broker sends **violation events** including detected plates.  
- Backend checks if the plate belongs to a registered user → updates their streak.  

---

## Reward Logic (Streak System)  

- System tracks **two streaks per user**:  
  - **Parking streak** → no parking violations.  
  - **Traffic streak** → no driving violations.  
- **Automatic daily increment:** each day without violation increases both streaks.  
- **Violation detected:** if Orion notifies a violation for a user’s plate → corresponding streak resets to zero.  
- **Milestones:** on reaching defined streak lengths, users receive reward points.  
- **Points** accumulate in total balance; longer streaks yield higher rewards.  

---

## Point Examples  

| Condition | Reward | Description |
|------------|---------|-------------|
| 7-day clean parking streak | +20 pts | short milestone |
| 30-day clean parking streak | +100 pts | monthly reward |
| 7-day clean traffic streak | +15 pts | safe driving week |
| 30-day clean traffic streak | +75 pts | long-term streak |
| Any violation | reset | lose progress |

---

## Data Model  

Single table: **`users`**

| Field | Description |
|--------|-------------|
| user_id | unique identifier |
| email | login credential |
| password_hash | secure hash |
| license_plates | list/array of registered plates (optional) |
| points_total | accumulated reward points |
| parking_streak | current streak length |
| traffic_streak | current streak length |
| preferences | JSON: driver settings (notifications, visibility) |
| created_at | registration date |

---

## Data Flow  

```text
Daily Scheduler
     ↓
Increment streaks for all users without recent violations
     ↓
Violation detected by sensor or system
     ↓
Image sent to Vision AI (University System)
     ↓
Vision AI returns license plate text
     ↓
Orion Context Broker creates violation event
     ↓
Backend matches event to user by plate
     ↓
Reset streak and update points if necessary
```

---

## Technical Implementation: License Plate Recognition  

- When a violation is detected, an **image** is sent to the **Vision AI** provided by the university.  
- The Vision AI processes the image and returns the detected **license plate number** based on a predefined prompt.  
- The backend uses this plate to match the **event** with the corresponding **user**.  
- Implementation example shown in **`vision_demo.py`**.  
