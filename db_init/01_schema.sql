-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Parking entities to simulate
CREATE TABLE IF NOT EXISTS parking_entities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255),
    lat DOUBLE,
    lng DOUBLE,
    total_spots INT,
    url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Road segments for map snapping and simulation
-- Storing individual segments for easier spatial querying/sampling
CREATE TABLE IF NOT EXISTS road_segments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lat1 DOUBLE NOT NULL,
    lng1 DOUBLE NOT NULL,
    lat2 DOUBLE NOT NULL,
    lng2 DOUBLE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Traffic entities to simulate
CREATE TABLE IF NOT EXISTS traffic_entities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255),
    lat DOUBLE,
    lng DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Driver profiles for the rewards system
-- Independent from the users table (which is for the other frontend)
CREATE TABLE IF NOT EXISTS driver_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    license_plate VARCHAR(20),
    last_traffic_violation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_parking_violation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed test driver profile
-- TODO: This will be replaced with proper user management in the future
INSERT INTO driver_profiles (username, email, password_hash, license_plate, current_points)
VALUES ('test_driver', 'test@example.com', 'hashed_password_placeholder', 'ABC-1234', 150)
ON DUPLICATE KEY UPDATE username=VALUES(username);
