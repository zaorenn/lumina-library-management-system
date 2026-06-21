"""Authentication and account-management use cases."""

from __future__ import annotations

import sqlite3

import bcrypt

from controllers.validators import ValidationError, email, password, text
from models.database import db_session


def _verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def _hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class AuthController:
    @staticmethod
    def login_admin(username: str, raw_password: str):
        normalized_username = str(username or "").strip()
        with db_session() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash, name, email
                FROM admins WHERE username = ? COLLATE NOCASE
                """,
                (normalized_username,),
            ).fetchone()

        if row and _verify_password(str(raw_password or ""), row[2]):
            return True, {
                "id": row[0],
                "username": row[1],
                "name": row[3],
                "email": row[4],
            }
        return False, None

    @staticmethod
    def update_admin_profile(admin_id, new_username, new_name, new_email):
        try:
            username = text(new_username, "Kullanıcı adı", minimum=3, maximum=50)
            name = text(new_name, "Ad soyad", minimum=2, maximum=100)
            normalized_email = email(new_email)
            with db_session() as connection:
                cursor = connection.execute(
                    """
                    UPDATE admins SET username = ?, name = ?, email = ? WHERE id = ?
                    """,
                    (username, name, normalized_email, admin_id),
                )
                if cursor.rowcount == 0:
                    return False, "Yönetici bulunamadı."
            return True, "Profil başarıyla güncellendi."
        except ValidationError as exc:
            return False, str(exc)
        except sqlite3.IntegrityError:
            return False, "Bu kullanıcı adı veya e-posta zaten kullanılıyor."

    @staticmethod
    def change_admin_password(admin_id, old_password, new_password):
        try:
            validated_password = password(new_password)
        except ValidationError as exc:
            return False, str(exc)

        with db_session() as connection:
            row = connection.execute("SELECT password_hash FROM admins WHERE id = ?", (admin_id,)).fetchone()
            if not row:
                return False, "Yönetici bulunamadı."
            if not _verify_password(str(old_password or ""), row[0]):
                return False, "Mevcut şifre hatalı."
            if _verify_password(validated_password, row[0]):
                return False, "Yeni şifre mevcut şifreden farklı olmalıdır."
            connection.execute(
                "UPDATE admins SET password_hash = ? WHERE id = ?",
                (_hash_password(validated_password), admin_id),
            )
        return True, "Şifre başarıyla güncellendi."

    @staticmethod
    def register(name, member_email, member_phone, raw_password):
        from controllers.validators import phone

        try:
            clean_name = text(name, "Ad soyad", minimum=2, maximum=100)
            normalized_email = email(member_email)
            clean_phone = phone(member_phone)
            validated_password = password(raw_password)
            with db_session() as connection:
                connection.execute(
                    """
                    INSERT INTO members
                        (name, email, phone, password_hash, is_approved, is_active)
                    VALUES (?, ?, ?, ?, 0, 1)
                    """,
                    (
                        clean_name,
                        normalized_email,
                        clean_phone,
                        _hash_password(validated_password),
                    ),
                )
            return True, "Kayıt başarılı! Hesabınız yönetici onayından sonra açılacak."
        except ValidationError as exc:
            return False, str(exc)
        except sqlite3.IntegrityError:
            return False, "Bu e-posta adresi sistemde zaten kayıtlı."

    @staticmethod
    def login(member_email, raw_password):
        login_value = str(member_email or "").strip()
        try:
            if "@" in login_value:
                normalized_email = email(login_value)
                normalized_username = ""
            else:
                normalized_email = ""
                normalized_username = text(login_value, "Kullanıcı adı", minimum=3, maximum=50).lower()
        except ValidationError:
            return None, "Hatalı e-posta veya şifre."

        with db_session() as connection:
            row = connection.execute(
                """
                SELECT id, name, email, password_hash, is_approved, must_change_password
                FROM members
                WHERE is_active = 1
                  AND (email = ? COLLATE NOCASE OR username = ? COLLATE NOCASE)
                """,
                (normalized_email, normalized_username),
            ).fetchone()

        if not row or not _verify_password(str(raw_password or ""), row[3]):
            return None, "Hatalı e-posta veya şifre."
        if not row[4]:
            return None, "Hesabınız henüz yönetici tarafından onaylanmamış."
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "must_change_password": row[5],
        }, "Başarılı"

    @staticmethod
    def change_password(member_id, old_password, new_password):
        try:
            validated_password = password(new_password)
        except ValidationError as exc:
            return False, str(exc)

        with db_session() as connection:
            row = connection.execute(
                "SELECT password_hash FROM members WHERE id = ? AND is_active = 1",
                (member_id,),
            ).fetchone()
            if not row or not _verify_password(str(old_password or ""), row[0]):
                return False, "Mevcut şifreniz hatalı."
            if _verify_password(validated_password, row[0]):
                return False, "Yeni şifre mevcut şifreden farklı olmalıdır."
            connection.execute(
                """
                UPDATE members
                SET password_hash = ?, must_change_password = 0
                WHERE id = ?
                """,
                (_hash_password(validated_password), member_id),
            )
        return True, "Şifreniz başarıyla değiştirildi."
