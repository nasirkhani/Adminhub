import csv

contacts = []

def save_contacts():
    with open("Address_book.csv", "w", newline="") as file:
        header_names = ["Name", "Phone", "Email", "Address"]
        writer = csv.DictWriter(file, fieldnames=header_names)
        writer.writeheader()
        writer.writerows(contacts)

def view_contacts():
    print("Your Address Book: ")
    for contact in contacts:
        print(f"Name: {contact['Name']}")
        print(f"Phone: {contact['Phone']}")
        print(f"Email: {contact['Email']}")
        print(f"Address: {contact['Address']}")
        print("-" * 20)


def open_file():
    try:
        with open("Address_book.csv", "r") as file:
            lines = csv.DictReader(file)
            for line in lines:
                contacts.append(line)
    except FileNotFoundError:
        print("The file does not exist!")

open_file()
while True:
    try:
        print("Address Book Menu:")
        print("1. Add Contact")
        print("2. View Contact")
        print("3. Update Contact")
        print("4. Delete Contact")
        print("5. Exit")

        choice = int(input("Enter your choice (1/2/3/4/5): ").strip())
        if choice == 2:
            view_contacts()
        elif choice == 5:
            print("Goodbye")
            exit()
        else:
            print("Invalid choice!, Please try again.")
    except Exception as e:
        print(f"Error: {e}")
    



