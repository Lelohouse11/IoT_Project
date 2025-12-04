# Reporting system concept and design
The system reporting part is responsible for letting users report problems they see while travelling. However, the system checks these reports from several angels to filter out any false or untrue statement.
## UI and data sending (Frontend)
Instead of typing a long message, the user just selects the right category (sometimes subcategories). This is done to make the report faster to send and to simplify statistical analysis.
### Platform: 
- PWA
### Input Method: 
- Pre-defined, multi-level category selector
- GPS coordinates and timestamps are attached automatically by the system
#### Example categories:
- Road Hazard (Object on road, Pothole, Animal)
- Traffic Incident (Accident, Congestion, Broken-down vehicle)
- Parking Violation (Illegal parking, Blocked driveway)
- Environment (Hazardous weather)
### Technical implementation 
- Data communication
    - Protocol: HTTP POST
    - Data model: JSON
- Geolocation API for precise coordinates
    - Security Requirement: Modern browsers restrict GPS access to Secure Contexts -> therefore the client must be served via HTTPS
    - For the development: 
        - Ngrok
            - disadvantage: the free version generates a random URL that changes with every restart
        - Browser override: modifying the Chrome flags
            - requires manual configuration on each devices
- Timestamp
    - Server-side
        - preferred   
        - The SQL database automatically save the date (created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        - Network connection should be stable
    - Client-side
## Architecture changes (Backend)
- New Endpoint
    - Method: POST
    - Function: handles incoming user reports, updates the database
- Storage: SQL
## Validation strategy (Hybrid validation)
The system uses two methods to check if a user report is real: automatic sensor checks and feedback from other users.
### Sensor based validation
The system compares the user's report with data from the sensor network (InfluxDB)
- Search window: accept data that fits within limits
    - Time: +- 15 minutes of the user report
    - Location: 200 meters of the reported GPS coordinates
    (these limits are only examples)
### Involving users in the verification process
Ask other users nearby to confirm the report, while we notificated them about the report - maybe just for major events, to avoid distracting users for small issues
- Feedback: Confirm/Deny
- Decision: made form counts the votes
    - If many users vote "Deny" and no sensors confirm it, the report is marked as REJECTED 
    - We also check the heatmap, if the area is very crowded - we wait for more negítive votes

