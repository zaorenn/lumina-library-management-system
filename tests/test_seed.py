"""Tests for evaluator-friendly LibSys demo credentials."""

from __future__ import annotations

import models.database
from controllers.auth import AuthController
from seed_db import seed


def test_demo_admin_and_member_can_log_in_with_readme_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(models.database, "DB_PATH", tmp_path / "demo.db")
    monkeypatch.setattr(models.database, "DEFAULT_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(models.database, "DEFAULT_ADMIN_PASSWORD", "admin123")

    seed()

    admin_ok, _ = AuthController.login_admin("admin", "admin123")
    member, message = AuthController.login("uye", "uye123")
    assert admin_ok is True
    assert message == "Başarılı"
    assert member["name"] == "Deneme Üyesi"
