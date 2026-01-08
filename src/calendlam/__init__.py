from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import datetime as dt
import os

# generate data structure for year
def generate_months_for_full_year(months_cz, months_en, days_cz, days_en):
    months = []
    current_date = YEAR_START
    while(current_date <= YEAR_END):
        month = {
            "name_cz": months_cz[current_date.month - 1],
            "name_en": months_en[current_date.month - 1],
            "weeks": []
        }

        this_month = current_date.month
        while(current_date.month == this_month and current_date <= YEAR_END):
            week = []
            for _ in range(7):
                week.append({
                    "date": current_date,
                    "day_number": current_date.day,
                    "day_cz": days_cz[current_date.weekday()],
                    "day_en": days_en[current_date.weekday()],
                })
                current_date += dt.timedelta(days=1)
                if(current_date.month != this_month or current_date == YEAR_END):
                    break

            month["weeks"].append(week)

        months.append(month)

    return months


def print_and_dump(months):
    print(months)
    import json
    with open('output/data.json', 'w') as f:
        json.dump(months, f, default=str, indent=4)
    exit(0)


# render and print pages
def load_template(template_name):
    jinja_env = Environment(loader=FileSystemLoader("templates"))
    template = jinja_env.get_template(template_name)

    return template

def copy_css_to_output():
    with open("templates/style.css", "r") as f:
        style_css = f.read()
    with open("output/html/style.css", "w") as f:
        f.write(style_css)

def output_as_separate_pages(months):
    for month_number, month in enumerate(months):
        for week_number_in_month, page in enumerate(month["weeks"]):
            print(page)

            # render templates with variables
            templated_week = WEEK_TEMPLATE.render(days=page, month=month, year = YEAR)
            templated_page = WRAPPER_TEMPLATE.render(content=templated_week)
            
            # define output filename based on month and week number
            filename = f"page_{month_number+1:03d}_{week_number_in_month+1:03d}"

            # create output directories if they don't exist
            from pathlib import Path
            dir = Path("output/html/")
            dir.mkdir(parents=True, exist_ok=True)
            dir = Path("output/pdf/")
            dir.mkdir(parents=True, exist_ok=True)



            with open(f"output/html/{filename}.html", "w") as f:
                f.write(templated_page)

            style_path = os.path.join("templates", "style.css")
            HTML(string=templated_page) \
            .write_pdf(f"output/pdf/{filename}.pdf", pdf_variant="pdf/x-3", stylesheets=[style_path])


