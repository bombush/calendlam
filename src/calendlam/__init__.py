"""
Generator of a calendar ready for printing and bookbinding.

Book layout: every spread has a week of days on the LEFT page and a blank page for
notes on the RIGHT page. Pages are imposed two per A4-landscape sheet side
(duplex, flipped on the short edge), and grouped into signatures that are folded in half and bound.
"""
import datetime as dt
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
OUTPUT_DIR = PACKAGE_DIR / "output"

# Constants
YEAR = 2026
SHEETS_PER_SIGNATURE = 5  # one sheet = one A4 folded in half = 4 book pages

DAYS_CZ = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]
DAYS_CZ_SHORT = ["PO", "ÚT", "ST", "ČT", "PÁ", "SO", "NE"]
MONTHS_CZ = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září", "říjen", "listopad", "prosinec"]

# CSS selectors of the text elements whose font can be overridden
FONT_TARGETS = {
    "number": ".number-block-number-font-editable",  # day numbers
    "day": ".day-cz-font-editable",                  # weekday names
    "month": ".header-text-font-editable",           # month header
}

# thickness overrides (in mm) accepted for the lines on each day
LINE_NAMES = ("header", "row", "mid", "q1", "q3")
LINE_STYLES = ("solid", "dotted", "dashed", "none")
# layout overrides (in mm): height of a day, height of a day on the month overview pages, gap left of the day area, and how far lines stretch right (to the fold by default)
LAYOUT_NAMES = ("row-height", "overview-row-height", "margin-left", "extend-right")

_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
WRAPPER_TEMPLATE = _jinja_env.get_template("wrapper.jinja")
PAGE_TEMPLATE = _jinja_env.get_template("week.jinja")


# ---------------------------------------------------------------- content ----

def generate_weeks(year):
    """
    Monday-Sunday weeks covering the whole year. The first and last week are
    completed with days of the neighbouring years.
    """
    first, last = dt.date(year, 1, 1), dt.date(year, 12, 31)
    current = first - dt.timedelta(days=first.weekday())
    end = last + dt.timedelta(days=6 - last.weekday())

    weeks = []
    while current <= end:
        weeks.append([current + dt.timedelta(days=i) for i in range(7)])
        current += dt.timedelta(days=7)
    return weeks


def week_header(week):
    """'LEDEN 2026', 'LEDEN/ÚNOR 2026' or 'PROSINEC 2025 / LEDEN 2026' (month order = calendar order)."""
    months = list(dict.fromkeys((d.year, d.month) for d in week))
    if len({y for y, _ in months}) > 1:
        return " / ".join(f"{MONTHS_CZ[m - 1]} {y}" for y, m in months)
    return "/".join(MONTHS_CZ[m - 1] for _, m in months) + f" {months[0][0]}"


def blank_page():
    return {"kind": "blank", "header": "", "days": [], "info": ""}


def week_page(week):
    return {
        "kind": "week",
        "header": week_header(week),
        "days": [{"day_number": d.day, "day_cz": DAYS_CZ[d.weekday()]} for d in week],
        "info": "",
    }


def month_overview_pages(year):
    """
    Month overview pages, three months (columns) per page: Jan-Mar, Apr-Jun, Jul-Sep, Oct-Dec.
    Each column lists the days of the month, one row per day with the day number and weekday abbreviation.
    """
    columns = []
    for month in range(1, 13):
        first = dt.date(year, month, 1)
        days, current = [], first
        while current.month == month:
            days.append({"day_number": current.day, "day_abbr": DAYS_CZ_SHORT[current.weekday()]})
            current += dt.timedelta(days=1)
        columns.append({"header": MONTHS_CZ[month - 1], "days": days})
    return [
        {"kind": "months", "header": "", "days": [], "months": columns[i:i + 3], "info": ""}
        for i in range(0, 12, 3)
    ]


def build_book_pages(year, overview=True):
    """
    Book pages in reading order. Page 1 is the right-hand page opening the
    book. With overview pages, pages 2-5 are the two month-overview spreads
    (Jan-Mar | Apr-Jun, Jul-Sep | Oct-Dec) and the first week lands on page 6;
    without them it lands on page 2. Either way weeks sit on even (left)
    pages with their notes on the following odd (right) page.
    """
    pages = [blank_page()]
    if overview:
        pages.extend(month_overview_pages(year))
    for week in generate_weeks(year):
        pages.append(week_page(week))
        pages.append(blank_page())  # notes page: intentionally empty
    return pages


# ------------------------------------------------------------- imposition ----

