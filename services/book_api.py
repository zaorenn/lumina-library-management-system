"""Reliable book metadata search backed by Google Books and Open Library."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from controllers.validators import ValidationError, isbn

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
USER_AGENT = "LibSys/3.0 (+https://github.com/zaorenn/libsys-library-management-system)"
REQUEST_TIMEOUT = (4, 12)


class BookServiceError(RuntimeError):
    """Raised when neither metadata provider can answer a search."""


@dataclass(frozen=True, slots=True)
class OnlineBook:
    title: str
    author: str
    isbn: str
    category: str
    published_year: int
    description: str
    cover_url: str
    source: str


def _build_session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.35,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    session.mount("https://", adapter)
    return session


_SESSION = _build_session()


def _clean_text(value: object, *, limit: int) -> str:
    raw = html.unescape(str(value or ""))
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()[:limit]


def _valid_isbn(values: object) -> str | None:
    candidates: list[object] = []
    if isinstance(values, (list, tuple)):
        candidates.extend(values)
    elif values:
        candidates.append(values)
    # Prefer ISBN-13 when a provider gives multiple editions.
    candidates.sort(key=lambda item: 0 if len(re.sub(r"[-\s]", "", str(item))) == 13 else 1)
    for candidate in candidates:
        try:
            return isbn(candidate)
        except ValidationError:
            continue
    return None


def _year(value: object) -> int:
    match = re.search(r"-?\d{1,4}", str(value or ""))
    if not match:
        return date.today().year
    parsed = int(match.group())
    return parsed if -3000 <= parsed <= date.today().year else date.today().year


def _description(value: object, title: str, author: str, category: str) -> str:
    cleaned = _clean_text(value, limit=1900)
    if cleaned:
        return cleaned
    return (
        f"{title}, {author} tarafından kaleme alınmış {category.lower()} kategorisinde bir eserdir. "
        "Bu kayıt, eserin temel bibliyografik bilgilerini çevrimiçi kitap veritabanından sunar; "
        "ayrıntılı içerik ve baskı bilgileri yayınevine göre değişebilir."
    )


def _cover_from_isbn(isbn_value: str) -> str:
    return f"https://covers.openlibrary.org/b/isbn/{isbn_value}-L.jpg?default=false"


def _parse_google(item: dict[str, Any]) -> OnlineBook | None:
    info = item.get("volumeInfo") or {}
    identifiers = [entry.get("identifier") for entry in info.get("industryIdentifiers") or []]
    isbn_value = _valid_isbn(identifiers)
    title = _clean_text(info.get("title"), limit=200)
    if not isbn_value or not title:
        return None
    authors = info.get("authors") or []
    author = _clean_text(authors[0] if authors else "Bilinmeyen Yazar", limit=150)
    categories = info.get("categories") or []
    category = _clean_text(categories[0] if categories else "Genel", limit=80) or "Genel"
    images = info.get("imageLinks") or {}
    cover = images.get("extraLarge") or images.get("large") or images.get("medium") or images.get("thumbnail")
    cover_url = str(cover or _cover_from_isbn(isbn_value)).replace("http://", "https://", 1)
    return OnlineBook(
        title=title,
        author=author,
        isbn=isbn_value,
        category=category,
        published_year=_year(info.get("publishedDate")),
        description=_description(info.get("description"), title, author, category),
        cover_url=cover_url,
        source="Google Books",
    )


def _parse_open_library(doc: dict[str, Any]) -> OnlineBook | None:
    isbn_value = _valid_isbn(doc.get("isbn"))
    title = _clean_text(doc.get("title"), limit=200)
    cover_id = doc.get("cover_i")
    if not isbn_value or not title or not cover_id:
        return None
    authors = doc.get("author_name") or []
    author = _clean_text(authors[0] if authors else "Bilinmeyen Yazar", limit=150)
    subjects = doc.get("subject") or []
    category = _clean_text(subjects[0] if subjects else "Genel", limit=80) or "Genel"
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg?default=false"
    return OnlineBook(
        title=title,
        author=author,
        isbn=isbn_value,
        category=category,
        published_year=_year(doc.get("first_publish_year")),
        description=_description(doc.get("first_sentence"), title, author, category),
        cover_url=cover_url,
        source="Open Library",
    )


def _google_search(query: str, limit: int) -> list[OnlineBook]:
    response = _SESSION.get(
        GOOGLE_BOOKS_URL,
        params={"q": query, "maxResults": min(40, max(limit * 2, 10)), "printType": "books"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return [book for item in response.json().get("items", []) if (book := _parse_google(item))]


def _open_library_search(query: str, limit: int) -> list[OnlineBook]:
    response = _SESSION.get(
        OPEN_LIBRARY_SEARCH_URL,
        params={
            "q": query,
            "limit": min(50, max(limit * 3, 15)),
            "fields": "title,author_name,isbn,subject,first_publish_year,cover_i,first_sentence",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return [book for doc in response.json().get("docs", []) if (book := _parse_open_library(doc))]


@lru_cache(maxsize=64)
def _cached_search(normalized_query: str, limit: int) -> tuple[OnlineBook, ...]:
    results: list[OnlineBook] = []
    provider_errors: list[Exception] = []
    for provider in (_open_library_search, _google_search):
        if len(results) >= limit:
            break
        try:
            results.extend(provider(normalized_query, limit))
        except (requests.RequestException, ValueError) as exc:
            provider_errors.append(exc)

    unique: list[OnlineBook] = []
    seen: set[str] = set()
    for book in results:
        if book.isbn in seen:
            continue
        seen.add(book.isbn)
        unique.append(book)
        if len(unique) == limit:
            break
    if not unique and provider_errors:
        raise BookServiceError(
            "Çevrimiçi kitap servislerine şu anda ulaşılamıyor. İnternet bağlantınızı kontrol edip yeniden deneyin."
        ) from provider_errors[-1]
    return tuple(unique)


def search_books(query: object, *, limit: int = 10) -> list[OnlineBook]:
    """Search shared online metadata providers and return normalized books."""

    normalized = re.sub(r"\s+", " ", str(query or "")).strip()
    if len(normalized) < 2:
        raise BookServiceError("Aramak için en az 2 karakter girin.")
    safe_limit = min(20, max(1, int(limit)))
    return list(_cached_search(normalized.casefold(), safe_limit))


def clear_search_cache() -> None:
    """Clear cached API answers; useful for tests and explicit refreshes."""

    _cached_search.cache_clear()
