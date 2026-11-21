"""
FastAPI server for the calendar print preview.

Renders the calendar with the templates in src/calendlam and serves it to the
Alpine.js frontend in static/, which shows it in a scrollable iframe and prints it.

Run from the repository root:
    uvicorn calendlam3.app:app --reload
"""
import re
import sys
from pathlib import Path

from fastapi import FastAPI, Query
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

app = FastAPI(title="Calendlam")


@app.get("/render", response_class=HTMLResponse)
def render(
    year: int = Query(calendlam.YEAR, ge=1, le=9999),
    sheets: int = Query(calendlam.SHEETS_PER_SIGNATURE, ge=1, le=50),
    info: bool = True,
):
    """Full printable HTML document with the stylesheet inlined."""
    html = calendlam.render_year_html(year, sheets, info)
    css = (calendlam.TEMPLATES_DIR / "style.css").read_text()
    html = re.sub(r'<link rel="stylesheet" href="style.css">',
                  lambda _: f"<style>{css}{PREVIEW_CSS}</style>", html)
    return html


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
