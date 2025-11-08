CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USER TABLE
-- Stores player account information
-- ============================================
CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    hash_pass VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_name ON "user"(name);

-- ============================================
-- BUILDING TABLE
-- Player-owned structures on hexagonal tiles
-- Uses H3 index as natural primary key
-- ============================================
CREATE TABLE building (
    h3_index VARCHAR(20) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    biome_type biome_type NOT NULL,
    resource_type resource_type NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    last_claim_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_building_level CHECK (level >= 1 AND level <= 10)
);

CREATE INDEX idx_building_user_id ON building(user_id);
CREATE INDEX idx_building_resource_type ON building(resource_type);
CREATE INDEX idx_building_biome_type ON building(biome_type);
CREATE INDEX idx_building_last_claim_at ON building(last_claim_at);

-- ============================================
-- RESOURCE_TYPE ENUM
-- Available resource types in the game
-- ============================================
CREATE TYPE resource_type AS ENUM (
    'WOOD',   -- Lumber harvested from forests
    'STONE',  -- Stone mined from quarries
    'WHEAT'   -- Grain grown in farmlands
);

-- ============================================
-- BIOME_TYPE ENUM
-- Available biome types in the game
-- ============================================
CREATE TYPE biome_type AS ENUM (
    'TREE_COVER',           -- Tree cover (10)
    'SHRUBLAND',            -- Shrubland (20)
    'GRASSLAND',            -- Grassland (30)
    'CROPLAND',             -- Cropland (40)
    'WETLAND',              -- Herbaceous wetland (50)
    'MANGROVES',            -- Mangroves (60)
    'MOSS_LICHEN',          -- Moss and lichen (70)
    'BARE',                 -- Bare/sparse vegetation (80)
    'BUILT_UP',             -- Built-up (90)
    'WATER',                -- Permanent water bodies (100)
    'SNOW_ICE',             -- Snow and ice (110)
    'UNCLASSIFIABLE'        -- Unclassifiable (254)
);

-- ============================================
-- INVENTORY_ITEM TABLE
-- User inventory (buildings generate resources on claim)
-- ============================================
CREATE TABLE inventory_item (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    resource_type resource_type NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inventory_quantity CHECK (quantity >= 0),
    CONSTRAINT unique_user_resource UNIQUE (user_id, resource_type)
);

CREATE INDEX idx_inventory_user_id ON inventory_item(user_id);
CREATE INDEX idx_inventory_resource_type ON inventory_item(resource_type);

-- ============================================
-- MARKET_ORDER TABLE
-- Buy and Sell orders on the market
-- ============================================
CREATE TABLE market_order (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    order_type VARCHAR(10) NOT NULL CHECK (order_type IN ('BUY','SELL')),
    resource_type resource_type NOT NULL,
    amount INTEGER NOT NULL CHECK (amount > 0),
    total_price INTEGER NOT NULL CHECK (total_price >= 0),
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_market_order_user_id ON market_order(user_id);
CREATE INDEX idx_market_order_order_type ON market_order(order_type);
CREATE INDEX idx_market_order_resource_type ON market_order(resource_type);
CREATE INDEX idx_market_order_status ON market_order(status);

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

CREATE TRIGGER update_building_updated_at BEFORE UPDATE ON building
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_item_updated_at BEFORE UPDATE ON inventory_item
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_market_order_updated_at BEFORE UPDATE ON market_order
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS
-- Useful queries for common operations
-- ============================================

-- View: User inventory with resource details
CREATE VIEW v_user_inventory AS
SELECT 
    i.id,
    i.user_id,
    u.name AS user_name,
    i.resource_type,
    i.quantity,
    i.updated_at
FROM inventory_item i
JOIN "user" u ON i.user_id = u.id;

-- View: Building details with owner information
CREATE VIEW v_building_details AS
SELECT 
    b.h3_index,
    b.name AS building_name,
    b.resource_type,
    b.biome_type,
    b.level,
    b.user_id,
    u.name AS owner_name,
    b.created_at,
    b.updated_at
FROM building b
JOIN "user" u ON b.user_id = u.id;

-- ============================================
-- COMMENTS
-- Add table and column descriptions
-- ============================================
COMMENT ON TABLE "user" IS 'Player account information';
COMMENT ON COLUMN "user".hash_pass IS 'Bcrypt hashed password (with salt)';

COMMENT ON TABLE building IS 'Player-owned structures on hexagonal map tiles';
COMMENT ON COLUMN building.h3_index IS 'H3 geospatial index - natural primary key';
COMMENT ON COLUMN building.user_id IS 'References user who owns the building';
COMMENT ON COLUMN building.biome_type IS 'Biome classification (e.g., Forest, Plains, Urban)';
COMMENT ON COLUMN building.resource_type IS 'Resource type produced by this building (WOOD, STONE, WHEAT)';
COMMENT ON COLUMN building.last_claim_at IS 'Timestamp of last resource claim - used to calculate accumulated resources';

COMMENT ON TYPE resource_type IS 'Available resource types: WOOD (lumber from forests), STONE (mined from quarries), WHEAT (grown in farmlands)';

COMMENT ON TABLE inventory_item IS 'User inventory - buildings generate resources on claim based on last_claim_at timestamp';
COMMENT ON COLUMN inventory_item.user_id IS 'References user who owns the resources';
COMMENT ON COLUMN inventory_item.resource_type IS 'Type of resource stored (ENUM: WOOD, STONE, WHEAT)';

COMMENT ON TABLE market_order IS 'Market buy/sell orders';
COMMENT ON COLUMN market_order.order_type IS 'Type of order: BUY wants to acquire resource; SELL offers to provide resource';
COMMENT ON COLUMN market_order.resource_type IS 'Resource being traded (cannot be MONEY)';
COMMENT ON COLUMN market_order.amount IS 'Number of units of resource to buy/sell';
COMMENT ON COLUMN market_order.total_price IS 'Total price for the entire order denominated in MONEY';
COMMENT ON COLUMN market_order.status IS 'OPEN=active, CLOSED=filled/completed';
