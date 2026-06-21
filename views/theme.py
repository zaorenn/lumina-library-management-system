"""LibSys shared visual language and filesystem-safe asset helpers."""

from pathlib import Path

APP_NAME = "LibSys"
TAGLINE = "Hikâyeler burada ışık bulur."
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_DIR = ASSET_DIR / "icons"

# Neutral Glass palette: frosted whites by day, near-black glass by night.
BACKGROUND = ("#E9EDF1", "#050607")
PANEL = ("#F7F9FA", "#0B0E11")
PANEL_ELEVATED = ("#EFF3F5", "#14191E")
GLASS = ("#FBFCFD", "#101419")
GLASS_MUTED = ("#EDF1F3", "#171D22")
GLASS_HOVER = ("#E1E7EA", "#222A30")
PRIMARY = ("#2F5960", "#258E88")
PRIMARY_HOVER = ("#24464C", "#31A49D")
ACCENT = ("#126F70", "#65D7CF")
SUCCESS = ("#167361", "#48CFAE")
DANGER = ("#B94152", "#F07080")
WARNING = ("#986313", "#E8B45D")
TEXT = ("#172026", "#EDF3F4")
TEXT_MUTED = ("#657178", "#95A2A7")
BORDER = ("#C9D1D5", "#293137")
GLASS_BORDER = ("#BDC8CC", "#364249")
INPUT = ("#F3F6F7", "#090C0E")
SIDEBAR = ("#E4E9EB", "#080B0D")

FONT_FAMILY = "Segoe UI"
RADIUS_LARGE = 22
RADIUS_MEDIUM = 16


def icon_path(filename: str) -> Path:
    return ICON_DIR / filename
