import json
import numpy as np
import pandas as pd
import os
from pydatview.io import defaultUserDataDir

from .GUICommon import Error
from .GUICommon import getFontSize, getMonoFontSize
from .GUIPlotPanel import PlotPanel
from .GUIInfoPanel import InfoPanel
from .Tables import TableList
from .pipeline import Pipeline


def configFilePath():
    return os.path.join(defaultUserDataDir(), 'pyDatView', 'pyDatView.json')

def loadAppData(mainframe):
    configFile = configFilePath()
    os.makedirs(os.path.dirname(configFile), exist_ok=True)
    data = defaultAppData(mainframe)
    #print('>>> configFile', configFile)
    #print('Default Data content:\n')
    #for k,v in data.items():
    #    print('{:20s}: {}\n'.format(k,v))
    if os.path.exists(configFile):
        sError=''
        try:
            with open(configFile) as f:
                data2 = json.load(f)
        except:
            sError='Error: pyDatView config file is not properly formatted.\n\n'
            sError+='The config file was at the following location:\n     {}\n\n'.format(configFile)

            configFileBkp = configFile+'_bkp'
            import shutil
            try:
                shutil.copy2(configFile, configFileBkp)
                sError+='A backup of the file was made at the following location:\n    {}\n\n'.format(configFileBkp)
                backup=True
            except:
                backup=False
            if backup:
                try:
                    os.remove(configFile)
                except:
                    sError+='To solve this issue, the config file was deleted.\n\n'
            else:
                sError+='A backup of the file could not be made and the file was not deleted\n\n'
            sError+='If the problem persists, post an issue on the github repository\n'
            #raise Exception(sError)
            Error(mainframe, sError)
        if len(sError)==0:
            # Merging only what overlaps between default and user file
            # --- Level 1
            for k1,v1 in data2.items():
                if k1 in data.keys():
                    if type(data[k1]) is dict:
                        # --- Level 2
                        for k2,v2 in v1.items():
                            if k2 in data[k1].keys():
                                if type(data[k1][k2]) is dict:
                                    # --- Level 3
                                    for k3,v3 in v2.items():
                                        if k3 in data[k1][k2].keys():
                                            data[k1][k2][k3]=v3
                                else:
                                    data[k1][k2]=v2
                    else:
                        data[k1]=v1
    #print('Data content on load:\n')
    #for k,v in data.items():
    #    print('{:20s}: {}\n'.format(k,v))
    return data

def saveAppData(mainFrame, data):
    if not mainFrame.datareset:
        # --- Import data from GUI
        data['fontSize']    = int(getFontSize())
        data['monoFontSize'] = int(getMonoFontSize())
        if hasattr(mainFrame, 'plotPanel'):
            mainFrame.plotPanel.saveData(data['plotPanel'])
        if hasattr(mainFrame, 'infoPanel'):
            mainFrame.infoPanel.saveData(data['infoPanel'])
        if hasattr(mainFrame, 'tablist'):
            mainFrame.tablist.saveOptions(data['loaderOptions'])
        if hasattr(mainFrame, 'pipePanel'):
            mainFrame.pipePanel.saveData(data['pipeline'])

    # --- Sanitize data
    data = _sanitize(data)

    # --- Write config file
    configFile = configFilePath()
    #print('>>> Writing configFile', configFile)
    #print('Data content on close:\n')
    #for k,v in data.items():
    #    print('{:20s}: {}\n'.format(k,v))
    try:
        os.makedirs(os.path.dirname(configFile), exist_ok=True)
        with open(configFile, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def _sanitize(data):
    """
    Replace numpy arrays with list 
    TODO: remove any callbacks/lambda
    """
    # --- Level 1
    for k1,v1 in data.items():
        if type(v1) is dict:
            data[k1] = _sanitize(v1)
        elif isinstance(v1, (pd.core.series.Series,np.ndarray)):
            data[k1]=list(v1)
    return data

def defaultAppData(mainframe):
    data={}
    # --- Main frame data
    data['windowSize'] = (900,700)
    data['monoFontSize'] = mainframe.systemFontSize
    data['fontSize']     = mainframe.systemFontSize
    # Loader/Table
    data['loaderOptions'] = TableList.defaultOptions()
    # Pipeline
    data['pipeline'] = Pipeline.defaultData()
    #SIDE_COL       = [160,160,300,420,530]
    #SIDE_COL_LARGE = [200,200,360,480,600]
    #BOT_PANL =85
    # GUI
    data['plotPanel']=PlotPanel.defaultData()
    data['infoPanel']=InfoPanel.defaultData()
    return data



