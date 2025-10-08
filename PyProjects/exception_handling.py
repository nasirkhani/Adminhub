# try:
#     num1 = int(input("Enter the first number: "))
#     num2 = int(input("Enter the second number: "))

#     print(num1 / num2)

# except ZeroDivisionError:
#     print("The second number is zero.")
# except ValueError:
#     print("The value is not a number.")
# while True:
#     try:
#         file = open("something_random.txt", "r")
#         content  = file.read()
#         print(content)
#         file.close()
#     except FileNotFoundError:
#         print("File not found!")
#     finally:
#         print("Please try again.")
#         print("Or")
#         x = input("For exit press q: ")
#         z = input("For continue press c: ")
#         if x.lower == 'q':
#             print("Exiting...")
#             quit()
#         else:
#             print("Continuing...\n")



while True:
    try:
        # تلاش برای باز کردن فایل
        with open("something_random.txt", "r") as file:
            content = file.read()
            print("\n=== File Content ===")
            print(content)
        print("\nFile found successfully. Exiting program.")
        break                   # اگر فایل پیدا شد از حلقه خارج شو
    except FileNotFoundError:
        print("File not found!")
        
        choice = input("For exit press q, for continue press c: ").lower()
        
        if choice == 'q':
            print("Exiting...")
            quit()              # یا exit()، بلافاصله از برنامه خارج می‌شود
        elif choice == 'c':
            print("Trying again...\n")
            continue            # دوباره از اول حلقه اجرا شود
        else:
            print("Invalid input, please enter 'q' or 'c'.\n")
