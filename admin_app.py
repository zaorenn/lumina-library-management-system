"""LibSys administration application entry point."""

from models.database import init_db
from views.admin_ui import AdminWindow


def main() -> None:
    init_db()
    application = AdminWindow()
    application.mainloop()


if __name__ == "__main__":
    main()
