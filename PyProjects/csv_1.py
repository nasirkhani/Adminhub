import csv

file_path = "color.csv"

with open(file_path, newline="", encoding="utf-8") as f:
    csv_reader = csv.reader(f)
    rows = list(csv_reader)

print(rows)

