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
