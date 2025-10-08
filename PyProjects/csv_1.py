import csv

with open("color.csv","r") as f:
    content = csv.reader(f)
    for row in content:
        print(row)

