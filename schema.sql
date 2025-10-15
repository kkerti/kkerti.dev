-- Temperature readings table
CREATE TABLE IF NOT EXISTS temperature_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    temperature REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id TEXT DEFAULT 'pico_xxx',
    metadata TEXT -- JSON field for additional data
);

-- Index for faster queries by timestamp
CREATE INDEX IF NOT EXISTS idx_temperature_timestamp ON temperature_readings(timestamp);

-- Insert some sample data
-- INSERT INTO temperature_readings (temperature, timestamp, device_id) VALUES 
--     (23.5, datetime('now', '-60 minutes'), 'lab'),
--     (24.1, datetime('now', '-50 minutes'), 'lab'),
--     (25.3, datetime('now', '-40 minutes'), 'lab'),
--     (26.8, datetime('now', '-30 minutes'), 'lab'),
--     (25.9, datetime('now', '-20 minutes'), 'lab'),
--     (24.2, datetime('now', '-10 minutes'), 'lab'),
--     (23.8, datetime('now'), 'lab');