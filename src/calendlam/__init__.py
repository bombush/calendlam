from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import datetime as dt

# init dates
year_start = dt.date(2026, 1, 1)
year_end = dt.date(2026, 12, 31)


# define day and month names
days_en = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
days_cz = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"]
months_en = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
months_cz = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září", "říjen", "listopad", "prosinec"]


# generate data structure for year
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


def print_and_dump(months):
    print(months)
    import json
    with open('output/data.json', 'w') as f:
        json.dump(months, f, default=str, indent=4)
    exit(0)

#print_and_dump(months)

# render and print pages
jinja_env = Environment(loader=FileSystemLoader("templates"))
template = jinja_env.get_template("week.jinja")
for i, month in enumerate(months):
    for j, page in enumerate(month["weeks"]):
        print(page)
        templated_page = template.render(days=page, month=month, year = 2026)
        filename = f"page_{i+1:03d}_{j+1:03d}"

        from pathlib import Path
        dir = Path("output/html/")
        dir.mkdir(parents=True, exist_ok=True)
        dir = Path("output/pdf/")
        dir.mkdir(parents=True, exist_ok=True)

        with open(f"output/html/{filename}.html", "w") as f:
            f.write(templated_page)

        HTML(string=templated_page).write_pdf(f"output/pdf/{filename}.pdf", pdf_variant="pdf/x-3")