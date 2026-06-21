"""Business logic for catalog, members, loans, and member requests."""

from __future__ import annotations

import datetime as dt
import sqlite3

import bcrypt

from controllers.validators import (
    ValidationError,
    copies,
    email,
    isbn,
    optional_text,
    password,
    phone,
    text,
    url,
    year,
)
from models.database import db_session

MAX_ACTIVE_BORROWS = 3
DEFAULT_BORROW_DAYS = 14
MAX_BORROW_DAYS = 60


def _audit(connection, action: str, table: str, record_id: int, description: str) -> None:
    connection.execute(
        """
        INSERT INTO audit_logs (action_type, table_name, record_id, description)
        VALUES (?, ?, ?, ?)
        """,
        (action, table, record_id, description),
    )


def _book_values(
    title_value,
    author_value,
    isbn_value,
    category_value,
    published_year,
    description_value,
    cover_image_url,
    total_copies,
):
    return (
        text(title_value, "Kitap adı", maximum=200),
        text(author_value, "Yazar", maximum=150),
        isbn(isbn_value),
        text(category_value or "Genel", "Kategori", maximum=80),
        year(published_year),
        optional_text(description_value, "Açıklama", maximum=5000),
        url(cover_image_url),
        copies(total_copies),
    )


class BookController:
    @staticmethod
    def add_book(
        title,
        author,
        isbn_value,
        category,
        published_year,
        description,
        cover_image_url,
        total_copies,
    ):
        try:
            values = _book_values(
                title,
                author,
                isbn_value,
                category,
                published_year,
                description,
                cover_image_url,
                total_copies,
            )
            with db_session() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO books
                        (title, author, isbn, category, published_year, description,
                         cover_image_url, total_copies, available_copies, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (*values, values[-1]),
                )
                _audit(
                    connection,
                    "CREATE",
                    "books",
                    cursor.lastrowid,
                    f"Kitap eklendi: {values[0]}",
                )
            return True, "Kitap başarıyla eklendi."
        except ValidationError as exc:
            return False, str(exc)
        except sqlite3.IntegrityError:
            return False, "Bu ISBN ile kayıtlı başka bir kitap var."

    @staticmethod
    def get_all_books(search_term="", limit=1000, offset=0):
        query = str(search_term or "").strip()
        try:
            safe_limit = min(max(int(limit), 1), 1000)
            safe_offset = max(int(offset), 0)
        except (TypeError, ValueError):
            safe_limit, safe_offset = 20, 0
        like_term = f"%{query}%"
        with db_session() as connection:
            return connection.execute(
                """
                SELECT id, title, author, isbn, category, published_year,
                       description, cover_image_url, total_copies, available_copies
                FROM books
                WHERE is_active = 1
                  AND (title LIKE ? OR author LIKE ? OR isbn LIKE ? OR category LIKE ?)
                ORDER BY title COLLATE NOCASE, author COLLATE NOCASE
                LIMIT ? OFFSET ?
                """,
                (like_term, like_term, like_term, like_term, safe_limit, safe_offset),
            ).fetchall()

    @staticmethod
    def get_catalog_stats():
        with db_session() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(available_copies), 0),
                       COUNT(DISTINCT category)
                FROM books WHERE is_active = 1
                """
            ).fetchone()
        return {"titles": row[0], "available": row[1], "categories": row[2]}

    @staticmethod
    def delete_book(book_id):
        try:
            with db_session(immediate=True) as connection:
                row = connection.execute(
                    """
                    SELECT title,
                           EXISTS(
                               SELECT 1 FROM borrows
                               WHERE book_id = books.id AND actual_return_date IS NULL
                           )
                    FROM books WHERE id = ? AND is_active = 1
                    """,
                    (book_id,),
                ).fetchone()
                if not row:
                    return False, "Kitap bulunamadı."
                if row[1]:
                    return False, "Ödünçte olan bir kitap arşivlenemez."
                connection.execute("UPDATE books SET is_active = 0 WHERE id = ?", (book_id,))
                _audit(connection, "ARCHIVE", "books", int(book_id), f"Kitap arşivlendi: {row[0]}")
            return True, "Kitap arşivlendi; ödünç geçmişi korundu."
        except (TypeError, ValueError):
            return False, "Geçersiz kitap numarası."

    @staticmethod
    def update_book(
        book_id,
        title,
        author,
        isbn_value,
        category,
        published_year,
        description,
        cover_image_url,
        total_copies,
    ):
        try:
            values = _book_values(
                title,
                author,
                isbn_value,
                category,
                published_year,
                description,
                cover_image_url,
                total_copies,
            )
            with db_session(immediate=True) as connection:
                current = connection.execute(
                    """
                    SELECT total_copies, available_copies, cover_image_url
                    FROM books WHERE id = ? AND is_active = 1
                    """,
                    (book_id,),
                ).fetchone()
                if not current:
                    return False, "Kitap bulunamadı."

                checked_out = current[0] - current[1]
                new_total = values[-1]
                if new_total < checked_out:
                    return False, f"En az {checked_out} kopya ödünçte; toplam sayı bunun altına indirilemez."
                new_available = new_total - checked_out
                cover = values[6] or current[2]
                cursor = connection.execute(
                    """
                    UPDATE books
                    SET title = ?, author = ?, isbn = ?, category = ?,
                        published_year = ?, description = ?, cover_image_url = ?,
                        total_copies = ?, available_copies = ?
                    WHERE id = ? AND is_active = 1
                    """,
                    (*values[:6], cover, new_total, new_available, book_id),
                )
                if cursor.rowcount == 0:
                    return False, "Kitap bulunamadı."
                _audit(connection, "UPDATE", "books", int(book_id), f"Kitap güncellendi: {values[0]}")
            return True, "Kitap başarıyla güncellendi."
        except ValidationError as exc:
            return False, str(exc)
        except (TypeError, ValueError):
            return False, "Geçersiz kitap numarası."
        except sqlite3.IntegrityError:
            return False, "Bu ISBN ile kayıtlı başka bir kitap var."


class MemberController:
    @staticmethod
    def add_member(
        name,
        member_email,
        member_phone,
        raw_password,
        *,
        approved=False,
        must_change_password=False,
    ):
        try:
            clean_name = text(name, "Ad soyad", minimum=2, maximum=100)
            normalized_email = email(member_email)
            clean_phone = phone(member_phone)
            validated_password = password(raw_password)
            password_hash = bcrypt.hashpw(validated_password.encode("utf-8"), bcrypt.gensalt()).decode(
                "utf-8"
            )
            with db_session() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO members
                        (name, email, phone, password_hash, is_approved,
                         must_change_password, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        clean_name,
                        normalized_email,
                        clean_phone,
                        password_hash,
                        int(bool(approved)),
                        int(bool(must_change_password)),
                    ),
                )
                _audit(connection, "CREATE", "members", cursor.lastrowid, f"Üye eklendi: {clean_name}")
            return True, "Üye başarıyla eklendi."
        except ValidationError as exc:
            return False, str(exc)
        except sqlite3.IntegrityError:
            return False, "Bu e-posta adresi sistemde zaten kayıtlı."

    @staticmethod
    def get_all_members(search_term=""):
        like_term = f"%{str(search_term or '').strip()}%"
        with db_session() as connection:
            return connection.execute(
                """
                SELECT id, name, email, phone, registered_date
                FROM members
                WHERE is_active = 1 AND is_approved = 1
                  AND (name LIKE ? OR email LIKE ?)
                ORDER BY name COLLATE NOCASE
                """,
                (like_term, like_term),
            ).fetchall()

    @staticmethod
    def get_pending_members():
        with db_session() as connection:
            return connection.execute(
                """
                SELECT id, name, email, phone, registered_date
                FROM members
                WHERE is_active = 1 AND is_approved = 0
                ORDER BY registered_date
                """
            ).fetchall()

    @staticmethod
    def approve_member(member_id):
        with db_session() as connection:
            cursor = connection.execute(
                "UPDATE members SET is_approved = 1 WHERE id = ? AND is_active = 1",
                (member_id,),
            )
            if cursor.rowcount == 0:
                return False, "Üye bulunamadı."
            _audit(connection, "APPROVE", "members", int(member_id), "Üyelik onaylandı.")
        return True, "Üyelik onaylandı."

    @staticmethod
    def delete_member(member_id):
        with db_session(immediate=True) as connection:
            row = connection.execute(
                "SELECT name FROM members WHERE id = ? AND is_active = 1", (member_id,)
            ).fetchone()
            if not row:
                return False, "Üye bulunamadı."
            active = connection.execute(
                """
                SELECT COUNT(*) FROM borrows
                WHERE member_id = ? AND actual_return_date IS NULL
                """,
                (member_id,),
            ).fetchone()[0]
            if active:
                return False, "Aktif ödüncü bulunan üye arşivlenemez. Önce kitapları iade alın."
            connection.execute("UPDATE members SET is_active = 0 WHERE id = ?", (member_id,))
            _audit(connection, "ARCHIVE", "members", int(member_id), f"Üye arşivlendi: {row[0]}")
        return True, "Üye arşivlendi; işlem geçmişi korundu."


class BorrowController:
    @staticmethod
    def borrow_book(book_id, member_id, days=DEFAULT_BORROW_DAYS):
        try:
            loan_days = int(days)
            if not 1 <= loan_days <= MAX_BORROW_DAYS:
                return False, f"Ödünç süresi 1-{MAX_BORROW_DAYS} gün arasında olmalıdır."
            due_date = (dt.date.today() + dt.timedelta(days=loan_days)).isoformat()

            with db_session(immediate=True) as connection:
                member = connection.execute(
                    """
                    SELECT name FROM members
                    WHERE id = ? AND is_active = 1 AND is_approved = 1
                    """,
                    (member_id,),
                ).fetchone()
                if not member:
                    return False, "Aktif ve onaylı üye bulunamadı."

                active_count = connection.execute(
                    """
                    SELECT COUNT(*) FROM borrows
                    WHERE member_id = ? AND actual_return_date IS NULL
                    """,
                    (member_id,),
                ).fetchone()[0]
                if active_count >= MAX_ACTIVE_BORROWS:
                    return False, f"Aynı anda en fazla {MAX_ACTIVE_BORROWS} kitap ödünç alınabilir."

                duplicate = connection.execute(
                    """
                    SELECT 1 FROM borrows
                    WHERE member_id = ? AND book_id = ? AND actual_return_date IS NULL
                    """,
                    (member_id, book_id),
                ).fetchone()
                if duplicate:
                    return False, "Bu kitabın aktif bir ödünç kaydı zaten var."

                book = connection.execute(
                    """
                    SELECT available_copies FROM books
                    WHERE id = ? AND is_active = 1
                    """,
                    (book_id,),
                ).fetchone()
                if not book or book[0] <= 0:
                    return False, "Kitap şu anda stokta yok."

                connection.execute(
                    """
                    INSERT INTO borrows
                        (book_id, member_id, member_name_snapshot, borrow_date, return_date)
                    VALUES (?, ?, ?, DATE('now', 'localtime'), ?)
                    """,
                    (book_id, member_id, member[0], due_date),
                )
            return True, f"Kitap ödünç alındı. Son iade tarihi: {due_date}."
        except (TypeError, ValueError):
            return False, "Geçersiz kitap, üye veya süre bilgisi."
        except sqlite3.IntegrityError as exc:
            if "BOOK_UNAVAILABLE" in str(exc):
                return False, "Kitap şu anda stokta yok."
            return False, "Ödünç işlemi veritabanı kuralları nedeniyle tamamlanamadı."

    @staticmethod
    def return_book(borrow_id):
        try:
            with db_session(immediate=True) as connection:
                cursor = connection.execute(
                    """
                    UPDATE borrows
                    SET actual_return_date = DATE('now', 'localtime')
                    WHERE id = ? AND actual_return_date IS NULL
                    """,
                    (borrow_id,),
                )
                if cursor.rowcount == 0:
                    return False, "Kayıt bulunamadı veya kitap daha önce iade edilmiş."
            return True, "Kitap iade alındı."
        except (TypeError, ValueError):
            return False, "Geçersiz ödünç numarası."

    @staticmethod
    def get_all_borrows():
        with db_session() as connection:
            return connection.execute(
                """
                SELECT br.id, b.title, br.member_name_snapshot, br.borrow_date,
                       br.return_date, br.actual_return_date, br.late_fee
                FROM borrows AS br
                JOIN books AS b ON b.id = br.book_id
                ORDER BY br.id DESC
                """
            ).fetchall()

    @staticmethod
    def get_member_borrows(member_id):
        with db_session() as connection:
            return connection.execute(
                """
                SELECT br.id, b.title, b.author, b.cover_image_url, br.borrow_date,
                       br.return_date, br.actual_return_date, br.late_fee
                FROM borrows AS br
                JOIN books AS b ON b.id = br.book_id
                WHERE br.member_id = ?
                ORDER BY br.id DESC
                """,
                (member_id,),
            ).fetchall()

    @staticmethod
    def get_active_borrowers_by_book(book_id):
        with db_session() as connection:
            return connection.execute(
                """
                SELECT member_name_snapshot, borrow_date
                FROM borrows
                WHERE book_id = ? AND actual_return_date IS NULL
                ORDER BY borrow_date
                """,
                (book_id,),
            ).fetchall()

    @staticmethod
    def get_dashboard_stats():
        with db_session() as connection:
            total_books = connection.execute("SELECT COUNT(*) FROM books WHERE is_active = 1").fetchone()[0]
            active_borrows = connection.execute(
                "SELECT COUNT(*) FROM borrows WHERE actual_return_date IS NULL"
            ).fetchone()[0]
            overdue_books = connection.execute(
                """
                SELECT COUNT(*) FROM borrows
                WHERE actual_return_date IS NULL
                  AND return_date < DATE('now', 'localtime')
                """
            ).fetchone()[0]
        return total_books, active_borrows, overdue_books

    @staticmethod
    def get_admin_overview():
        with db_session() as connection:
            row = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM books WHERE is_active = 1),
                    (SELECT COALESCE(SUM(total_copies), 0) FROM books WHERE is_active = 1),
                    (SELECT COUNT(*) FROM borrows WHERE actual_return_date IS NULL),
                    (SELECT COUNT(*) FROM borrows
                     WHERE actual_return_date IS NULL
                       AND return_date < DATE('now', 'localtime')),
                    (SELECT COUNT(*) FROM members
                     WHERE is_active = 1 AND is_approved = 1),
                    (SELECT COUNT(*) FROM members
                     WHERE is_active = 1 AND is_approved = 0),
                    (SELECT COUNT(*) FROM book_requests),
                    (SELECT COUNT(*) FROM profile_requests WHERE status = 'PENDING')
                """
            ).fetchone()
        return {
            "titles": row[0],
            "copies": row[1],
            "active_borrows": row[2],
            "overdue": row[3],
            "members": row[4],
            "pending_members": row[5],
            "book_requests": row[6],
            "profile_requests": row[7],
        }

    @staticmethod
    def get_recent_activity(limit=6):
        try:
            safe_limit = min(max(int(limit), 1), 20)
        except (TypeError, ValueError):
            safe_limit = 6
        with db_session() as connection:
            return connection.execute(
                """
                SELECT action_type, description, action_date
                FROM audit_logs
                ORDER BY id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()


class RequestController:
    @staticmethod
    def add_request(member_id, member_name, title_value, author, isbn_value, cover_url):
        try:
            clean_title = text(title_value, "Kitap adı", maximum=200)
            clean_author = optional_text(author, "Yazar", maximum=150)
            clean_isbn = isbn(isbn_value)
            clean_url = url(cover_url)
            with db_session() as connection:
                member = connection.execute(
                    "SELECT name FROM members WHERE id = ? AND is_active = 1",
                    (member_id,),
                ).fetchone()
                if not member:
                    return False, "Aktif üye bulunamadı."
                duplicate = connection.execute(
                    """
                    SELECT 1 FROM book_requests
                    WHERE member_id = ? AND (isbn = ? OR lower(title) = lower(?))
                    """,
                    (member_id, clean_isbn, clean_title),
                ).fetchone()
                if duplicate:
                    return False, "Bu kitap için daha önce istek gönderdiniz."
                connection.execute(
                    """
                    INSERT INTO book_requests
                        (member_id, member_name, title, author, isbn, cover_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (member_id, member[0], clean_title, clean_author, clean_isbn, clean_url),
                )
            return True, "Kitap isteği yöneticiye gönderildi."
        except ValidationError as exc:
            return False, str(exc)

    @staticmethod
    def get_all_requests():
        with db_session() as connection:
            return connection.execute(
                """
                SELECT id, member_id, member_name, title, author, isbn,
                       request_date, cover_url
                FROM book_requests ORDER BY id DESC
                """
            ).fetchall()

    @staticmethod
    def delete_request(request_id):
        with db_session() as connection:
            cursor = connection.execute("DELETE FROM book_requests WHERE id = ?", (request_id,))
        return cursor.rowcount > 0


class NotificationController:
    @staticmethod
    def add_notification(member_id, message):
        try:
            clean_message = text(message, "Bildirim", maximum=500)
            with db_session() as connection:
                connection.execute(
                    "INSERT INTO notifications (member_id, message) VALUES (?, ?)",
                    (member_id, clean_message),
                )
            return True
        except (ValidationError, sqlite3.IntegrityError):
            return False

    @staticmethod
    def get_unread_notifications(member_id):
        with db_session() as connection:
            return connection.execute(
                """
                SELECT id, message, created_at FROM notifications
                WHERE member_id = ? AND is_read = 0
                ORDER BY id DESC
                """,
                (member_id,),
            ).fetchall()

    @staticmethod
    def mark_as_read(notification_id, member_id=None):
        query = "UPDATE notifications SET is_read = 1 WHERE id = ?"
        params = [notification_id]
        if member_id is not None:
            query += " AND member_id = ?"
            params.append(member_id)
        with db_session() as connection:
            cursor = connection.execute(query, params)
        return cursor.rowcount > 0


class ProfileRequestController:
    @staticmethod
    def add_request(member_id, member_name, new_name, new_email):
        try:
            clean_name = text(new_name, "Ad soyad", minimum=2, maximum=100)
            clean_email = email(new_email)
            with db_session() as connection:
                member = connection.execute(
                    "SELECT name FROM members WHERE id = ? AND is_active = 1",
                    (member_id,),
                ).fetchone()
                if not member:
                    return False, "Aktif üye bulunamadı."
                if connection.execute(
                    """
                    SELECT 1 FROM profile_requests
                    WHERE member_id = ? AND status = 'PENDING'
                    """,
                    (member_id,),
                ).fetchone():
                    return False, "Zaten değerlendirme bekleyen bir profil talebiniz var."
                owner = connection.execute(
                    "SELECT id FROM members WHERE email = ? COLLATE NOCASE AND id <> ?",
                    (clean_email, member_id),
                ).fetchone()
                if owner:
                    return False, "Bu e-posta adresi başka bir hesap tarafından kullanılıyor."
                connection.execute(
                    """
                    INSERT INTO profile_requests
                        (member_id, member_name, new_name, new_email)
                    VALUES (?, ?, ?, ?)
                    """,
                    (member_id, member[0], clean_name, clean_email),
                )
            return True, "Profil güncelleme isteğiniz yöneticiye iletildi."
        except ValidationError as exc:
            return False, str(exc)

    @staticmethod
    def get_pending_requests():
        with db_session() as connection:
            return connection.execute(
                """
                SELECT id, member_id, member_name, new_name, new_email, request_date
                FROM profile_requests
                WHERE status = 'PENDING'
                ORDER BY request_date
                """
            ).fetchall()

    @staticmethod
    def approve_request(request_id, member_id, new_name, new_email):
        try:
            clean_name = text(new_name, "Ad soyad", minimum=2, maximum=100)
            clean_email = email(new_email)
            with db_session(immediate=True) as connection:
                request_row = connection.execute(
                    """
                    SELECT 1 FROM profile_requests
                    WHERE id = ? AND member_id = ? AND status = 'PENDING'
                    """,
                    (request_id, member_id),
                ).fetchone()
                if not request_row:
                    return False, "Bekleyen talep bulunamadı."
                connection.execute(
                    "UPDATE members SET name = ?, email = ? WHERE id = ? AND is_active = 1",
                    (clean_name, clean_email, member_id),
                )
                connection.execute(
                    "UPDATE profile_requests SET status = 'APPROVED' WHERE id = ?",
                    (request_id,),
                )
                _audit(connection, "UPDATE", "members", int(member_id), "Profil talebi onaylandı.")
            return True, "Profil talebi onaylandı."
        except ValidationError as exc:
            return False, str(exc)
        except sqlite3.IntegrityError:
            return False, "Bu e-posta adresi başka bir hesap tarafından kullanılıyor."

    @staticmethod
    def reject_request(request_id):
        with db_session() as connection:
            cursor = connection.execute(
                """
                UPDATE profile_requests SET status = 'REJECTED'
                WHERE id = ? AND status = 'PENDING'
                """,
                (request_id,),
            )
        return cursor.rowcount > 0
