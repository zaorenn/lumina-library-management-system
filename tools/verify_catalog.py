"""Validate curated catalog metadata and optionally probe remote cover images."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from controllers.validators import isbn
from models.catalog import DEFAULT_CATALOG, CatalogBook


def validate_metadata() -> list[str]:
    errors = []
    for book in DEFAULT_CATALOG:
        try:
            isbn(book.isbn)
        except ValueError as exc:
            errors.append(f"{book.title}: {exc}")
        if len(book.summary) < 100:
            errors.append(f"{book.title}: özet çok kısa")
    return errors


def probe_cover(book: CatalogBook) -> str | None:
    try:
        with requests.get(book.cover_url, timeout=15, stream=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                return f"{book.title}: görsel yerine {content_type or 'bilinmeyen içerik'} döndü"
    except requests.RequestException as exc:
        return f"{book.title}: kapak erişilemedi ({exc})"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="LibSys başlangıç kataloğunu doğrula.")
    parser.add_argument("--online", action="store_true", help="Open Library kapaklarını da kontrol et.")
    args = parser.parse_args()

    errors = validate_metadata()
    if args.online:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(probe_cover, book): book for book in DEFAULT_CATALOG}
            for future in as_completed(futures):
                if error := future.result():
                    errors.append(error)

    if errors:
        print("\n".join(errors))
        return 1
    print(f"{len(DEFAULT_CATALOG)} katalog kaydı başarıyla doğrulandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
