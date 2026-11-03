-- PostgreSQL Database Schema for Real-Time AI Voice Agent (Restaurant Reservations)

CREATE TABLE IF NOT EXISTS restaurant_tables (
    id SERIAL PRIMARY KEY,
    table_number VARCHAR(10) UNIQUE NOT NULL,
    capacity INT NOT NULL,
    min_capacity INT NOT NULL DEFAULT 1,
    seating_area VARCHAR(50) NOT NULL DEFAULT 'indoor', -- 'indoor', 'patio', 'bar', 'private_room'
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    confirmation_code VARCHAR(20) UNIQUE NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(30) NOT NULL,
    party_size INT NOT NULL,
    reservation_date DATE NOT NULL,
    reservation_time TIME NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 90,
    table_id INT REFERENCES restaurant_tables(id) ON DELETE SET NULL,
    dietary_requirements TEXT,
    allergy_level VARCHAR(20) DEFAULT 'NONE', -- 'NONE', 'MILD', 'MODERATE', 'SEVERE_ANAPHYLAXIS'
    allergen_flags VARCHAR(255),               -- e.g. 'peanuts,shellfish,gluten'
    special_requests TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED', -- 'CONFIRMED', 'CANCELLED', 'COMPLETED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    ingredients TEXT NOT NULL,
    allergens VARCHAR(255), -- Comma-separated allergens or 'none'
    is_gluten_free BOOLEAN NOT NULL DEFAULT FALSE,
    is_vegan BOOLEAN NOT NULL DEFAULT FALSE,
    is_vegetarian BOOLEAN NOT NULL DEFAULT FALSE,
    is_nut_free BOOLEAN NOT NULL DEFAULT TRUE,
    price NUMERIC(8, 2) NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS safety_audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    raw_text_preview TEXT,
    sanitized_text TEXT,
    risk_level VARCHAR(20) NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    action_taken VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Tables
INSERT INTO restaurant_tables (table_number, capacity, min_capacity, seating_area) VALUES
('T-01', 2, 1, 'indoor'),
('T-02', 2, 1, 'indoor'),
('T-03', 4, 2, 'indoor'),
('T-04', 4, 2, 'indoor'),
('T-05', 6, 3, 'indoor'),
('T-06', 8, 4, 'indoor'),
('P-01', 2, 1, 'patio'),
('P-02', 4, 2, 'patio'),
('P-03', 6, 3, 'patio'),
('PR-01', 12, 6, 'private_room')
ON CONFLICT (table_number) DO NOTHING;

-- Seed Menu Items with explicit allergen tags & safety cross-checks
INSERT INTO menu_items (name, category, description, ingredients, allergens, is_gluten_free, is_vegan, is_vegetarian, is_nut_free, price) VALUES
('Wild Mushroom Risotto', 'Main', 'Creamy Arborio rice with wild forest mushrooms and truffle oil', 'Arborio rice, wild mushrooms, vegetable broth, parmesan, truffle oil, garlic', 'dairy', TRUE, FALSE, TRUE, TRUE, 26.50),
('Pan-Seared Atlantic Salmon', 'Main', 'Fresh Atlantic salmon fillet served with asparagus and lemon-herb butter', 'Atlantic salmon, asparagus, butter, lemon, olive oil, sea salt', 'fish,dairy', TRUE, FALSE, FALSE, TRUE, 32.00),
('Thai Coconut Curry (Spicy)', 'Main', 'Aromatic red coconut curry with crushed roasted peanuts and jasmine rice', 'Coconut milk, red curry paste, bell peppers, tofu, crushed peanuts, peanut oil, cilantro', 'peanuts,soy', TRUE, TRUE, TRUE, FALSE, 22.00),
('Classic Caesar Salad', 'Appetizer', 'Crisp romaine lettuce, croutons, parmesan, house-made anchovy dressing', 'Romaine lettuce, wheat croutons, parmesan, anchovy paste, eggs, Dijon mustard', 'gluten,fish,dairy,eggs', FALSE, FALSE, FALSE, TRUE, 14.50),
('Heirloom Tomato Bruschetta', 'Appetizer', 'Grilled artisan sourdough topped with ripe heirloom tomatoes, basil, and garlic', 'Artisan sourdough (wheat), heirloom tomatoes, basil, garlic, extra virgin olive oil', 'gluten', FALSE, TRUE, TRUE, TRUE, 12.00),
('Crispy Calamari Fritti', 'Appetizer', 'Lightly breaded squid rings with roasted garlic aioli and lemon wedges', 'Squid, wheat flour batter, garlic aioli (eggs), lemon', 'shellfish,gluten,eggs', FALSE, FALSE, FALSE, TRUE, 16.50),
('Decadent Chocolate Lava Cake', 'Dessert', 'Warm molten chocolate cake with vanilla bean gelato and almond praline garnish', 'Dark chocolate, butter, sugar, eggs, wheat flour, whole milk, almond praline', 'dairy,eggs,gluten,tree_nuts', FALSE, FALSE, TRUE, FALSE, 11.00),
('Mango Passionfruit Sorbet', 'Dessert', 'Refreshing artisanal sorbet crafted with tropical Alfonso mangoes and passionfruit', 'Alfonso mango puree, passionfruit juice, organic cane sugar, spring water', 'none', TRUE, TRUE, TRUE, TRUE, 9.50)
ON CONFLICT DO NOTHING;

