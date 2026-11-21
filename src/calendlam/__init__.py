from jinja2 import Environment, FileSystemLoader
import datetime as dt
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
OUTPUT_DIR = PACKAGE_DIR / "output"

# generate data structure for year
def generate_months_for_full_year(months_cz, months_en, days_cz, days_en, year):
    """
    Generate a data structure for a full year of a calendar.
    """
    year_start, year_end = dt.date(year, 1, 1), dt.date(year, 12, 31)
    months = []
    current_date = year_start
    while(current_date <= year_end):
        month = {
            "name_cz": months_cz[current_date.month - 1],
            "name_en": months_en[current_date.month - 1],
            "weeks": []
        }

        this_month = current_date.month
        while(current_date.month == this_month and current_date <= year_end):
            week = []
            for _ in range(7):
                week.append({
                    "date": current_date,
                    "day_number": current_date.day,
                    "day_cz": days_cz[current_date.weekday()],
                    "day_en": days_en[current_date.weekday()],
                })
                current_date += dt.timedelta(days=1)
                if(current_date.month != this_month or current_date == year_end):
                    break

            month["weeks"].append(week)

        months.append(month)

    return months


def print_and_dump(months, name):
    print(months)
    import json
    with open(OUTPUT_DIR / f'dump_{name}.json', 'w') as f:
        json.dump(months, f, default=str, indent=4, ensure_ascii=False)


# render and print pages
def load_template(template_name):
    jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = jinja_env.get_template(template_name)

    return template

def get_css_path():
    return str(TEMPLATES_DIR / "style.css")

def copy_css_to_output():
    css_in_path = TEMPLATES_DIR / "style.css"
    css_out_path = OUTPUT_DIR / "html" / "style.css"

    with open(css_in_path, "r") as f:
        style_css = f.read()
    with open(css_out_path, "w") as f:
        f.write(style_css)



def render_pages_as_single_document(pages, year):
    all_pages_content = ""
    for page in pages:
        templated_week = DOUBLEPAGE_TEMPLATE.render(
            days=page['days'], 
            month=page['month'], 
            year=year,
            signature_number=page['_meta_signature_number'],
            global_page_number=page['_meta_global_page_number'],
            page_in_signature_number=page['_meta_page_in_signature_number']
        )
        all_pages_content += templated_week

    full_page = WRAPPER_TEMPLATE.render(content=all_pages_content)

    return full_page

def output_html_to_file(html_content, filename, sheets_per_signature):
    with open(OUTPUT_DIR / "html" / f"{filename}_{sheets_per_signature}s.html", "w") as f:
        f.write(html_content)

def render_html_to_pdf_and_output(html_content, filename, sheets_per_signature):
    from weasyprint import HTML  # heavy native deps, only needed for PDF output
    style_path = get_css_path()
    HTML(string=html_content) \
        .write_pdf(str(OUTPUT_DIR / "pdf" / f"{filename}_{sheets_per_signature}s.pdf"), pdf_variant="pdf/x-3", stylesheets=[style_path])


def generate_page():
    page = {
        "month" : { "name_cz" : "", "name_en": ""},
        "days" : [],
        "empty" : False,

        "_meta_signature_number": None,
        "_meta_page_in_signature_number": None,
        "_meta_global_page_number": None
    }
    return page

def months_to_pages(months):
    """
    Convert months structure into a linear list of printable pages of 7 days with metadata.
    """
    # generate a flat array of all days
    all_days = []
    for month in months:
        if 'weeks' not in month:
            print(month)
            raise Exception("weeks not in month")

        for week in month['weeks']:
            for day in week:
                day["_month"] = { "name_cz" : month['name_cz'], "name_en" : month['name_en'] }
                all_days.append(day)


    # split to chunks of seven days
    paged_days = [ all_days[start:start+7] for start in range(0, len(all_days) ,7)]


    # add page metadata to each page
    pages = []
    for page_of_days in paged_days:
        i_page = generate_page()
        i_page['days'] = page_of_days

        month_names_cz = [ day['_month']['name_cz'] for day in i_page['days'] ]
        month_names_en = [ day['_month']['name_en'] for day in i_page['days'] ]

        unique_months_cz = dict.fromkeys(month_names_cz)
        unique_months_en = dict.fromkeys(month_names_en)

        i_page['month']['name_cz'] = "/".join(unique_months_cz)
        i_page['month']['name_en'] = "/".join(unique_months_en)

        pages.append(i_page)

    return pages

