-- Seed data for Library Book Return System

-- Insert default library
INSERT INTO library (library_name, location) VALUES
('Main Library', 'Main Campus, Building A'),
('Engineering Library', 'Engineering Building, 2nd Floor')
ON CONFLICT DO NOTHING;

-- Insert default return boxes (linked to ESP32 devices)
INSERT INTO return_box (return_box_name, location, library_id) VALUES
('Return Box 01', 'Main Library Entrance', 1),
('Return Box 02', 'Engineering Library Entrance', 2)
ON CONFLICT DO NOTHING;

-- Insert sample books
INSERT INTO book (isbn, title, author, publisher, publication_year, category) VALUES
('978-0134685991', 'Effective Java', 'Joshua Bloch', 'Addison-Wesley', 2018, 'Computer Science'),
('978-0596007126', 'Head First Design Patterns', 'Eric Freeman', 'O''Reilly Media', 2004, 'Computer Science'),
('978-0132350884', 'Clean Code', 'Robert C. Martin', 'Prentice Hall', 2008, 'Computer Science'),
('978-0201633610', 'Design Patterns', 'Gang of Four', 'Addison-Wesley', 1994, 'Computer Science'),
('978-0135957059', 'The Pragmatic Programmer', 'Andrew Hunt', 'Addison-Wesley', 2019, 'Computer Science')
ON CONFLICT (isbn) DO NOTHING;

-- Insert sample book copies with RFID EPCs (example EPCs - replace with actual tags)
INSERT INTO book_copy (book_id, copy_number, book_epc, status, condition, library_id) VALUES
(1, 1, 'E280691500004022A7D4C001', 'available', 'good', 1),
(1, 2, 'E280691500004022A7D4C002', 'available', 'good', 1),
(2, 1, 'E280691500004022A7D4C003', 'available', 'good', 1),
(2, 2, 'E280691500004022A7D4C004', 'available', 'fair', 1),
(3, 1, 'E280691500004022A7D4C005', 'available', 'good', 1),
(4, 1, 'E280691500004022A7D4C006', 'available', 'good', 2),
(5, 1, 'E280691500004022A7D4C007', 'available', 'good', 1)
ON CONFLICT (book_epc) DO NOTHING;

-- Insert test users (password: "password123" - plain text)
INSERT INTO "user" (user_fname, user_lname, user_email, user_password_hash, phone_number, user_role) VALUES
('John', 'Doe', 'john.doe@university.edu', 'password123', '123-456-7890', 'student'),
('Jane', 'Smith', 'jane.smith@university.edu', 'password123', '123-456-7891', 'student'),
('Admin', 'Librarian', 'admin@library.edu', 'password123', '123-456-7892', 'librarian')
ON CONFLICT (user_email) DO NOTHING;

-- Insert sample active loans
INSERT INTO loan (user_id, copy_id, checkout_date, due_date, status) VALUES
(1, 1, CURRENT_TIMESTAMP - INTERVAL '5 days', CURRENT_TIMESTAMP + INTERVAL '2 days', 'active'),
(1, 3, CURRENT_TIMESTAMP - INTERVAL '10 days', CURRENT_TIMESTAMP - INTERVAL '3 days', 'overdue'),
(2, 5, CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP + INTERVAL '5 days', 'active')
ON CONFLICT DO NOTHING;
