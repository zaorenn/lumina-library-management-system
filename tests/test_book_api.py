"""Tests for normalized, shared online book metadata search."""

from __future__ import annotations

import requests

from services import book_api


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_google_books_result_has_cover_description_and_valid_isbn(monkeypatch):
    payload = {
        "items": [
            {
                "volumeInfo": {
                    "title": "Test Kitabı",
                    "authors": ["Test Yazarı"],
                    "industryIdentifiers": [
                        {"type": "ISBN_10", "identifier": "0451524934"},
                        {"type": "ISBN_13", "identifier": "9780451524935"},
                    ],
                    "categories": ["Fiction"],
                    "publishedDate": "1949-06-08",
                    "description": "<b>Güçlü</b> ve açıklayıcı bir çevrimiçi kitap özeti.",
                    "imageLinks": {"thumbnail": "http://example.com/cover.jpg"},
                }
            }
        ]
    }

    def fake_get(url, **_kwargs):
        if url == book_api.OPEN_LIBRARY_SEARCH_URL:
            return FakeResponse({"docs": []})
        assert url == book_api.GOOGLE_BOOKS_URL
        return FakeResponse(payload)

    monkeypatch.setattr(book_api._SESSION, "get", fake_get)
    book_api.clear_search_cache()
    results = book_api.search_books("Test Kitabı", limit=1)

    assert results[0].isbn == "9780451524935"
    assert results[0].cover_url == "https://example.com/cover.jpg"
    assert results[0].description == "Güçlü ve açıklayıcı bir çevrimiçi kitap özeti."
    assert results[0].source == "Google Books"


def test_open_library_is_used_when_google_books_fails(monkeypatch):
    def fake_get(url, **_kwargs):
        if url == book_api.GOOGLE_BOOKS_URL:
            raise requests.ConnectionError("offline")
        return FakeResponse(
            {
                "docs": [
                    {
                        "title": "Yedek Sonuç",
                        "author_name": ["Yazar"],
                        "isbn": ["9780743273565"],
                        "subject": ["Classic"],
                        "first_publish_year": 1925,
                        "cover_i": 123,
                    }
                ]
            }
        )

    monkeypatch.setattr(book_api._SESSION, "get", fake_get)
    book_api.clear_search_cache()
    result = book_api.search_books("Yedek Sonuç", limit=2)[0]

    assert result.source == "Open Library"
    assert result.cover_url.endswith("/123-L.jpg?default=false")
    assert result.description


def test_search_deduplicates_provider_results(monkeypatch):
    google_payload = {
        "items": [
            {
                "volumeInfo": {
                    "title": "Aynı Kitap",
                    "authors": ["Yazar"],
                    "industryIdentifiers": [{"identifier": "9780451524935"}],
                }
            }
        ]
    }
    open_payload = {
        "docs": [
            {
                "title": "Aynı Kitap",
                "author_name": ["Yazar"],
                "isbn": ["9780451524935"],
                "cover_i": 456,
            }
        ]
    }

    def fake_get(url, **_kwargs):
        return FakeResponse(google_payload if url == book_api.GOOGLE_BOOKS_URL else open_payload)

    monkeypatch.setattr(book_api._SESSION, "get", fake_get)
    book_api.clear_search_cache()
    assert len(book_api.search_books("Aynı Kitap", limit=2)) == 1
