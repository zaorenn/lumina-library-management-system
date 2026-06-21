"""Tests for the built-in cover-rich starter catalog."""

from __future__ import annotations

import models.database
from controllers.validators import isbn
from models.catalog import DEFAULT_CATALOG


def test_default_catalog_is_complete_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(models.database, "DB_PATH", tmp_path / "catalog.db")
    monkeypatch.setattr(models.database, "DEFAULT_ADMIN_PASSWORD", "admin123")

    assert len(DEFAULT_CATALOG) == 80
    assert len({book.isbn for book in DEFAULT_CATALOG}) == 80
    assert len({book.cover_url for book in DEFAULT_CATALOG}) == 80
    assert all(isbn(book.isbn) == book.isbn for book in DEFAULT_CATALOG)
    assert all(len(book.summary) >= 100 for book in DEFAULT_CATALOG)

    models.database.init_db(seed_catalog=True)
    models.database.init_db(seed_catalog=True)

    connection = models.database.get_connection()
    try:
        rows = connection.execute(
            """
            SELECT isbn, description, cover_image_url, total_copies, available_copies
            FROM books WHERE is_active = 1
            """
        ).fetchall()
    finally:
        connection.close()

    assert len(rows) == 80
    assert all(description.strip() for _, description, _, _, _ in rows)
    assert all(url.startswith("https://covers.openlibrary.org/") for _, _, url, _, _ in rows)
    assert all(total == available == 4 for _, _, _, total, available in rows)


def test_catalog_repair_restores_cover_and_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(models.database, "DB_PATH", tmp_path / "repair.db")
    models.database.init_db(seed_catalog=True)

    connection = models.database.get_connection()
    try:
        connection.execute(
            "UPDATE books SET description = '', cover_image_url = '' WHERE isbn = ?",
            (DEFAULT_CATALOG[0].isbn,),
        )
        connection.commit()
    finally:
        connection.close()

    assert models.database.refresh_catalog_metadata() == 0
    ok, result = models.database.check_integrity()
    assert ok, result

    connection = models.database.get_connection()
    try:
        restored = connection.execute(
            "SELECT description, cover_image_url FROM books WHERE isbn = ?",
            (DEFAULT_CATALOG[0].isbn,),
        ).fetchone()
    finally:
        connection.close()
    assert restored == (DEFAULT_CATALOG[0].summary, DEFAULT_CATALOG[0].cover_url)