def impose_signature(pages):
    """
    Order the pages of one signature (a multiple of 4) as printed sheet sides.
    Returns (left, right) pairs: front of sheet 1, back of sheet 1, front of sheet 2...
    Nested sheets: the outermost sheet carries first and last pages.
    """
    n = len(pages)
    assert n % 4 == 0, "a signature must have a multiple of 4 pages"
    sides = []
    for i in range(n // 4):
        sides.append((pages[n - 1 - 2 * i], pages[2 * i]))      # front
        sides.append((pages[2 * i + 1], pages[n - 2 - 2 * i]))  # back
    return sides


def build_sheet_sides(year=YEAR, sheets_per_signature=SHEETS_PER_SIGNATURE, overview=True):
    """All (left, right) sheet sides, in print order, with binder metadata on each page."""
    pages = build_book_pages(year, overview)
    per_sig = sheets_per_signature * 4

    # pad with blanks so every signature is complete
    while len(pages) % per_sig:
        pages.append(blank_page())

    for number, page in enumerate(pages, start=1):
        page["book_page"] = number
        page["signature"] = (number - 1) // per_sig + 1
        if page["kind"] != "blank":
            page["info"] = f"S{page['signature']} P{number}"

    sides = []
    for start in range(0, len(pages), per_sig):
        sides.extend(impose_signature(pages[start:start + per_sig]))
    return sides


# ----------------------------------------------------------------- render ----

def render_pages_as_single_document(sides, year, show_page_info=True, fonts=None, lines=None, line_styles=None, layout=None):
    content = ""
    for left, right in sides:
        rendered = []
        for page in (left, right):
            rendered.append(PAGE_TEMPLATE.render(
                kind=page["kind"], header=page["header"], days=page["days"], months=page.get("months", []),
                year=year, info=page["info"] if show_page_info else ""))
        content += f'<div class="sheet-side"><div class="half">{rendered[0]}</div><div class="half">{rendered[1]}</div></div>\n'
    return WRAPPER_TEMPLATE.render(
        content=content,
        font_rules=[(FONT_TARGETS[k], family) for k, family in (fonts or {}).items() if family],
        line_vars=[(k, float(v)) for k, v in (lines or {}).items() if k in LINE_NAMES and v is not None],
        layout_vars=[(k, float(v)) for k, v in (layout or {}).items() if k in LAYOUT_NAMES and v is not None],
        line_style_vars=[(k, v) for k, v in (line_styles or {}).items() if k in LINE_NAMES and v in LINE_STYLES],
    )


def render_year_html(year=YEAR, sheets_per_signature=SHEETS_PER_SIGNATURE, show_page_info=True, fonts=None, lines=None, line_styles=None, layout=None, overview=True):
    """overview: include the month overview pages at the front of the book.
    layout: optional {name: mm} for the keys of LAYOUT_NAMES.
    line_styles: optional {name: border style} for the same keys, values from LINE_STYLES.
    lines: optional {name: thickness in mm} for the keys of LINE_NAMES
    (header = line under the month header, row = solid line under a day, mid = dotted middle line, q1/q3 = thin dividers at 1/4 and 3/4).
    fonts: optional {target: Google Fonts family} overriding the stylesheet defaults;
    targets are the keys of FONT_TARGETS ('number', 'day', 'month')."""
    return render_pages_as_single_document(
        build_sheet_sides(year, sheets_per_signature, overview), year, show_page_info, fonts, lines, line_styles, layout)


def get_css_path():
    return str(TEMPLATES_DIR / "style.css")


def copy_css_to_output():
    (OUTPUT_DIR / "html" / "style.css").write_text((TEMPLATES_DIR / "style.css").read_text())


def output_html_to_file(html_content, filename, sheets_per_signature):
    (OUTPUT_DIR / "html" / f"{filename}_{sheets_per_signature}s.html").write_text(html_content)


def render_html_to_pdf_and_output(html_content, filename, sheets_per_signature):
    from weasyprint import HTML  # heavy native deps, only needed for PDF output
    HTML(string=html_content).write_pdf(
        str(OUTPUT_DIR / "pdf" / f"{filename}_{sheets_per_signature}s.pdf"),
        pdf_variant="pdf/x-3", stylesheets=[get_css_path()])


def main():
    (OUTPUT_DIR / "html").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "pdf").mkdir(parents=True, exist_ok=True)
    copy_css_to_output()
    html = render_year_html()
    output_html_to_file(html, filename="full_year_signatures", sheets_per_signature=SHEETS_PER_SIGNATURE)
    #render_html_to_pdf_and_output(html, filename="full_year_signatures", sheets_per_signature=SHEETS_PER_SIGNATURE)


if __name__ == "__main__":
    main()
