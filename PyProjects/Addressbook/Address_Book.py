import csv

contacts = []

CSV_FILE = "Address_book.csv"
HEADER_NAMES = ["Name", "Phone", "Email", "Address"]

def save_contacts():
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=HEADER_NAMES)
        writer.writeheader()
        writer.writerows(contacts)

def open_file():
    try:
        with open(CSV_FILE, "r", encoding="utf-8") as file:
            lines = csv.DictReader(file)
            for line in lines:
                contacts.append(dict(line))  # ensure plain dict
    except FileNotFoundError:
        # file not found -> start with empty contacts
        pass

def view_contacts():
    if not contacts:
        print("Address book is empty.")
        return
    print("Your Address Book:")
    for i, contact in enumerate(contacts, start=1):
        print(f"{i}. Name: {contact.get('Name','')}")
        print(f"   Phone: {contact.get('Phone','')}")
        print(f"   Email: {contact.get('Email','')}")
        print(f"   Address: {contact.get('Address','')}")
        print("-" * 30)

def find_matches_by_name(name):
    name = name.strip().lower()
    matches = [(i, c) for i, c in enumerate(contacts) if c.get("Name", "").strip().lower() == name]
    return matches

def add_contact():
    name = input("Enter the name: ").strip()
    phone = input("Enter the phone: ").strip()
    email = input("Enter the email: ").strip()
    address = input("Enter the address: ").strip()
    contacts.append({"Name": name, "Phone": phone, "Email": email, "Address": address})
    save_contacts()
    print("Contact added successfully!")

def update_contact():
    name = input("Enter the name of the contact to update: ").strip()
    matches = find_matches_by_name(name)
    if not matches:
        print("No contact found with that name.")
        return
    if len(matches) > 1:
        print("Multiple contacts found:")
        for idx, (i, c) in enumerate(matches, start=1):
            print(f"{idx}. {c.get('Name')} - {c.get('Phone')} - {c.get('Email')}")
        sel = input(f"Choose which contact to update (1-{len(matches)}), or press Enter to cancel: ").strip()
        if not sel:
            print("Cancelled.")
            return
        try:
            sel = int(sel) - 1
            chosen_index = matches[sel][0]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
    else:
        chosen_index = matches[0][0]

    contact = contacts[chosen_index]
    print("Press Enter to keep current value.")
    new_name = input(f"Name [{contact.get('Name')}]: ").strip() or contact.get('Name')
    new_phone = input(f"Phone [{contact.get('Phone')}]: ").strip() or contact.get('Phone')
    new_email = input(f"Email [{contact.get('Email')}]: ").strip() or contact.get('Email')
    new_address = input(f"Address [{contact.get('Address')}]: ").strip() or contact.get('Address')

    contacts[chosen_index] = {"Name": new_name, "Phone": new_phone, "Email": new_email, "Address": new_address}
    save_contacts()
    print("Contact updated successfully!")

def delete_contact():
    name = input("Enter the name of the contact to delete: ").strip()
    matches = find_matches_by_name(name)
    if not matches:
        print("No contact found with that name.")
        return
    if len(matches) > 1:
        print("Multiple contacts found:")
        for idx, (i, c) in enumerate(matches, start=1):
            print(f"{idx}. {c.get('Name')} - {c.get('Phone')} - {c.get('Email')}")
        sel = input(f"Choose which contact to delete (1-{len(matches)}), or press Enter to cancel: ").strip()
        if not sel:
            print("Cancelled.")
            return
        try:
            sel = int(sel) - 1
            chosen_index = matches[sel][0]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
    else:
        # only one match -> remove it
        chosen_index = matches[0][0]

    removed = contacts.pop(chosen_index)
    save_contacts()
    print(f"Contact '{removed.get('Name')}' deleted successfully!")

# load existing file
open_file()

# main loop
while True:
    try:
        print("\nAddress Book Menu:")
        print("1. Add Contact")
        print("2. View Contacts")
        print("3. Update Contact")
        print("4. Delete Contact")
        print("5. Exit")

        choice = input("Enter your choice (1/2/3/4/5): ").strip()
        if choice == "1":
            add_contact()
        elif choice == "2":
            view_contacts()
        elif choice == "3":
            update_contact()
        elif choice == "4":
            delete_contact()
        elif choice == "5":
            print("Goodbye")
            break
        else:
            print("Invalid choice! Please try again.")
    except Exception as e:
        print(f"Error: {e}")
