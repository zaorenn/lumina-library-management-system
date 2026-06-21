"""Integration tests for LibSys SQLite-backed business rules."""

from __future__ import annotations

import sqlite3

import pytest

import models.database
from controllers.auth import AuthController
from controllers.library import (
    MAX_ACTIVE_BORROWS,
    BookController,
    BorrowController,
    MemberController,
    NotificationController,
    ProfileRequestController,
    RequestController,
)
from controllers.validators import first_valid_isbn, isbn13_from_body


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    database_path = tmp_path / "libsys-test.db"
    monkeypatch.setattr(models.database, "DB_PATH", database_path)
    monkeypatch.setattr(models.database, "DEFAULT_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(models.database, "DEFAULT_ADMIN_PASSWORD", "admin123")
    models.database.init_db(seed_catalog=False)
    yield database_path


def valid_isbn(number=1):
    return isbn13_from_body(f"978625{number:06d}")


def test_external_isbn_selection_skips_invalid_values():
    assert first_valid_isbn(["invalid", "12345", "9780451524935"]) == "9780451524935"
    assert first_valid_isbn(None) is None


def add_book(number=1, copies=3, title=None):
    result = BookController.add_book(
        title or f"Test Kitabı {number}",
        "Test Yazarı",
        valid_isbn(number),
        "Roman",
        2024,
        "Test açıklaması",
        "https://example.com/cover.jpg",
        copies,
    )
    assert result[0], result[1]
    return BookController.get_all_books(valid_isbn(number))[0][0]


def add_member(number=1, *, approved=True):
    result = MemberController.add_member(
        f"Üye {number}",
        f"uye{number}@example.com",
        "+90 555 111 22 33",
        "Guclu123!",
        approved=approved,
    )
    assert result[0], result[1]
    rows = MemberController.get_all_members() if approved else MemberController.get_pending_members()
    return next(row[0] for row in rows if row[2] == f"uye{number}@example.com")


def test_database_enables_foreign_keys_and_has_current_schema(isolated_database):
    connection = models.database.get_connection()
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        triggers = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        }
        assert {"before_borrow_insert", "after_borrow_insert", "after_borrow_update_return"} <= triggers
    finally:
        connection.close()


def test_default_admin_login_uses_hashed_password():
    success, admin = AuthController.login_admin("admin", "admin123")
    assert success is True
    assert admin["name"] == "Sistem Yöneticisi"
    assert AuthController.login_admin("admin", "wrong-password")[0] is False

    connection = models.database.get_connection()
    try:
        stored = connection.execute("SELECT password_hash FROM admins").fetchone()[0]
    finally:
        connection.close()
    assert stored != "admin123"
    assert stored.startswith("$2")


@pytest.mark.parametrize(
    ("name", "member_email", "raw_password", "expected"),
    [
        ("", "user@example.com", "Guclu123!", "Ad soyad"),
        ("Test User", "not-an-email", "Guclu123!", "e-posta"),
        ("Test User", "user@example.com", "zayif", "8 karakter"),
        ("Test User", "user@example.com", "lowercase1", "büyük harf"),
    ],
)
def test_registration_rejects_invalid_inputs(name, member_email, raw_password, expected):
    success, message = AuthController.register(name, member_email, "555 111 22 33", raw_password)
    assert success is False
    assert expected.lower() in message.lower()


def test_registration_is_pending_and_email_is_case_insensitive():
    success, _ = AuthController.register("Ayşe Yılmaz", "Ayse@Example.com", "+90 555 111 22 33", "Guclu123!")
    assert success is True
    assert len(MemberController.get_pending_members()) == 1
    user, message = AuthController.login("AYSE@example.com", "Guclu123!")
    assert user is None
    assert "onaylanmamış" in message

    duplicate, message = AuthController.register(
        "Başka Üye", "ayse@example.com", "+90 555 222 33 44", "Baska123!"
    )
    assert duplicate is False
    assert "zaten" in message


