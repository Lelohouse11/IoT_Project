-- Camera device initialization for Vrachnaiika, Patras region
-- Two cameras monitoring different road segments in the area

-- Camera 1: Main road intersection camera (Vrachnaiika center)
-- Location: ~38.2710°N, 21.7820°E
-- Monitors: Traffic flow and parking occupancy
INSERT INTO camera_devices (
    camera_id, 
    location_lat, 
    location_lng, 
    road_segment_id,
    traffic_flow_entity_id,
    onstreet_parking_entity_id,
    status
) VALUES (
    'CAM-VRACH-01',
    38.271000,
    21.782000,
    'SEG-VRACH-01',
    'urn:ngsi-ld:TrafficFlowObserved:VRACH-01',
    'urn:ngsi-ld:OnStreetParking:P-095',
    'active'
) ON DUPLICATE KEY UPDATE camera_id=VALUES(camera_id);

-- Camera 2: Red light violation monitoring camera (Vrachnaiika south)
-- Location: ~38.2685°N, 21.7795°E
-- Note: Only monitors red light violations, no traffic or parking entities
INSERT INTO camera_devices (
    camera_id, 
    location_lat, 
    location_lng, 
    road_segment_id,
    traffic_flow_entity_id,
    onstreet_parking_entity_id,
    status
) VALUES (
    'CAM-VRACH-02',
    38.268500,
    21.779500,
    'SEG-VRACH-02',
    NULL,
    NULL,
    'active'
) ON DUPLICATE KEY UPDATE camera_id=VALUES(camera_id);
