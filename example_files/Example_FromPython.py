"""
Example for calling pydatview to visuzalize a dataframe while scripting from python

"""
import numpy as np
import pandas as pd
import pydatview 

df1 = pd.DataFrame(data={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0})
df2 = pd.DataFrame(data={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0})

# --- Opening two dataframes
pydatview.show(dataframes=[df1,df2], names=['WT1','WT2'])
# pydatview.show([df1,df2])

# --- Opening one dataframe
# pydatview.show(df1)

# --- Opening files:
#pydatview.show(filenames=['file.csv','file2.csv'])
#pydatview.show(['file.csv','file2.csv'])
#pydatview.show('file.csv')
