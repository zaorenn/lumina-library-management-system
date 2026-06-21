"""Create deterministic demo accounts and the curated starter catalog."""

from __future__ import annotations

import argparse

from models.catalog import DEFAULT_CATALOG
from models.database import ensure_demo_member, get_connection, init_db

RESET_ORDER = (
    "notifications",
    "profile_requests",
    "book_requests",
    # Eski proje sürümlerinden kalmış olabilecek tablolar.
    "reviews",
    "wishlist",
    "reservations",
    "borrows",
    "audit_logs",
    "books",
    "members",
    "admins",
)


def _reset_database() -> None:
    connection = get_connection()
    try:
        existing_tables = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        for table in RESET_ORDER:
            if table not in existing_tables:
                continue
            connection.execute(f"DELETE FROM {table}")
            connection.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def seed(*, reset: bool = False) -> None:
    """Prepare demo content, preserving existing data unless reset is explicit."""

    init_db(seed_catalog=False)
    if reset:
        print("Veritabanındaki mevcut veriler sıfırlanıyor...")
        _reset_database()

    init_db(seed_catalog=True)
    ensure_demo_member(reset_password=True)
    print(f"{len(DEFAULT_CATALOG)} kapaklı ve özetli katalog kitabı hazır.")
    print("Demo hesapları: admin / admin123 ve uye / uye123")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LibSys demo verilerini hazırla.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Mevcut verileri silip temiz demo verisi oluşturur.",
    )
    seed(reset=parser.parse_args().reset)
