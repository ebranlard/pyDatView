import unittest
import numpy as np
#from pydatview.Tables import Table
import os
import matplotlib.pyplot as plt


from pydatview.Tables import TableList, Table
from pydatview.pipeline import Pipeline, Action
from pydatview.plotdata import PlotData

class TestPipeline(unittest.TestCase):

    def test_pipeline(self):
        pass


if __name__ == '__main__':

    from pydatview.plugins import getDataPluginsDict

    DPD = getDataPluginsDict()


    tablist = TableList.createDummyList(1)
    print(tablist._tabs[0].data)

    pipeline = Pipeline()

    action = DPD['Standardize Units (SI)']['callback']()
    pipeline.append(action)

    print(pipeline) 

    pipeline.apply(tablist)

    print(tablist._tabs[0].data)

    pipeline.apply(tablist)
    print(tablist._tabs[0].data)



    action = DPD['Standardize Units (WE)']['callback']()
    pipeline.append(action)

    pipeline.apply(tablist)
    print(tablist._tabs[0].data)


    pipeline.apply(tablist, force=True)
    print(tablist._tabs[0].data)
