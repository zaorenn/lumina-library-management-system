"""Tests for evaluator-friendly LibSys demo credentials."""

from __future__ import annotations

import models.database
from controllers.auth import AuthController
from models.database import get_connection
from seed_db import seed


def test_demo_admin_and_member_can_log_in_with_readme_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(models.database, "DB_PATH", tmp_path / "demo.db")
    monkeypatch.setattr(models.database, "DEFAULT_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(models.database, "DEFAULT_ADMIN_PASSWORD", "admin123")

    # Yeni kurulumda demo hesap ek komut gerektirmeden hazırdır.
    models.database.init_db()

    admin_ok, _ = AuthController.login_admin("admin", "admin123")
    member, message = AuthController.login("uye", "uye123")
    assert admin_ok is True
    assert message == "Başarılı"
    assert member["name"] == "Deneme Üyesi"

    connection = get_connection()
    try:
        demo = connection.execute(
            "SELECT username, email, phone, is_approved FROM members WHERE username = 'uye'"
        ).fetchone()
    finally:
        connection.close()
    assert demo == ("uye", "", "", 1)

    # Bu istisna yalnız seed katmanında oluşturulur; normal kayıt formu boş
    # e-posta ve kısa demo parolasıyla hesap açamaz.
    assert AuthController.register("Deneme", "", "", "uye123")[0] is False

    # Seed komutu mevcut demo kaydını çoğaltmadan README parolasını yeniler.
    seed()
    connection = get_connection()
    try:
        assert connection.execute("SELECT COUNT(*) FROM members WHERE username = 'uye'").fetchone()[0] == 1
    finally:
        connection.close()
