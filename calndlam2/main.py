"""
This is a calendar generator application

I will output a calendar ready for bookbinding.
It will print as two A5 pages side by side in landscape mode.
Will be printed double-sided on A4 paper and then folded in half.

The pages will be grouped in "signatures" which will then be bound together.

The output of this application will be a HTML file containing all pages styled with CSS
using Jinja2 templates.

"""
from dataclasses import dataclass
import datetime


YEAR = 2026

DAY_NAMES = {
    'en': ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
}

MONTH_NAMES = {
    'en': ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
}


@dataclass
class Day:
    date: datetime.date

@dataclass
class Page:
    days: list[Day]
    signature_number: int
    number_in_signature: int #position of page in signature

@dataclass
class Signature:
    pages: list[Page]
    signature_number: int

def generate_days():
    """
    Generate a list of days for the given year
    """
    days = []
    start_date = datetime.date(YEAR, 1, 1)
    end_date = datetime.date(YEAR, 12, 31)
    current_date = start_date
    
    while current_date <= end_date:
        days.append(Day(date=current_date))
        current_date += datetime.timedelta(days=1)
    
    return days

def add_page_metadata_to_days(days: list[Day]) -> list[Page]:
    """
    Create pages with days
    Each page contains 7 days (one week)
    Each page with days is followed by an empty page for bookbinding
    """
    pages = []
    DAYS_PER_PAGE = 7
    
    for i in range(0, len(days), DAYS_PER_PAGE):
        page_days = days[i:i + DAYS_PER_PAGE]
        # Signature and number_in_signature will be set later
        page = Page(
            days=page_days,
            signature_number=0,
            number_in_signature=0
        )
        pages.append(page)
        
        # Add empty page after each page with days
        empty_page = Page(
            days=[],
            signature_number=0,
            number_in_signature=0
        )
        pages.append(empty_page)
    
    return pages

def rearrange_pages_into_signatures(pages: list[Page]) -> list[Page]:
    """
    rearrange pages for printing so that pages are in correct order for binding into signatures

    Example:
    original order: [1, empty, 2, empty, 3, empty, 4, empty, 5, empty, 6, empty]
    new order: [1, empty, 6, empty, 2, empty, 5, empty, 3, empty, 4, empty]
    
    For bookbinding, pages are arranged so that when folded and bound,
    they appear in the correct order. Each signature typically contains
    a multiple of 4 pages (4, 8, 12, 16, etc.) for proper folding.
    
    The pattern [1,6,2,5,3,4] ensures that when printed double-sided and folded,
    pages with days appear on the left and empty pages on the right.
    """
    SIGNATURE_SIZE = 8  # 8 pages per signature (4 sheets, double-sided)
    rearranged_pages = []
    
    # Group pages into signatures
    for sig_start in range(0, len(pages), SIGNATURE_SIZE):
        sig_pages = pages[sig_start:sig_start + SIGNATURE_SIZE]
        
        # Rearrange pages within signature for bookbinding
        # Pattern: first, last, second, second-to-last, etc.
        # This ensures days on left, empty on right when bound
        rearranged_sig = []
        left = 0
        right = len(sig_pages) - 1
        
        while left <= right:
            if left == right:
                rearranged_sig.append(sig_pages[left])
            else:
                rearranged_sig.append(sig_pages[left])
                rearranged_sig.append(sig_pages[right])
            left += 1
            right -= 1
        
        # Update page metadata with signature information
        for idx, page in enumerate(rearranged_sig):
            page.signature_number = sig_start // SIGNATURE_SIZE + 1
            page.number_in_signature = idx + 1
        
        rearranged_pages.extend(rearranged_sig)
    
    return rearranged_pages

def generate_html(signatures: list[Signature]) -> str:
    """
    Generate an HTML file containing all pages styled with CSS
    Two A5 pages side by side in landscape mode for printing on A4
    """
    html_parts = []
    
    # HTML header with CSS
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calendar {}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 0;
        }}
        
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: white;
        }}
        
        .page-spread {{
            width: 297mm;
            height: 210mm;
            display: flex;
            page-break-after: always;
            box-sizing: border-box;
        }}
        
        .page {{
            width: 148.5mm;
            height: 210mm;
            padding: 10mm;
            box-sizing: border-box;
            border-right: 1px dashed #ccc;
        }}
        
        .page:last-child {{
            border-right: none;
        }}
        
        .page-header {{
            text-align: center;
            font-size: 14pt;
            font-weight: bold;
            margin-bottom: 5mm;
            border-bottom: 2px solid #333;
            padding-bottom: 2mm;
        }}
        
        .empty-page {{
            background: #fafafa;
        }}
        
        .week-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 2mm;
            margin-top: 5mm;
        }}
        
        .day-header {{
            text-align: center;
            font-weight: bold;
            font-size: 10pt;
            padding: 2mm;
            background: #f0f0f0;
        }}
        
        .day-cell {{
            min-height: 20mm;
            border: 1px solid #ddd;
            padding: 2mm;
            font-size: 9pt;
        }}
        
        .day-number {{
            font-weight: bold;
            font-size: 11pt;
        }}
        
        .month-name {{
            color: #666;
            font-size: 8pt;
            margin-top: 1mm;
        }}
        
        @media print {{
            .page-spread {{
                page-break-after: always;
            }}
        }}
    </style>
