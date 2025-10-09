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
