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
VALUES ('test_driver', 'test@example.com', 'hashed_password_placeholder', 'ABC-1234', 1100)
ON DUPLICATE KEY UPDATE username=VALUES(username);

-- Milestone awards tracking table
-- Tracks which milestones have been awarded to prevent double-awarding
CREATE TABLE IF NOT EXISTS milestone_awards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    driver_id INT NOT NULL,
    streak_type ENUM('traffic', 'parking') NOT NULL,
    milestone_days INT NOT NULL,
    points_awarded INT NOT NULL,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES driver_profiles(id) ON DELETE CASCADE,
    UNIQUE KEY unique_milestone (driver_id, streak_type, milestone_days)
);

-- Rewards catalog table
-- Stores available rewards that drivers can redeem with their points
CREATE TABLE IF NOT EXISTS rewards_catalog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    points_cost INT NOT NULL,
    category VARCHAR(50),
    available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed rewards catalog with predefined rewards
INSERT INTO rewards_catalog (name, description, points_cost, category, available)
VALUES 
    ('Bus Ticket', 'Single ride bus ticket valid for 90 minutes', 150, 'transport', TRUE),
    ('CityBike 24h Pass', '24-hour unlimited access to city bike sharing', 300, 'transport', TRUE),
    ('Morning Espresso', 'Free espresso at participating cafes', 450, 'food', TRUE),
    ('Groceries Discount', '10% discount voucher at local supermarkets', 600, 'shopping', TRUE)
ON DUPLICATE KEY UPDATE name=VALUES(name);
