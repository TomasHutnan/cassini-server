CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USER TABLE
-- Stores player account information
-- ============================================
CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    hash_pass VARCHAR(255) NOT NULL,
    hash_salt VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_name ON "user"(name);

-- ============================================
-- CHARACTER TABLE
-- Each user has one online and one offline character
-- ============================================
CREATE TABLE character (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    is_pvp BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_character_type UNIQUE (user_id, is_pvp)
);

CREATE INDEX idx_character_user_id ON character(user_id);
CREATE INDEX idx_character_is_pvp ON character(is_pvp);

-- ============================================
-- BUILDING TABLE
-- Player-owned structures on hexagonal tiles
-- Uses H3 index as natural primary key
-- ============================================
CREATE TABLE building (
    h3_index VARCHAR(20) PRIMARY KEY,
    player_id UUID NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    biome_type VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_building_level CHECK (level >= 1 AND level <= 10)
);

CREATE INDEX idx_building_player_id ON building(player_id);
CREATE INDEX idx_building_type ON building(type);
CREATE INDEX idx_building_biome_type ON building(biome_type);

-- ============================================
-- RESOURCE_TYPE TABLE
-- Enumeration of available resource types
-- ============================================
CREATE TABLE resource_type (
    type_name VARCHAR(50) PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default resource types
INSERT INTO resource_type (type_name, description) VALUES
    ('WOOD', 'Lumber harvested from forests'),
    ('STONE', 'Stone mined from quarries'),
    ('WHEAT', 'Grain grown in farmlands');

-- ============================================
-- INVENTORY_ITEM TABLE
-- Polymorphic inventory for characters and buildings
-- ============================================
CREATE TABLE inventory_item (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    character_id UUID REFERENCES character(id) ON DELETE CASCADE,
    settlement_h3_index VARCHAR(15) REFERENCES settlement(h3_index) ON DELETE CASCADE,
    resource_type_name VARCHAR(50) NOT NULL REFERENCES resource_type(type_name) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inventory_owner CHECK (
        (character_id IS NOT NULL AND settlement_h3_index IS NULL)
        OR (character_id IS NULL AND settlement_h3_index IS NOT NULL)
    ),
    CONSTRAINT chk_inventory_quantity CHECK (quantity >= 0),
    CONSTRAINT unique_owner_resource UNIQUE (character_id, settlement_h3_index, resource_type_name)
);

CREATE INDEX idx_inventory_character_id ON inventory_item(character_id);
CREATE INDEX idx_inventory_settlement_h3_index ON inventory_item(settlement_h3_index);
CREATE INDEX idx_inventory_resource_type ON inventory_item(resource_type_name);

-- ============================================
-- TRIGGERS
-- Auto-update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_updated_at BEFORE UPDATE ON "user"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_character_updated_at BEFORE UPDATE ON character
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_building_updated_at BEFORE UPDATE ON building
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_item_updated_at BEFORE UPDATE ON inventory_item
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS
-- Useful queries for common operations
-- ============================================

-- View: Character inventory with resource details
CREATE VIEW v_character_inventory AS
SELECT 
    i.id,
    i.owner_id AS character_id,
    c.user_id,
    u.name AS user_name,
    i.resource_type_name,
    rt.description AS resource_description,
    i.quantity,
    i.updated_at
FROM inventory_item i
JOIN character c ON i.owner_id = c.id
JOIN "user" u ON c.user_id = u.id
JOIN resource_type rt ON i.resource_type_name = rt.type_name
WHERE i.owner_type = 'CHARACTER';

-- View: Building inventory with resource details
CREATE VIEW v_building_inventory AS
SELECT 
    i.id,
    i.owner_id AS building_h3_index,
    s.name AS building_name,
    s.player_id,
    i.resource_type_name,
    rt.description AS resource_description,
    i.quantity,
    i.updated_at
FROM inventory_item i
JOIN building s ON i.owner_id::text = s.h3_index
JOIN resource_type rt ON i.resource_type_name = rt.type_name
WHERE i.owner_type = 'BUILDING';

-- View: Building details with owner information
CREATE VIEW v_building_details AS
SELECT 
    s.h3_index,
    s.name AS building_name,
    s.type AS building_type,
    s.biome_type,
    s.level,
    c.id AS character_id,
    c.is_pvp,
    u.id AS user_id,
    u.name AS owner_name,
    s.created_at,
    s.updated_at
FROM building s
JOIN character c ON s.player_id = c.id
JOIN "user" u ON c.user_id = u.id;

-- ============================================
-- COMMENTS
-- Add table and column descriptions
-- ============================================
COMMENT ON TABLE "user" IS 'Player account information';
COMMENT ON COLUMN "user".hash_pass IS 'Bcrypt hashed password';
COMMENT ON COLUMN "user".hash_salt IS 'Password salt for additional security';

COMMENT ON TABLE character IS 'Game characters - each user has one PVP (online) and one PVE (offline) character';
COMMENT ON COLUMN character.is_pvp IS 'true = PVP/online character, false = PVE/offline character';

COMMENT ON TABLE building IS 'Player-owned structures on hexagonal map tiles';
COMMENT ON COLUMN building.h3_index IS 'H3 geospatial index - natural primary key';
COMMENT ON COLUMN building.biome_type IS 'Biome classification (e.g., Forest, Plains, Urban)';
COMMENT ON COLUMN building.type IS 'Building function (e.g., Farm, Mine, Lumberyard)';

COMMENT ON TABLE resource_type IS 'Enumeration of all available resource types in the game';

COMMENT ON TABLE inventory_item IS 'Polymorphic inventory for both characters and buildings';
COMMENT ON COLUMN inventory_item.owner_type IS 'Must be either CHARACTER or BUILDING';
COMMENT ON COLUMN inventory_item.owner_id IS 'References either character.id or building.h3_index';
