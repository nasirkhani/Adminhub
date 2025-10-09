import pandas as pd

# df = pd.DataFrame({'animal': ['aligator', 'bee', 'falcon', 'lion', 
#                               'monkey', 'parrot', 'shark', 'whale', 'zebra']})

# print(df)

with pd.ExcelWriter("test.xlsx") as writer:
    pd.read_csv("color.csv")
    
    pd.to_