def test_member_can_login_after_approval():
    member_id = add_member(1, approved=False)
    assert MemberController.approve_member(member_id)[0] is True
    user, message = AuthController.login("UYE1@EXAMPLE.COM", "Guclu123!")
    assert message == "Başarılı"
    assert user["id"] == member_id


def test_book_crud_preserves_entered_isbn_and_stock_math():
    book_id = add_book(copies=3)
    book = BookController.get_all_books()[0]
    assert book[0] == book_id
    assert book[3] == valid_isbn(1)
    assert book[8:10] == (3, 3)

    success, message = BookController.update_book(
        book_id,
        "Güncellenmiş Kitap",
        "Yeni Yazar",
        valid_isbn(1),
        "Deneme",
        2025,
        "Yeni açıklama",
        "",
        5,
    )
    assert success, message
    updated = BookController.get_all_books()[0]
    assert updated[1] == "Güncellenmiş Kitap"
    assert updated[7] == "https://example.com/cover.jpg"
    assert updated[8:10] == (5, 5)

    assert BookController.delete_book(book_id)[0] is True
    assert BookController.get_all_books() == []


def test_book_validation_and_duplicate_isbn():
    add_book()
    success, message = BookController.add_book("İkinci", "Yazar", valid_isbn(1), "Roman", 2024, "", "", 1)
    assert success is False
    assert "ISBN" in message

    success, message = BookController.add_book("Geçersiz", "Yazar", "12345", "Roman", 2024, "", "", 1)
    assert success is False
    assert "ISBN" in message


def test_borrow_and_return_updates_stock_once():
    book_id = add_book(copies=2)
    member_id = add_member()
    success, message = BorrowController.borrow_book(book_id, member_id)
    assert success, message
    assert BookController.get_all_books()[0][9] == 1

    borrow_id = BorrowController.get_all_borrows()[0][0]
    assert BorrowController.return_book(borrow_id)[0] is True
    assert BookController.get_all_books()[0][9] == 2
    assert BorrowController.return_book(borrow_id)[0] is False
    assert BookController.get_all_books()[0][9] == 2


def test_same_book_cannot_be_borrowed_twice_by_same_member():
    book_id = add_book(copies=2)
    member_id = add_member()
    assert BorrowController.borrow_book(book_id, member_id)[0] is True
    success, message = BorrowController.borrow_book(book_id, member_id)
    assert success is False
    assert "zaten" in message
    assert BookController.get_all_books()[0][9] == 1


def test_active_borrow_limit_is_enforced():
    member_id = add_member()
    for number in range(1, MAX_ACTIVE_BORROWS + 1):
        assert BorrowController.borrow_book(add_book(number), member_id)[0] is True

    extra_book_id = add_book(MAX_ACTIVE_BORROWS + 1)
    success, message = BorrowController.borrow_book(extra_book_id, member_id)
    assert success is False
    assert str(MAX_ACTIVE_BORROWS) in message


def test_inventory_and_member_cannot_be_archived_during_active_loan():
    book_id = add_book()
    member_id = add_member()
    assert BorrowController.borrow_book(book_id, member_id)[0] is True
    assert BookController.delete_book(book_id)[0] is False
    assert MemberController.delete_member(member_id)[0] is False

    borrow_id = BorrowController.get_all_borrows()[0][0]
    BorrowController.return_book(borrow_id)
    assert BookController.delete_book(book_id)[0] is True
    assert MemberController.delete_member(member_id)[0] is True
    assert len(BorrowController.get_all_borrows()) == 1


def test_total_copies_cannot_drop_below_checked_out_count():
    book_id = add_book(copies=2)
    first_member = add_member(1)
    second_member = add_member(2)
    assert BorrowController.borrow_book(book_id, first_member)[0] is True
    assert BorrowController.borrow_book(book_id, second_member)[0] is True

    book = BookController.get_all_books()[0]
    success, message = BookController.update_book(book_id, *book[1:7], book[7], 1)
    assert success is False
    assert "ödünçte" in message


