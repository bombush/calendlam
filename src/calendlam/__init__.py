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


#output_as_separate_pages(months)
output_as_single_page(months)