def output_signatures_as_single_page(signatures):
    """
    Output all signatures as a single HTML page.
    
    Args:
        signatures: List of signatures from generate_signatures_for_a5_print()
    """
    all_pages_content = ""
    global_a4_side_counter = 0  # Track A4 sheet sides across all signatures
    
    for signature_number, signature in enumerate(signatures):
        # Each div id="page" = 1 A4 sheet side when printed
        # When printing double-sided, 2 consecutive div id="page" = 1 A4 sheet (front + back)
        # Calculate A4 sheet range for this signature
        num_weeks_in_signature = len(signature)  # Each week = 1 A4 sheet side
        num_a4_sheets_in_signature = (num_weeks_in_signature + 1) // 2  # 2 sides = 1 A4 sheet
        signature_start_a4 = (global_a4_side_counter // 2) + 1  # A4 sheet number (1-based)
        signature_end_a4 = ((global_a4_side_counter + num_weeks_in_signature - 1) // 2) + 1
        
        # Render each week (each week = 1 div id="page" = 1 A4 sheet side)
        for week_index, week_data in enumerate(signature):
            # Calculate physical page number within signature (0-based)
            # Each pair of weeks = 1 physical page in the book
            physical_page_number_0based = week_index // 2
            
            # Calculate A4 sheet side number (each div id="page" = 1 A4 sheet side)
            a4_side_number = global_a4_side_counter + 1  # 1-based
            # Calculate A4 sheet number (2 sides = 1 A4 sheet)
            a4_sheet_number = (global_a4_side_counter // 2) + 1  # 1-based
            
            # Render week - each week.jinja render = 1 div id="page" = 1 A4 sheet side
            templated_week = WEEK_TEMPLATE.render(
                days=week_data['days'], 
                month=week_data['month'], 
                year=week_data['year'],
                signature_number=signature_number,
                page_number=physical_page_number_0based,  # 0-based, template adds 1 for display
                a4_sheet_number=a4_sheet_number,
                a4_side_number=a4_side_number,
                signature_a4_range=f"{signature_start_a4}-{signature_end_a4}"
            )
            all_pages_content += templated_week
            
            global_a4_side_counter += 1
    
    full_page = WRAPPER_TEMPLATE.render(content=all_pages_content)
    
    with open("output/html/full_year_signatures.html", "w") as f:
        f.write(full_page)


def generate_signatures_for_a5_print(months, pages_per_signature=5):
    """
    input: months in the structure generated by generate_months_for_full_year()
    output: list of signatures, where each signature is a list of week data dicts

    Generate signatures for A5 print with double-sided printing:
    - Each week = 1 A4 sheet side (1 div id="page")
    - Calendar is double-sided: each A4 sheet has 2 weeks (front + back)
    - Weeks are arranged in bookbinding order so they pair correctly when printed
    
    Each page data dict contains:
    - 'days': list - week data - matches template expectation
    - 'month': dict - month data
    - 'year': int - year
    
    The dict can be passed directly to WEEK_TEMPLATE.render() as:
        WEEK_TEMPLATE.render(days=page['days'], month=page['month'], year=page['year'])
    """
    # Flatten all weeks from all months with their context
    all_weeks = []
    for month in months:
        for week in month["weeks"]:
            all_weeks.append({
                "days": week,  # Use 'days' to match template expectation
                "month": month,
                "year": YEAR
            })
    
    # Group weeks into signatures
    signatures = []
    week_index = 0
    
    while week_index < len(all_weeks):
        # Collect weeks for this signature
        signature_weeks = []
        while len(signature_weeks) < pages_per_signature and week_index < len(all_weeks):
            signature_weeks.append(all_weeks[week_index])
            week_index += 1
        
        # Arrange weeks in bookbinding order for double-sided printing
        # For N weeks, arrange as: [N, 1, 2, N-1, N-2, 3, 4, N-3, ...]
        # This pairs weeks so that when printed double-sided:
        # Sheet 1: Week N (front), Week 1 (back)
        # Sheet 2: Week 2 (front), Week N-1 (back)
        # etc.
        arranged_signature = _arrange_weeks_for_bookbinding(signature_weeks)
        signatures.append(arranged_signature)
    
    return signatures


def _arrange_weeks_for_bookbinding(weeks):
    """
    Arrange weeks in bookbinding order for double-sided printing.
    
    For N weeks, arrange them so that when printed double-sided, they pair correctly:
    - Sheet 1: Week N (front), Week 1 (back)
    - Sheet 2: Week 2 (front), Week N-1 (back)
    - Sheet 3: Week N-2 (front), Week 3 (back)
    - etc.
    
    This creates the pattern: [N, 1, 2, N-1, N-2, 3, 4, N-3, ...]
    
    Args:
        weeks: List of week data dicts in reading order (index 0 = first week, etc.)
        
    Returns:
        List of week data dicts in print order
    """
    num_weeks = len(weeks)
    if num_weeks == 0:
        return []
    
    arranged = []
    num_sheets = (num_weeks + 1) // 2  # Number of A4 sheets needed
    
    # Arrange weeks following bookbinding pattern
    for i in range(num_sheets):
        # Index from the start (working forwards: 0, 1, 2, ...)
        start_index = i
        # Index from the end (working backwards: N-1, N-2, N-3, ...)
        end_index = num_weeks - 1 - i
        
        if i % 2 == 0:
            # Even sheets: end week, then start week
            # This pairs: Week N with Week 1, Week N-2 with Week 3, etc.
            if end_index >= 0 and end_index < num_weeks:
                arranged.append(weeks[end_index])
            if start_index < num_weeks and start_index != end_index:
                arranged.append(weeks[start_index])
        else:
            # Odd sheets: start week, then end week
            # This pairs: Week 2 with Week N-1, Week 4 with Week N-3, etc.
            if start_index < num_weeks:
                arranged.append(weeks[start_index])
            if end_index >= 0 and end_index < num_weeks and start_index != end_index:
                arranged.append(weeks[end_index])
    
    return arranged


def _arrange_pages_for_bookbinding(pages):
    """
    Arrange pages in bookbinding order for double-sided printing.
    
    For a signature with N physical pages (2N sides), pages need to be arranged
    so that when printed double-sided, folded, and bound, they read correctly.
    
    The standard bookbinding arrangement pairs pages so that when folded:
    - Page 1 (index 0) pairs with page 2N (index 2N-1)
    - Page 2 (index 1) pairs with page 2N-1 (index 2N-2)
    - Page 3 (index 2) pairs with page 2N-2 (index 2N-3)
    - And so on...
    
    For printing, each sheet contains two sides. The print order is:
    - Sheet 0: [2N-1, 0] = [last, first]
    - Sheet 1: [1, 2N-2] = [second, second-to-last]
    - Sheet 2: [2N-3, 2] = [third-to-last, third]
    - Sheet 3: [3, 2N-4] = [fourth, fourth-to-last]
    - And so on...
    
    Args:
        pages: List of page data dicts in reading order (index 0 = first page, etc.)
        
    Returns:
        List of page data dicts in print order
    """
    num_pages = len(pages)
    if num_pages == 0:
        return []
    
    # For bookbinding, we arrange pages so that when folded, they read correctly
    arranged = []
    
    # Calculate how many sheets we have (each sheet has 2 sides)
    num_sheets = num_pages // 2
    
    # Arrange pages following bookbinding pattern
    # For each sheet i (0-indexed), pair page i with page (num_pages - 1 - i)
    for i in range(num_sheets):
        # Index from the start (working forwards: 0, 1, 2, ...)
        start_index = i
        # Index from the end (working backwards: 2N-1, 2N-2, 2N-3, ...)
        end_index = num_pages - 1 - i
        
        if i % 2 == 0:
            # Even sheets: end page, then start page
            if end_index >= 0 and end_index < num_pages:
                arranged.append(pages[end_index])
            if start_index < num_pages:
                arranged.append(pages[start_index])
        else:
            # Odd sheets: start page, then end page
            if start_index < num_pages:
                arranged.append(pages[start_index])
            if end_index >= 0 and end_index < num_pages:
                arranged.append(pages[end_index])
    
    return arranged

# Constants
YEAR = 2026
YEAR_START = dt.date(YEAR, 1, 1)
YEAR_END = dt.date(YEAR, 12, 31)


DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAYS_CZ = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]
MONTHS_EN = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
MONTHS_CZ = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září", "říjen", "listopad", "prosinec"]

WRAPPER_TEMPLATE = load_template("wrapper.jinja")
WEEK_TEMPLATE = load_template("week.jinja")
# copy style.css to output/html
copy_css_to_output()

months = generate_months_for_full_year(MONTHS_CZ, MONTHS_EN, DAYS_CZ, DAYS_EN)


def months_to_pages(months):
    page = {
        "month" : { "name_cz" : "", "name_en": ""},
        "days" : [],
        "signature_number": None,
        "page_in_signature_number": None,
        "empty" : False
    }

    # generate a flat array of all days
    all_days = []
    for month in months:
        for week in month.weeks:
            for day in week:
                day["_month"] = { "name_cz" : month.name_cz, "name_en" : month.name_en }
                all_days.append(day)

    # split to chunks of seven days
    paged_days = [ all_days[start:start+7] for start in range(0, len(all_days) ,7)]

    # add page metadata to each page
    pages = []
    for page_of_days in paged_days:
        i_page = page
        i_page.days = page_of_days

        month_names_cz = [ day.name_cz for day in i_page.days ]
        month_names_en = [ day.name_en for day in i_page.days ]

        unique_months_cz = set(month_names_cz)
        unique_months_en = set(month_names_en)

        i_page.month.name_cz = unique_months_cz.join(" / ")
        i_page.month.name_en = unique_months_en.join(" / ")

        pages.append(i_page)

    return pages


def pages_to_signatures(sheets_per_signature : int, pages : list):
    """
    Rearrange pages so that they are in the correct sequence for
    double-sided printing and grouping in bookbinding signatures.

    @param sheets_per_signature how many sheets of paper will be folded and bound together
    """
    pages = pages

    # two pages per sheet
    pages_per_signature = sheets_per_signature * 2

    # pad with empty pages
    empty_pages = pages_per_signature - (len(pages) % pages_per_signature)
    if (empty_pages):
        for i in range(0,empty_pages):
            page = page
            page.empty = True
            pages.append(page)

    # @TODO: write correct print grouping here



# signatures = generate_signatures_for_a5_print(months, pages_per_signature=5)





#output_as_separate_pages(months)
#output_as_single_page(months)
output_signatures_as_single_page(signatures)