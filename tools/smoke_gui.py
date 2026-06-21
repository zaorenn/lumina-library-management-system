"""Local, display-backed smoke test for every LibSys GUI screen."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

import models.database
from controllers.library import MemberController
from models.catalog import DEFAULT_CATALOG

SMOKE_DATABASE = Path.cwd() / ".libsys-gui-smoke.db"


def _cleanup_database() -> None:
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{SMOKE_DATABASE}{suffix}")
        path.unlink(missing_ok=True)


def _destroy_cleanly(app) -> None:
    for callback_id in app.tk.call("after", "info"):
        app.after_cancel(callback_id)
    app.destroy()


def _exercise_user_app() -> int:
    from views import ui

    # Remote covers are validated separately; GUI smoke stays deterministic.
    ui.CatalogCard.load_image = lambda self, url: None
    ui.BookDetailModal.load_image = lambda self, url: None

    app = ui.UserMainWindow()
    app.geometry("1180x780+20+20")
    app.update()
    app.update_idletasks()
    assert isinstance(app.current_view, ui.CatalogView)
    assert len(app.current_view.books) == 20
    while len(app.current_view.books) < len(DEFAULT_CATALOG):
        app.current_view.load_books()
    assert len(app.current_view.books) == len(DEFAULT_CATALOG)
    app.current_view.rearrange_grid()
    assert int(app.current_view.cards[2].grid_info()["column"]) == 2
    canvas = app.current_view.scroll._parent_canvas
    before_scroll = canvas.yview()[0]
    app.event_generate("<MouseWheel>", delta=-120)
    app.update_idletasks()
    assert canvas.yview()[0] > before_scroll
    app.withdraw()

    member = MemberController.get_all_members("smoke@example.com")[0]
    app.finalize_login(
        {
            "id": member[0],
            "name": member[1],
            "email": member[2],
            "must_change_password": 0,
        }
    )
    screens = (
        app.show_catalog,
        app.show_profile,
        app.show_request,
        app.show_notifications,
        app.show_settings,
    )
    for show_screen in screens:
        show_screen()
        app.update_idletasks()
        assert app.current_view.winfo_exists()
    _destroy_cleanly(app)
    return len(screens)


def _exercise_admin_app() -> int:
    from views import admin_ui

    admin_user = {
        "id": 1,
        "username": "admin",
        "name": "Sistem Yöneticisi",
        "email": "admin@libsys.local",
    }
    app = admin_ui.AdminWindow()
    app.withdraw()
    app.show_main(admin_user)
    app.update_idletasks()
    assert len(app.nav_buttons) == 10

    screen_factories = (
        lambda: admin_ui.AdminDashboard(app.content),
        lambda: admin_ui.AdminApprovalsView(app.content),
        lambda: admin_ui.AdminBooksView(app.content),
        lambda: admin_ui.AdminOpenLibraryView(app.content),
        lambda: admin_ui.AdminRequestsView(app.content),
        lambda: admin_ui.AdminMembersView(app.content),
        lambda: admin_ui.AdminProfileRequestsView(app.content),
        lambda: admin_ui.AdminBorrowsView(app.content),
        lambda: admin_ui.AdminProfileView(app.content, admin_user, lambda _data: None),
        lambda: admin_ui.AdminSettingsView(app.content),
    )
    checked = 0
    for create_screen in screen_factories:
        screen = create_screen()
        screen.pack(fill="both", expand=True)
        app.update_idletasks()
        assert screen.winfo_exists()
        if isinstance(screen, admin_ui.AdminBooksView):
            assert len(screen.tree.get_children()) == len(DEFAULT_CATALOG)
            first_item = screen.tree.get_children()[0]
            assert len(screen.tree.item(first_item, "values")) == 10
        if isinstance(screen, admin_ui.AdminSettingsView):
            screen.mode_var.set("Light")
            screen.change_mode()
            screen.mode_var.set("Dark")
            screen.change_mode()
        screen.destroy()
        checked += 1
    _destroy_cleanly(app)
    ctk.set_appearance_mode("Dark")
    return checked


def main() -> int:
    _cleanup_database()
    models.database.DB_PATH = SMOKE_DATABASE
    models.database.init_db(seed_catalog=True)
    success, message = MemberController.add_member(
        "Smoke Test Üyesi",
        "smoke@example.com",
        "+90 555 000 00 00",
        "Smoke123!",
        approved=True,
    )
    if not success:
        raise RuntimeError(message)

    try:
        user_screens = _exercise_user_app()
        admin_screens = _exercise_admin_app()
        ok, result = models.database.check_integrity()
        assert ok, result
        print(f"GUI smoke başarılı: {user_screens} üye + {admin_screens} yönetici ekranı.")
    finally:
        _cleanup_database()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
