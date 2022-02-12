import json
import os
from weio.weio import defaultUserDataDir
from .GUICommon import Error


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
    from .GUICommon import getFontSize, getMonoFontSize
    if not mainFrame.datareset:
        # --- Import data from GUI
        data['fontSize']    = int(getFontSize())
        data['monoFontSize'] = int(getMonoFontSize())
        if hasattr(mainFrame, 'plotPanel'):
            savePlotPanelData(data['plotPanel'], mainFrame.plotPanel)
        if hasattr(mainFrame, 'plotPanel'):
            saveInfoPanelData(data['infoPanel'], mainFrame.infoPanel)

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

def defaultAppData(mainframe):
    data={}
    # --- Main frame data
    data['windowSize'] = (900,700)
    data['monoFontSize'] = mainframe.systemFontSize
    data['fontSize']     = mainframe.systemFontSize
    #SIDE_COL       = [160,160,300,420,530]
    #SIDE_COL_LARGE = [200,200,360,480,600]
    #BOT_PANL =85
    data['plotPanel']=defaultPlotPanelData()
    data['infoPanel']=defaultInfoPanelData()
    return data

# --- Plot Panel
# TODO put this into plotPanel file?
def savePlotPanelData(data, plotPanel):
    data['Grid']      = plotPanel.cbGrid.IsChecked()
    data['CrossHair'] = plotPanel.cbXHair.IsChecked()
    data['plotStyle']['Font']           = plotPanel.esthPanel.cbFont.GetValue()
    data['plotStyle']['LegendFont']     = plotPanel.esthPanel.cbLgdFont.GetValue()
    data['plotStyle']['LegendPosition'] = plotPanel.esthPanel.cbLegend.GetValue()
    data['plotStyle']['LineWidth']      = plotPanel.esthPanel.cbLW.GetValue()
    data['plotStyle']['MarkerSize']     = plotPanel.esthPanel.cbMS.GetValue()
    
def defaultPlotPanelData():
    data={}
    data['CrossHair']=True
    data['Grid']=False
    plotStyle = dict()
    plotStyle['Font']           = '11'
    plotStyle['LegendFont']     = '11'
    plotStyle['LegendPosition'] = 'Upper right'
    plotStyle['LineWidth']      = '1.5'
    plotStyle['MarkerSize']     = '2'
    data['plotStyle']= plotStyle
    return data

# --- Info Panel
# TODO put this into infoPanel file?
def saveInfoPanelData(data, infoPanel):
    data['ColumnsRegular'] = [c['name'] for c in infoPanel.ColsReg if c['s']]
    data['ColumnsFFT']     = [c['name'] for c in infoPanel.ColsFFT if c['s']]
    data['ColumnsMinMax']  = [c['name'] for c in infoPanel.ColsMinMax if c['s']]
    data['ColumnsPDF']     = [c['name'] for c in infoPanel.ColsPDF if c['s']]
    data['ColumnsCmp']     = [c['name'] for c in infoPanel.ColsCmp if c['s']]

def defaultInfoPanelData():
    data={}
    data['ColumnsRegular'] = ['Column','Mean','Std','Min','Max','Range','dx','n']
    data['ColumnsFFT']     = ['Column','Mean','Std','Min','Max','Min(FFT)','Max(FFT)',u'\u222By(FFT)','dx(FFT)','xMax(FFT)','n(FFT)','n']
    data['ColumnsMinMax']  = ['Column','Mean','Std','Min','Max','Mean(MinMax)','Std(MinMax)',u'\u222By(MinMax)','n']
    data['ColumnsPDF']     = ['Column','Mean','Std','Min','Max','Min(PDF)','Max(PDF)',u'\u222By(PDF)','n(PDF)']
    data['ColumnsCmp']     = ['Column','Mean(Cmp)','Std(Cmp)','Min(Cmp)','Max(Cmp)','n(Cmp)']
    return data