def test_late_fee_trigger_calculates_five_lira_per_day():
    book_id = add_book()
    member_id = add_member()
    BorrowController.borrow_book(book_id, member_id)
    borrow_id = BorrowController.get_all_borrows()[0][0]

    connection = models.database.get_connection()
    try:
        connection.execute(
            """
            UPDATE borrows
            SET borrow_date = DATE('now', '-10 days'),
                return_date = DATE('now', '-3 days')
            WHERE id = ?
            """,
            (borrow_id,),
        )
        connection.commit()
    finally:
        connection.close()

    assert BorrowController.return_book(borrow_id)[0] is True
    assert BorrowController.get_all_borrows()[0][6] == 15.0


def test_profile_request_prevents_duplicates_and_email_conflicts():
    first_member = add_member(1)
    add_member(2)
    success, message = ProfileRequestController.add_request(
        first_member, "ignored snapshot", "Yeni İsim", "uye2@example.com"
    )
    assert success is False
    assert "başka" in message

    assert (
        ProfileRequestController.add_request(
            first_member, "ignored snapshot", "Yeni İsim", "yeni@example.com"
        )[0]
        is True
    )
    assert (
        ProfileRequestController.add_request(
            first_member, "ignored snapshot", "Başka İsim", "baska@example.com"
        )[0]
        is False
    )

    request = ProfileRequestController.get_pending_requests()[0]
    assert ProfileRequestController.approve_request(request[0], request[1], request[3], request[4])[0] is True
    user, _ = AuthController.login("yeni@example.com", "Guclu123!")
    assert user["name"] == "Yeni İsim"


def test_book_requests_and_notifications_are_scoped_to_member():
    first_member = add_member(1)
    second_member = add_member(2)
    request_args = (
        first_member,
        "Üye 1",
        "İstenen Kitap",
        "Bir Yazar",
        valid_isbn(99),
        "https://example.com/request.jpg",
    )
    assert RequestController.add_request(*request_args)[0] is True
    assert RequestController.add_request(*request_args)[0] is False

    assert NotificationController.add_notification(first_member, "Talebiniz onaylandı.") is True
    notification_id = NotificationController.get_unread_notifications(first_member)[0][0]
    assert NotificationController.mark_as_read(notification_id, second_member) is False
    assert len(NotificationController.get_unread_notifications(first_member)) == 1
    assert NotificationController.mark_as_read(notification_id, first_member) is True
    assert NotificationController.get_unread_notifications(first_member) == []


def test_database_trigger_rejects_direct_out_of_stock_insert():
    book_id = add_book(copies=1)
    first_member = add_member(1)
    second_member = add_member(2)
    assert BorrowController.borrow_book(book_id, first_member)[0] is True

    connection = models.database.get_connection()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="BOOK_UNAVAILABLE"):
            connection.execute(
                """
                INSERT INTO borrows (book_id, member_id, member_name_snapshot, return_date)
                VALUES (?, ?, ?, DATE('now', '+14 days'))
                """,
                (book_id, second_member, "Üye 2"),
            )
    finally:
        connection.rollback()
        connection.close()


def test_admin_overview_and_audit_activity_are_consistent():
    book_id = add_book(copies=4)
    member_id = add_member()
    assert BorrowController.borrow_book(book_id, member_id)[0] is True

    catalog = BookController.get_catalog_stats()
    assert catalog == {"titles": 1, "available": 3, "categories": 1}

    overview = BorrowController.get_admin_overview()
    assert overview["titles"] == 1
    assert overview["copies"] == 4
    assert overview["active_borrows"] == 1
    assert overview["members"] == 1
    assert overview["pending_members"] == 0

    activities = BorrowController.get_recent_activity()
    assert activities
    assert activities[0][0] == "BORROW"
    assert any(action == "CREATE" for action, _, _ in activities)