def rearrange_pages_in_signature(pages : list, singature_metadata_number : int):
    """
    Rearrange pages so that they are in the correct sequence for double-sided printing and grouping in bookbinding signatures.
    Print of A4, folded and bound to A5.
    """
    signature_pages = []
    if(len(pages) % 2 != 0):
        raise Exception(f"pages count must be even. Was : {len(pages)}")

    for i in range(0, len(pages)//2):
        idx_first, idx_last = i, len(pages) - 1 - i
        page_first, page_last = pages[idx_first], pages[idx_last]

        signature_pages.append(pages[idx_first])
        signature_pages.append(pages[idx_last])

        #add metadata to pages
        page_first['_meta_signature_number'] = singature_metadata_number
        page_last['_meta_signature_number'] = singature_metadata_number
        page_first['_meta_page_in_signature_number'] = idx_first
        page_last['_meta_page_in_signature_number'] = idx_last

    return signature_pages

def rearrange_pages_for_printing(sheets_per_signature : int, pages : list):
    """
    Rearrange pages so that signatures can be bound together.
    We want to group pages into signatures so that when folded and bound, they read correctly.

    @param sheets_per_signature how many sheets of paper will be folded and bound together
    """
    pages = [page for page in pages]

    # two pages per sheet
    pages_per_signature = sheets_per_signature * 2

    # pad the end of the year with empty pages so that all signatures have the same number of pages
    empty_pages = pages_per_signature - (len(pages) % pages_per_signature)
    if (empty_pages):
        for i in range(0,empty_pages):
            page = generate_page()
            page['empty'] = True
            pages.append(page)

    for i, page in enumerate(pages):
        page['_meta_global_page_number'] = i


    print(f"num pages to generate: {len(pages)}")

    meta_signature_num = 0 # for the person doing the binding to keep track of pages when printed out
    for i in range(0, len(pages), pages_per_signature):
        signature_pages = pages[i:i+pages_per_signature]
        signature_pages = rearrange_pages_in_signature(signature_pages, meta_signature_num)
        pages[i:i+pages_per_signature] = signature_pages
        meta_signature_num += 1

    return pages
    
"""
Generator of a calendar ready for printing and bookbinding,
printed in double-sided format and folded together into signatures.
"""

# Constants
YEAR = 2026
SHEETS_PER_SIGNATURE = 5

DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAYS_CZ = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]
MONTHS_EN = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
MONTHS_CZ = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září", "říjen", "listopad", "prosinec"]

WRAPPER_TEMPLATE = load_template("wrapper.jinja")
# template for a A4 page with ("double means" two A5 pages are rendered in a single A4-sized template page)
DOUBLEPAGE_TEMPLATE = load_template("week.jinja")


def build_pages(year=YEAR, sheets_per_signature=SHEETS_PER_SIGNATURE):
    """Generate all pages for the year, rearranged for double-sided printing."""
    months = generate_months_for_full_year(MONTHS_CZ, MONTHS_EN, DAYS_CZ, DAYS_EN, year)
    pages = months_to_pages(months)
    return rearrange_pages_for_printing(sheets_per_signature=sheets_per_signature, pages=pages)


def render_year_html(year=YEAR, sheets_per_signature=SHEETS_PER_SIGNATURE):
    return render_pages_as_single_document(build_pages(year, sheets_per_signature), year)


def main():
    (OUTPUT_DIR / "html").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "pdf").mkdir(parents=True, exist_ok=True)
    copy_css_to_output()
    html = render_year_html()
    output_html_to_file(html, filename="full_year_signatures", sheets_per_signature=SHEETS_PER_SIGNATURE)
    #render_html_to_pdf_and_output(html, filename="full_year_signatures", sheets_per_signature=SHEETS_PER_SIGNATURE)


if __name__ == "__main__":
    main()