</head>
<body>
""".format(YEAR))
    
    # Group pages into spreads (2 pages side by side)
    all_pages = []
    for sig in signatures:
        all_pages.extend(sig.pages)
    
    # Create page spreads (2 pages per spread)
    for i in range(0, len(all_pages), 2):
        print(f"Creating page spread {i//2 + 1}")
        html_parts.append('    <div class="page-spread">\n')
        
        # Left page
        if i < len(all_pages):
            page = all_pages[i]
            is_empty = len(page.days) == 0
            page_class = 'page empty-page' if is_empty else 'page'
            html_parts.append(f'        <div class="{page_class}">\n')
            
            if not is_empty:
                html_parts.append(f'            <div class="page-header">Week {i//2 + 1} - Signature {page.signature_number}</div>\n')
                html_parts.append('            <div class="week-grid">\n')
                
                # Day headers
                for day_name in DAY_NAMES['en']:
                    html_parts.append(f'                <div class="day-header">{day_name[:3]}</div>\n')
                
                # Days
                for day in page.days:
                    month_name_short = MONTH_NAMES['en'][day.date.month - 1][:3]
                    html_parts.append(f'                <div class="day-cell">\n')
                    html_parts.append(f'                    <div class="day-number">{day.date.day}</div>\n')
                    html_parts.append(f'                    <div class="month-name">{month_name_short}</div>\n')
                    html_parts.append('                </div>\n')
                
                # Fill empty cells if week is incomplete
                empty_cells_needed = 7 - len(page.days)
                for _ in range(empty_cells_needed):
                    print(f"Filling empty cell for week {i//2 + 1}")
                    html_parts.append('                <div class="day-cell"></div>\n')
                
                html_parts.append('            </div>\n')
            
            html_parts.append('        </div>\n')
        
        # Right page
        if i + 1 < len(all_pages):
            page = all_pages[i + 1]
            is_empty = len(page.days) == 0
            page_class = 'page empty-page' if is_empty else 'page'
            html_parts.append(f'        <div class="{page_class}">\n')
            
            if not is_empty:
                html_parts.append(f'            <div class="page-header">Week {i//2 + 1} - Signature {page.signature_number}</div>\n')
                html_parts.append('            <div class="week-grid">\n')
                
                # Day headers
                for day_name in DAY_NAMES['en']:
                    html_parts.append(f'                <div class="day-header">{day_name[:3]}</div>\n')
                
                # Days
                for day in page.days:
                    month_name_short = MONTH_NAMES['en'][day.date.month - 1][:3]
                    html_parts.append(f'                <div class="day-cell">\n')
                    html_parts.append(f'                    <div class="day-number">{day.date.day}</div>\n')
                    html_parts.append(f'                    <div class="month-name">{month_name_short}</div>\n')
                    html_parts.append('                </div>\n')
                
                # Fill empty cells if week is incomplete
                empty_cells_needed = 7 - len(page.days)
                for _ in range(empty_cells_needed):
                    print(f"Filling empty cell for week {i//2 + 1}")
                    html_parts.append('                <div class="day-cell"></div>\n')
                
                html_parts.append('            </div>\n')
            
            html_parts.append('        </div>\n')
        
        html_parts.append('    </div>\n')
    
    html_parts.append("</body>\n</html>")
    
    return "".join(html_parts)


def write_html_to_file(html: str, filename: str):
    """
    Write the HTML file to a file
    """
    with open(filename, "w") as f:
        f.write(html)

def main():
    print(f"Generating calendar for {YEAR}")
    days = generate_days()
    pages = add_page_metadata_to_days(days)
    rearranged_pages = rearrange_pages_into_signatures(pages)
    
    # Group rearranged pages into Signature objects
    SIGNATURE_SIZE = 8
    signatures = []
    for i in range(0, len(rearranged_pages), SIGNATURE_SIZE):
        print(f"Grouping pages into signature {i // SIGNATURE_SIZE + 1}")
        sig_pages = rearranged_pages[i:i + SIGNATURE_SIZE]
        
        # Pad incomplete signatures with empty pages
        while len(sig_pages) < SIGNATURE_SIZE:
            print(f"Padding signature {i // SIGNATURE_SIZE + 1} with empty page")
            empty_page = Page(
                days=[],
                signature_number=i // SIGNATURE_SIZE + 1,
                number_in_signature=len(sig_pages) + 1
            )
            sig_pages.append(empty_page)
        
        signature = Signature(
            pages=sig_pages,
            signature_number=i // SIGNATURE_SIZE + 1
        )
        signatures.append(signature)
    
    html = generate_html(signatures)
    print(f"Writing HTML to file calendar_{YEAR}.html")
    write_html_to_file(html, f"calendar_{YEAR}.html")

if __name__ == "__main__":
    main()