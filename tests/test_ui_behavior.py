"""Small GUI behavior tests that do not require a display server."""

from __future__ import annotations

from types import SimpleNamespace

from views.ui import CATALOG_SCROLL_UNITS, CatalogView


class FakeCanvas:
    def __init__(self):
        self.scroll_calls = []

    def yview_scroll(self, amount, unit):
        self.scroll_calls.append((amount, unit))

    def yview(self):
        return 0.2, 0.96


def test_catalog_mousewheel_scrolls_nested_cards_and_triggers_lazy_load():
    canvas = FakeCanvas()
    view = SimpleNamespace(
        scroll=SimpleNamespace(_parent_canvas=canvas),
        load_books=lambda: setattr(view, "loaded", True),
        loaded=False,
    )

    result = CatalogView.on_mousewheel(view, SimpleNamespace(delta=-120, num=None))

    assert result == "break"
    assert canvas.scroll_calls == [(CATALOG_SCROLL_UNITS, "units")]
    assert view.loaded is True
