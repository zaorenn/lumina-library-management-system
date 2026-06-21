"""Shared input validation for controller and GUI boundaries."""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ValidationError(ValueError):
    """Raised when user-provided data does not satisfy a business rule."""


def text(value: object, label: str, *, minimum: int = 1, maximum: int = 255) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) < minimum:
        raise ValidationError(f"{label} en az {minimum} karakter olmalıdır.")
    if len(cleaned) > maximum:
        raise ValidationError(f"{label} en fazla {maximum} karakter olabilir.")
    return cleaned


def optional_text(value: object, label: str, *, maximum: int = 2000) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) > maximum:
        raise ValidationError(f"{label} en fazla {maximum} karakter olabilir.")
    return cleaned


def email(value: object) -> str:
    cleaned = text(value, "E-posta", minimum=5, maximum=254).lower()
    if not EMAIL_RE.fullmatch(cleaned):
        raise ValidationError("Geçerli bir e-posta adresi girin.")
    return cleaned


def phone(value: object) -> str:
    cleaned = optional_text(value, "Telefon", maximum=24)
    if not cleaned:
        return ""
    if not re.fullmatch(r"[+()\d\s.-]+", cleaned):
        raise ValidationError("Telefon numarası geçersiz karakter içeriyor.")
    digit_count = sum(char.isdigit() for char in cleaned)
    if not 7 <= digit_count <= 15:
        raise ValidationError("Telefon numarası 7-15 rakam içermelidir.")
    return cleaned


def password(value: object) -> str:
    raw = str(value or "")
    if len(raw) < 8:
        raise ValidationError("Şifre en az 8 karakter olmalıdır.")
    if len(raw) > 128:
        raise ValidationError("Şifre en fazla 128 karakter olabilir.")
    if not any(char.islower() for char in raw):
        raise ValidationError("Şifre en az bir küçük harf içermelidir.")
    if not any(char.isupper() for char in raw):
        raise ValidationError("Şifre en az bir büyük harf içermelidir.")
    if not any(char.isdigit() for char in raw):
        raise ValidationError("Şifre en az bir rakam içermelidir.")
    return raw


def isbn(value: object) -> str:
    cleaned = re.sub(r"[-\s]", "", str(value or "").upper())
    if len(cleaned) == 10 and re.fullmatch(r"\d{9}[\dX]", cleaned):
        total = sum((10 - index) * (10 if char == "X" else int(char)) for index, char in enumerate(cleaned))
        if total % 11 == 0:
            return cleaned
    elif len(cleaned) == 13 and cleaned.isdigit():
        total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(cleaned[:12]))
        if (10 - total % 10) % 10 == int(cleaned[-1]):
            return cleaned
    raise ValidationError("Geçerli bir ISBN-10 veya ISBN-13 girin.")


def first_valid_isbn(values: object) -> str | None:
    """Return the first valid ISBN from an external API result list."""

    if not isinstance(values, (list, tuple)):
        return None
    for value in values:
        try:
            return isbn(value)
        except ValidationError:
            continue
    return None


def year(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Yayın yılı tam sayı olmalıdır.") from exc
    if not -3000 <= parsed <= date.today().year:
        raise ValidationError(f"Yayın yılı -3000 ile {date.today().year} arasında olmalıdır.")
    return parsed


def copies(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Kopya sayısı tam sayı olmalıdır.") from exc
    if not 1 <= parsed <= 100_000:
        raise ValidationError("Kopya sayısı 1 ile 100.000 arasında olmalıdır.")
    return parsed


def url(value: object) -> str:
    cleaned = optional_text(value, "Kapak URL'si", maximum=2048)
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("Kapak adresi http veya https ile başlayan geçerli bir URL olmalıdır.")
    return cleaned


def isbn13_from_body(body: str) -> str:
    """Return a valid ISBN-13 from a twelve-digit body (used by demo data)."""

    if len(body) != 12 or not body.isdigit():
        raise ValueError("ISBN-13 gövdesi 12 rakam olmalıdır.")
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(body))
    return f"{body}{(10 - total % 10) % 10}"
