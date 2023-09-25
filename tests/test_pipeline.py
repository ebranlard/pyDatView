import unittest
import numpy as np
#from pydatview.Tables import Table
import os
import matplotlib.pyplot as plt


from pydatview.Tables import TableList, Table
from pydatview.pipeline import Pipeline, Action
from pydatview.plotdata import PlotData
from pydatview.plugins import DATA_PLUGINS_SIMPLE

scriptDir = os.path.dirname(__file__)

class TestPipeline(unittest.TestCase):

    def test_pipeline_std_units(self):
        # Add two actions to the pipeline and verify that "apply" works as intended

        # --- Create Tabe List
        tablist = TableList.createDummy(nTabs=1, n=5)
        df = tablist._tabs[0].data.copy()
        self.assertTrue('RotSpeed_0_[rpm]' in tablist._tabs[0].data.keys())

        # --- Create a Pipeline with a Standardize units actions
        DPD = DATA_PLUGINS_SIMPLE
        pipeline = Pipeline()

        # --- Add and apply Standardize Units SI
        action = DPD['Standardize Units (SI)'](label='Standardize Units (SI)')
        pipeline.append(action, apply=False)
        pipeline.apply(tablist)
        self.assertTrue('RotSpeed_0_[rad/s]' in tablist._tabs[0].data.keys())

        #print(pipeline) 
        #print('>>> Data')
        #print(tablist._tabs[0].data)

        # --- Add and apply Standardize Units WE
        action = DPD['Standardize Units (WE)'](label='Standardize Units (WE)')
        pipeline.append(action, apply=False)
        pipeline.apply(tablist)
        self.assertTrue('RotSpeed_0_[rpm]' in tablist._tabs[0].data.keys())

        np.testing.assert_array_almost_equal(tablist._tabs[0].data['RotSpeed_0_[rpm]'],df['RotSpeed_0_[rpm]'], 6)
        #print('>>> Data 3')
        #print(tablist._tabs[0].data)
        #print('>>>> PIPELINE')
        #print(pipeline) 


    def test_pipeline_script_squareIt(self):
        # Add one action to the pipeline and verify that the script generation works
        # And that the script is actually runable! 
        tablist = TableList()
        tablist.load_tables_from_files(filenames=[os.path.join(scriptDir,'../example_files/CSVComma.csv')])

        # Dummy action
        imports=['import pandas as pd']
        code="""df = df**2"""
        action = Action(name='squareIt!', code=code, imports=imports)

        pipeline = Pipeline()
        pipeline.append(action, apply=False)
        ID= [[0,1,2]]
        s = pipeline.script(tablist, ID=ID, scripterOptions=None)
        #print(s)
        pipeline.scripter.run(pltshow=False)

    def test_pipeline_script_plotdata_plugins(self):
        # Add a Plot Data action to the pipeline and verify that the script generation works
        # And that the script is actually runable! 
        from pydatview.plugins.plotdata_sampler import samplerAction 
        from pydatview.plugins.plotdata_binning import binningAction
        from pydatview.plugins.plotdata_filter import filterAction 
        from pydatview.plugins.plotdata_removeOutliers import removeOutliersAction 
        tablist = TableList()
        tablist.load_tables_from_files(filenames=[os.path.join(scriptDir,'../example_files/FASTIn_arf_coords.txt')])

        pipeline = Pipeline()
        # action
        action = samplerAction()
        action.data['name']='Every n'
        action.data['param']=3

        pipeline.append(binningAction(data={'xMin':0, 'xMax':1, 'nBins':100}), apply=False) 
        pipeline.append(action, apply=False)
        pipeline.append(filterAction(), apply=False)
        pipeline.append(removeOutliersAction(), apply=False)
        ID= [[0,1,2]]
        s = pipeline.script(tablist, ID=ID, scripterOptions=None)
        #print(s)
        pipeline.scripter.run(pltshow=False)

    def test_pipeline_script_data_plugins(self):
        # Add a Data action to the pipeline and verify that the script generation works
        # And that the script is actually runable! 
        from pydatview.plugins.data_standardizeUnits import standardizeUnitsAction 
        tablist = TableList()
        tablist.load_tables_from_files(filenames=[os.path.join(scriptDir,'../example_files/CSVComma.csv')])

        pipeline = Pipeline()
        pipeline.append(standardizeUnitsAction(), apply=False) 
        pipeline.apply(tablist) # Apply will change unit
        ID= [[0,1,2]]
        s = pipeline.script(tablist, ID=ID, scripterOptions=None)
        #print(s)
        self.assertTrue(s.find('ColB_[rad/s]')>10) # Make sure units have been changed in script
        pipeline.scripter.run(pltshow=False)

if __name__ == '__main__':
    unittest.main()
#     TestPipeline().test_pipeline_script_squareIt()
#     TestPipeline().test_pipeline_script_plotdata_plugins()
#     TestPipeline().test_pipeline_script_data_plugins()



