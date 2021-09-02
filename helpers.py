def string_to_date(date):
    split = date.split(",")
    split = split[1:]
    month, day = split[0].strip().split(" ")
    month = month_to_num[month]
    year = split[1]
    return f"{year.strip()}{month.strip()}{day.strip()}"

month_to_num = {
    "January": "01",
    "February": "02",
    "March": "03",
    "April": "04",
    "May": "05",
    "June": "06",
    "July": "07",
    "August": "08",
    "September": "09",
    "October": "10",
    "November": "11",
    "December": "12",
}