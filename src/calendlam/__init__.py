from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import datetime as dt
import os

# generate data structure for year
def generate_data_structure_for_full_year(months_cz, months_en, days_cz, days_en):
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


def print_and_dump(months):
    print(months)
    import json
    with open('output/data.json', 'w') as f:
        json.dump(months, f, default=str, indent=4)
    exit(0)

#print_and_dump(months)

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
            templated_week = week_template.render(days=page, month=month, year = 2026)
            templated_page = wrapper_template.render(content=templated_week)
            
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

def output_as_single_page(months):
    all_pages_content = ""
    for month_number, month in enumerate(months):
        for week_number_in_month, page in enumerate(month["weeks"]):
            print(page)

            # render templates with variables
            templated_week = week_template.render(days=page, month=month, year = 2026)
            all_pages_content += templated_week

    full_page = wrapper_template.render(content=all_pages_content)

    with open(f"output/html/full_year.html", "w") as f:
        f.write(full_page)


def output_signatures_as_single_page(signatures):
    """
    Output all signatures as a single HTML page.
    
    Args:
        signatures: List of signatures from generate_signatures_for_a5_print()
    """
    all_pages_content = ""
    global_a4_sheet_counter = 0  # Track A4 sheets across all signatures
    
    for signature_number, signature in enumerate(signatures):
        # Calculate A4 sheet range for this signature
        # Each signature has pages_per_signature physical pages = pages_per_signature A4 sheets
        # (since each physical page = 1 A4 sheet when printed double-sided)
        pages_per_signature = len(signature) // 2  # Each physical page = 2 sides
        signature_start_a4 = global_a4_sheet_counter + 1
        signature_end_a4 = global_a4_sheet_counter + pages_per_signature
        
        # Page numbers restart for each signature
        # Each physical page has 2 sides (left and right), so divide by 2
        for side_number, page in enumerate(signature):
            # Calculate physical page number (0-based): each physical page = 2 sides
            # side_number 0,1 -> page 0; side_number 2,3 -> page 1; etc.
            physical_page_number_0based = side_number // 2
            
            # Calculate A4 sheet number within this signature
            # Each pair of consecutive pages in signature = 1 A4 sheet
            # Pages are in bookbinding order, so side_number 0,1 = A4 sheet 1, etc.
            a4_sheet_in_signature = (side_number // 2) + 1  # 1-based within signature
            a4_sheet_global = global_a4_sheet_counter + a4_sheet_in_signature
            
            if page['is_left']:
                # Render left page with week content
                templated_week = week_template.render(
                    days=page['days'], 
                    month=page['month'], 
                    year=page['year'],
                    signature_number=signature_number,
                    page_number=physical_page_number_0based,  # 0-based, template adds 1 for display
                    a4_sheet_number=a4_sheet_global,
                    signature_a4_range=f"{signature_start_a4}-{signature_end_a4}"
                )
                all_pages_content += templated_week
            else:
                # Render empty right page with page info
                # Template adds 1, so physical_page_number_0based + 1 = actual page number
                empty_page = f"""<div id="page">
    <div class="page-info rubik-regular">
        S{signature_number + 1} P{physical_page_number_0based + 1} A4:{a4_sheet_global} (S{signature_number + 1}: A4 {signature_start_a4}-{signature_end_a4})
    </div>
</div>"""
                all_pages_content += empty_page
        
        # Update global counter after processing all pages in this signature
        global_a4_sheet_counter += pages_per_signature
    
    full_page = wrapper_template.render(content=all_pages_content)
    
    with open("output/html/full_year_signatures.html", "w") as f:
        f.write(full_page)


def generate_signatures_for_a5_print(months, pages_per_signature=5):
    """
    input: months in the structure generated by generate_data_structure_for_full_year()
    output: list of signatures, where each signature is a list of page data dicts

    Generate signatures for A5 print with the following constraints:
    - a "signature" in this context is a set of pages that are sewn together for bookbinding
    - the week lines are on the left of a double page, the right side is empty
    - the weeks start on the first double page
    - the calendar is double-sided, so the first page of a signature is the left page of a double page
    
    Each page data dict contains:
    - 'is_left': bool - True if left page (with week content), False if right page (empty)
    - 'days': list - week data (only present if is_left is True) - matches template expectation
    - 'month': dict - month data (only present if is_left is True)
    - 'year': int - year (only present if is_left is True)
    
    For left pages, the dict can be passed directly to week_template.render() as:
        week_template.render(days=page['days'], month=page['month'], year=page['year'])
    
    For right pages (is_left=False), these are empty and should be skipped or handled separately.
    """
    # Flatten all weeks from all months with their context
    all_weeks = []
    for month in months:
        for week in month["weeks"]:
            all_weeks.append({
                "days": week,  # Use 'days' to match template expectation
                "month": month,
                "year": 2026
            })
    
    # Calculate total number of physical pages needed
    # Each week takes one left page, and each left page has a corresponding empty right page
    total_weeks = len(all_weeks)
    total_physical_pages = total_weeks  # One physical page per week (left side only)
    
    # Group pages into signatures
    signatures = []
    week_index = 0
    
    while week_index < total_weeks:
        signature = []
        pages_in_signature = 0
        
        # Create pages for this signature
        while pages_in_signature < pages_per_signature and week_index < total_weeks:
            # Add left page with week content (using 'days' to match template)
            signature.append({
                "is_left": True,
                "days": all_weeks[week_index]["days"],
                "month": all_weeks[week_index]["month"],
                "year": all_weeks[week_index]["year"]
            })
            
            # Add right page (empty)
            signature.append({
                "is_left": False
            })
            
            week_index += 1
            pages_in_signature += 1
        
        # Arrange pages in bookbinding order for printing
        # For a signature with N pages (2N sides), the print order is:
        # [2N, 1, 2, 2N-1, 2N-2, 3, 4, 2N-3, 2N-4, 5, ...]
        arranged_signature = _arrange_pages_for_bookbinding(signature)
        signatures.append(arranged_signature)
    
    return signatures


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

# init dates
year_start = dt.date(2026, 1, 1)
year_end = dt.date(2026, 12, 31)


# define day and month names
days_en = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
days_cz = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]
months_en = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
months_cz = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září", "říjen", "listopad", "prosinec"]

wrapper_template = load_template("wrapper.jinja")
week_template = load_template("week.jinja")
# copy style.css to output/html
copy_css_to_output()

months = generate_data_structure_for_full_year(months_cz, months_en, days_cz, days_en)

signatures = generate_signatures_for_a5_print(months, pages_per_signature=5)

#output_as_separate_pages(months)
#output_as_single_page(months)
output_signatures_as_single_page(signatures)