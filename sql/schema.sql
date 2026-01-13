-- Library Book Return System Database Schema
-- PostgreSQL 15

-- Enable UUID extension (if needed)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create USER table (reuse from original, but can extend for library roles)
CREATE TABLE IF NOT EXISTS "user" (
    user_id SERIAL PRIMARY KEY,
    user_fname VARCHAR(100) NOT NULL,
    user_lname VARCHAR(100) NOT NULL,
    user_email VARCHAR(255) UNIQUE NOT NULL,
    user_password_hash VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    payment_status VARCHAR(50) DEFAULT 'active',
    user_role VARCHAR(50) DEFAULT 'student',  -- student, librarian, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create LIBRARY table (library locations)
CREATE TABLE library (
    library_id SERIAL PRIMARY KEY,
    library_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create RETURN_BOX table (physical return boxes - reusing fridge concept)
CREATE TABLE return_box (
    return_box_id SERIAL PRIMARY KEY,
    return_box_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    library_id INTEGER REFERENCES library(library_id) ON DELETE SET NULL,
    fridge_id INTEGER,  -- Reference to ESP32 device (can reuse fridge table or create device table)
    status VARCHAR(50) DEFAULT 'active',  -- active, maintenance, inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create BOOK table (catalog of books)
CREATE TABLE book (
    book_id SERIAL PRIMARY KEY,
    isbn VARCHAR(20) UNIQUE,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    publisher VARCHAR(255),
    publication_year INTEGER,
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create BOOK_COPY table (individual copies of books with RFID tags)
CREATE TABLE book_copy (
    copy_id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES book(book_id) ON DELETE CASCADE,
    copy_number INTEGER NOT NULL,  -- Copy 1, 2, 3 of same book
    book_epc VARCHAR(100) UNIQUE NOT NULL,  -- RFID tag (unique per copy)
    status VARCHAR(50) DEFAULT 'available',  -- available, checked_out, returned, damaged, lost
    condition VARCHAR(50) DEFAULT 'good',  -- good, fair, poor, damaged
    library_id INTEGER REFERENCES library(library_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_book_copy UNIQUE (book_id, copy_number)
);

-- Create index on book_epc for fast RFID lookups
CREATE INDEX idx_book_copy_epc ON book_copy(book_epc);
CREATE INDEX idx_book_copy_status ON book_copy(status);
CREATE INDEX idx_book_copy_book_id ON book_copy(book_id);

-- Create LOAN table (borrowing records)
CREATE TABLE loan (
    loan_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
    copy_id INTEGER NOT NULL REFERENCES book_copy(copy_id) ON DELETE RESTRICT,
    checkout_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP NOT NULL,
    return_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',  -- active, returned, overdue, lost
    fine_amount DECIMAL(10, 2) DEFAULT 0.00,
    fine_paid BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_loan_status CHECK (status IN ('active', 'returned', 'overdue', 'lost'))
);

-- Create indexes for loan queries
CREATE INDEX idx_loan_user_id ON loan(user_id);
CREATE INDEX idx_loan_copy_id ON loan(copy_id);
CREATE INDEX idx_loan_status ON loan(status);
CREATE INDEX idx_loan_due_date ON loan(due_date);

-- Create RETURN_TRANSACTION table (return sessions)
CREATE TABLE return_transaction (
    return_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
    return_box_id INTEGER REFERENCES return_box(return_box_id) ON DELETE SET NULL,
    return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processed, completed, cancelled
    processed_by INTEGER REFERENCES "user"(user_id) ON DELETE SET NULL,  -- Library staff
    processed_at TIMESTAMP,
    total_fines DECIMAL(10, 2) DEFAULT 0.00,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_return_status CHECK (status IN ('pending', 'processed', 'completed', 'cancelled'))
);

-- Create index on return_transaction
CREATE INDEX idx_return_transaction_user_id ON return_transaction(user_id);
CREATE INDEX idx_return_transaction_status ON return_transaction(status);
CREATE INDEX idx_return_transaction_return_box_id ON return_transaction(return_box_id);

-- Create RETURN_ITEM table (books in a return transaction)
CREATE TABLE return_item (
    return_item_id SERIAL PRIMARY KEY,
    return_id INTEGER NOT NULL REFERENCES return_transaction(return_id) ON DELETE CASCADE,
    copy_id INTEGER NOT NULL REFERENCES book_copy(copy_id) ON DELETE RESTRICT,
    loan_id INTEGER REFERENCES loan(loan_id) ON DELETE SET NULL,  -- Link to original loan
    condition_on_return VARCHAR(50) DEFAULT 'good',  -- good, fair, poor, damaged
    fine_amount DECIMAL(10, 2) DEFAULT 0.00,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_return_item UNIQUE (return_id, copy_id)
);

-- Create index on return_item
CREATE INDEX idx_return_item_return_id ON return_item(return_id);
CREATE INDEX idx_return_item_copy_id ON return_item(copy_id);
CREATE INDEX idx_return_item_loan_id ON return_item(loan_id);

-- Create FRIDGE table (reuse for ESP32 devices/return boxes)
CREATE TABLE fridge (
    fridge_id SERIAL PRIMARY KEY,
    fridge_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_user_updated_at BEFORE UPDATE ON "user"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_library_updated_at BEFORE UPDATE ON library
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_return_box_updated_at BEFORE UPDATE ON return_box
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_book_updated_at BEFORE UPDATE ON book
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_book_copy_updated_at BEFORE UPDATE ON book_copy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_loan_updated_at BEFORE UPDATE ON loan
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_return_transaction_updated_at BEFORE UPDATE ON return_transaction
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate fine based on due date
CREATE OR REPLACE FUNCTION calculate_fine(due_date TIMESTAMP, return_date TIMESTAMP, daily_fine_rate DECIMAL DEFAULT 0.50)
RETURNS DECIMAL AS $$
DECLARE
    days_overdue INTEGER;
    calculated_fine DECIMAL;
BEGIN
    IF return_date IS NULL OR return_date <= due_date THEN
        RETURN 0.00;
    END IF;
    
    days_overdue := EXTRACT(DAY FROM (return_date - due_date))::INTEGER;
    calculated_fine := days_overdue * daily_fine_rate;
    
    -- Cap maximum fine (e.g., $10.00)
    IF calculated_fine > 10.00 THEN
        calculated_fine := 10.00;
    END IF;
    
    RETURN calculated_fine;
END;
$$ language 'plpgsql';
