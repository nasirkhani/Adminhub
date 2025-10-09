import pandas as pd 

while True:
    try:
        with open("something_random.txt", "r") as file:
            content = file.read()
            print("\n=== File Content ===")
            print(content)
        print("\nFile found successfully. Exiting program.")
        break
    except FileNotFoundError:
        print("File not found!")
        
        choice = input("For exit press q, for continue press c: ").lower()
        
        if choice == 'q':
            print("Exiting...")
            quit()
        elif choice == 'c':
            print("Trying again...\n")
            continue
        else:
            print("Invalid input, please enter 'q' or 'c'.\n")
