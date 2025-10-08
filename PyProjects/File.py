# file = open("mytest.txt", "r")

# contect = file.readlines()
# for line in contect:
#     print(line.strip())
    
# file = open("mytest.txt", "a")
# file.write("In line ezafe shode.\n")

# file.close()


with open("mytest.txt", "a") as myfile:
    myfile.write("This is lastline\n")

