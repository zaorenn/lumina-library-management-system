-- LibSys Kütüphane Yönetim Sistemi
-- SQLite 3.35+ için şema, indeksler ve iş kuralları.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT COLLATE NOCASE UNIQUE NOT NULL CHECK (length(trim(username)) >= 3),
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Yönetici',
    email TEXT COLLATE NOCASE UNIQUE NOT NULL DEFAULT 'admin@libsys.local'
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    author TEXT NOT NULL CHECK (length(trim(author)) > 0),
    isbn TEXT COLLATE NOCASE UNIQUE NOT NULL CHECK (length(trim(isbn)) > 0),
    category TEXT NOT NULL DEFAULT 'Genel',
    published_year INTEGER,
    description TEXT NOT NULL DEFAULT '',
    cover_image_url TEXT NOT NULL DEFAULT '',
    total_copies INTEGER NOT NULL CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL CHECK (
        available_copies >= 0 AND available_copies <= total_copies
    ),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) >= 2),
    username TEXT COLLATE NOCASE,
    email TEXT COLLATE NOCASE UNIQUE NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    is_approved INTEGER NOT NULL DEFAULT 0 CHECK (is_approved IN (0, 1)),
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
    registered_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS borrows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    member_id INTEGER,
    member_name_snapshot TEXT NOT NULL,
    borrow_date DATE NOT NULL DEFAULT CURRENT_DATE,
    return_date DATE NOT NULL,
    actual_return_date DATE,
    late_fee REAL NOT NULL DEFAULT 0 CHECK (late_fee >= 0),
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE RESTRICT,
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE SET NULL,
    CHECK (return_date >= borrow_date),
    CHECK (actual_return_date IS NULL OR actual_return_date >= borrow_date)
);

CREATE TABLE IF NOT EXISTS book_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    member_name TEXT NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    author TEXT NOT NULL DEFAULT '',
    isbn TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'Genel',
    published_year INTEGER,
    description TEXT NOT NULL DEFAULT '',
    cover_url TEXT NOT NULL DEFAULT '',
    request_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    message TEXT NOT NULL CHECK (length(trim(message)) > 0),
    is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    member_name TEXT NOT NULL,
    new_name TEXT NOT NULL,
    new_email TEXT COLLATE NOCASE NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    request_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER,
    action_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_books_catalog
    ON books (is_active, title, author);
CREATE INDEX IF NOT EXISTS idx_members_approval
    ON members (is_active, is_approved, name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_members_username_unique
    ON members (username COLLATE NOCASE)
    WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_borrows_active_member
    ON borrows (member_id, actual_return_date);
CREATE INDEX IF NOT EXISTS idx_borrows_active_book
    ON borrows (book_id, actual_return_date);
CREATE INDEX IF NOT EXISTS idx_notifications_unread
    ON notifications (member_id, is_read, created_at);
CREATE INDEX IF NOT EXISTS idx_book_requests_member
    ON book_requests (member_id, isbn, request_date);
CREATE INDEX IF NOT EXISTS idx_profile_requests_status
    ON profile_requests (status, request_date);

-- init_db her çalıştığında tetikleyicilerin güncel tanımını uygular.
DROP TRIGGER IF EXISTS before_borrow_insert;
DROP TRIGGER IF EXISTS after_borrow_insert;
DROP TRIGGER IF EXISTS after_borrow_update_return;

CREATE TRIGGER before_borrow_insert
BEFORE INSERT ON borrows
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM books
            WHERE id = NEW.book_id AND is_active = 1 AND available_copies > 0
        )
        THEN RAISE(ABORT, 'BOOK_UNAVAILABLE')
    END;
END;

CREATE TRIGGER after_borrow_insert
AFTER INSERT ON borrows
BEGIN
    UPDATE books
    SET available_copies = available_copies - 1
    WHERE id = NEW.book_id;

    INSERT INTO audit_logs
        (action_type, table_name, record_id, action_date, description)
    VALUES
        ('BORROW', 'borrows', NEW.id, datetime('now', 'localtime'),
         'Kitap ödünç verildi. Üye ID: ' || COALESCE(NEW.member_id, 'silinmiş'));
END;

CREATE TRIGGER after_borrow_update_return
AFTER UPDATE OF actual_return_date ON borrows
WHEN NEW.actual_return_date IS NOT NULL AND OLD.actual_return_date IS NULL
BEGIN
    UPDATE borrows
    SET late_fee = MAX(
        0,
        CAST(julianday(NEW.actual_return_date) - julianday(OLD.return_date) AS INTEGER)
    ) * 5.0
    WHERE id = NEW.id;

    UPDATE books
    SET available_copies = MIN(total_copies, available_copies + 1)
    WHERE id = NEW.book_id;

    INSERT INTO audit_logs
        (action_type, table_name, record_id, action_date, description)
    VALUES
        ('RETURN', 'borrows', NEW.id, datetime('now', 'localtime'), 'Kitap iade edildi.');
END;
