"""LibSys member application entry point."""

from models.database import init_db
from views.ui import UserMainWindow


def main() -> None:
    init_db()
    application = UserMainWindow()
    application.mainloop()


if __name__ == "__main__":
    main()
