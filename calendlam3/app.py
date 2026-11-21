"""
FastAPI server for the calendar print preview.

Renders the calendar with the templates in src/calendlam and serves it to the
Alpine.js frontend in static/, which shows it in a scrollable iframe and prints it.

Run from the repository root:
    uvicorn calendlam3.app:app --reload
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"

sys.path.insert(0, str(ROOT / "src"))
import calendlam  # noqa: E402

# Screen-only styling so the pages read as sheets of paper in the preview.
# Print output is untouched (these rules are all inside @media screen).
PREVIEW_CSS = """
@media screen {
  html { background: #e5e7eb; }
  body { padding: 16px 0; }
  .sheet-side { width: 289mm; height: 202mm; margin: 0 auto 16px; background: #fff;
                box-shadow: 0 2px 8px rgba(0,0,0,.25); position: relative; }
  .sheet-side::after { content: ""; position: absolute; left: 50%; top: 0; bottom: 0;
                       border-left: 1px dashed #bbb; }  /* fold line */
}
"""

# Google Fonts offered for the day numbers and weekday names (all have a regular 400 weight, which the stylesheet uses).
# The Google Fonts catalogue itself needs an API key, so this is a curated list.
FONTS = [
    "Cinzel", "Rubik Glitch", "Rubik", "Open Sans", "Bebas Neue", "Oswald", "Roboto Slab", "Playfair Display",
    "Abril Fatface", "Lobster", "Pacifico", "Caveat", "Permanent Marker", "Shadows Into Light", "Special Elite",
    "Righteous", "Bungee", "Orbitron", "Press Start 2P", "Monoton", "Fredericka the Great",
]

LineStyle = Literal["solid", "dotted", "dashed", "none"]  # keep in sync with calendlam.LINE_STYLES

app = FastAPI(title="Calendlam")


# --- saved settings: every save is a new JSON file, so older versions stay available ---
SETTINGS_DIR = Path(__file__).resolve().parent / "saves"
SAVE_ID = re.compile(r"^[0-9A-Za-z_-]{1,100}$")  # file stem; also blocks path traversal
MAX_SETTINGS_BYTES = 20_000


def _save_path(save_id: str) -> Path:
    if not SAVE_ID.match(save_id):
        raise HTTPException(status_code=404, detail="no such save")
    return SETTINGS_DIR / f"{save_id}.json"


@app.get("/api/settings")
def list_settings():
    """Saved versions, newest first."""
    saves = []
    for path in sorted(SETTINGS_DIR.glob("*.json"), reverse=True) if SETTINGS_DIR.is_dir() else []:
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue  # skip unreadable/corrupt files
        saves.append({"id": path.stem, "name": data.get("name", ""), "saved_at": data.get("saved_at", "")})
    return saves


@app.get("/api/settings/{save_id}")
def get_settings(save_id: str):
    path = _save_path(save_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="no such save")
    return json.loads(path.read_text())


@app.post("/api/settings")
def save_settings(payload: dict = Body(...)):
    """Write the posted settings to a NEW file; returns its id."""
    settings = payload.get("settings")
    name = str(payload.get("name") or "").strip()[:60]
    if not isinstance(settings, dict):
        raise HTTPException(status_code=422, detail="settings must be an object")
    now = datetime.now()
    document = {"name": name, "saved_at": now.isoformat(timespec="seconds"), "settings": settings}
    text = json.dumps(document, indent=2, ensure_ascii=False)
    if len(text.encode()) > MAX_SETTINGS_BYTES:
        raise HTTPException(status_code=413, detail="settings too large")
    slug = re.sub(r"[^0-9A-Za-z]+", "-", name).strip("-").lower()[:40]
    save_id = now.strftime("%Y%m%d-%H%M%S-%f") + (f"_{slug}" if slug else "")
    SETTINGS_DIR.mkdir(exist_ok=True)
    (SETTINGS_DIR / f"{save_id}.json").write_text(text)  # unique timestamp: never overwrites
    return {"id": save_id, "name": name, "saved_at": document["saved_at"]}


@app.get("/api/fonts")
def fonts():
    return FONTS


@app.get("/render", response_class=HTMLResponse)
def render(
    year: int = Query(calendlam.YEAR, ge=1, le=9999),
    sheets: int = Query(calendlam.SHEETS_PER_SIGNATURE, ge=1, le=50),
    info: bool = True,
    number_font: str | None = None,
    day_font: str | None = None,
    month_font: str | None = None,
    line_header: float | None = Query(None, ge=0, le=3),
    line_row: float | None = Query(None, ge=0, le=3),
    line_mid: float | None = Query(None, ge=0, le=3),
    line_q1: float | None = Query(None, ge=0, le=3),
    line_q3: float | None = Query(None, ge=0, le=3),
    overview: bool = True,
    row_height: float | None = Query(None, ge=5, le=40),
    overview_row_height: float | None = Query(None, ge=2, le=8),
    margin_left: float | None = Query(None, ge=0, le=30),
    extend_right: float | None = Query(None, ge=0, le=30),
    style_header: LineStyle | None = None,
    style_row: LineStyle | None = None,
    style_mid: LineStyle | None = None,
    style_q1: LineStyle | None = None,
    style_q3: LineStyle | None = None,
):
    """Full printable HTML document with the stylesheet inlined."""
    fonts = {"number": number_font, "day": day_font, "month": month_font}
    for font in fonts.values():
        if font is not None and font not in FONTS:  # whitelist: value goes into CSS/URL
            raise HTTPException(status_code=422, detail="unknown font")
    html = calendlam.render_year_html(
        year, sheets, info, fonts,
        lines={"header": line_header, "row": line_row, "mid": line_mid, "q1": line_q1, "q3": line_q3},
        layout={"row-height": row_height, "overview-row-height": overview_row_height, "margin-left": margin_left, "extend-right": extend_right},
        overview=overview,
        line_styles={"header": style_header, "row": style_row, "mid": style_mid, "q1": style_q1, "q3": style_q3})
    css = (calendlam.TEMPLATES_DIR / "style.css").read_text()
    html = re.sub(r'<link rel="stylesheet" href="style.css">',
                  lambda _: f"<style>{css}{PREVIEW_CSS}</style>", html)
    return html


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
