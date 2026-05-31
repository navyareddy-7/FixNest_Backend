-- 1. Create Roles Table
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE
);

-- 2. Create Hostels Table (without admin_id FK first to avoid circular dependency)
CREATE TABLE hostels (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    location VARCHAR NOT NULL,
    admin_id INTEGER,
    total_rooms INTEGER NOT NULL DEFAULT 0,
    total_students INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create Rooms Table
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    room_number VARCHAR NOT NULL,
    hostel_id INTEGER NOT NULL REFERENCES hostels(id) ON DELETE CASCADE,
    capacity INTEGER NOT NULL DEFAULT 4,
    occupied INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'available'
);

-- 4. Create Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    phone_number VARCHAR,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    hostel_id INTEGER REFERENCES hostels(id),
    room_id INTEGER REFERENCES rooms(id),
    status VARCHAR NOT NULL DEFAULT 'active',
    push_token VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add the admin_id Foreign Key to hostels now that users table exists
ALTER TABLE hostels
    ADD CONSTRAINT fk_hostel_admin 
    FOREIGN KEY (admin_id) 
    REFERENCES users(id) ON DELETE SET NULL;

-- 5. Create Notices Table
CREATE TABLE notices (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    hostel_id INTEGER REFERENCES hostels(id) ON DELETE CASCADE,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Create Complaints Table
CREATE TABLE complaints (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    hostel_id INTEGER NOT NULL REFERENCES hostels(id) ON DELETE CASCADE,
    status VARCHAR NOT NULL DEFAULT 'pending',
    severity VARCHAR NOT NULL DEFAULT 'medium',
    image_url VARCHAR,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    worker_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Create Comments Table
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    text VARCHAR NOT NULL,
    is_system_action BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_hostels_name ON hostels(name);
CREATE INDEX idx_rooms_room_number ON rooms(room_number);

-- Insert Default Roles
INSERT INTO roles (name) VALUES 
    ('super_admin'), 
    ('hostel_admin'), 
    ('worker'), 
    ('student');
