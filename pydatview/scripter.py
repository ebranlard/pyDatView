import numpy as np
from collections import OrderedDict

# From pydatview imports to WELIB
_WELIB={
    'pydatview.io':'welib.weio',
    'pydatview.tools':'welib.tools',
    'pydatview.fast.postpro':'welib.fast.postpro',
        }
_PYFAST={
    'pydatview.io'          :'pyFAST.input_output',
    'pydatview.tools'       :'pyFAST.tools',
    'pydatview.fast.postpro':'pyFAST.postpro', # I think...
        }

_flavorReplaceDict={
        'welib':_WELIB,
        'pyFAST':_PYFAST,
        'pydatview':{},
        }

_defaultOpts={
        'libFlavor':'pydatview',
        'dfsFlavor':'dict',
        'oneTabPerFile':False,
        'oneRawTab':False,
        'indent':'    ',
        'verboseCommentLevel':2,
        }
_defaultPlotStyle={
    'grid':False, 'logX':False, 'logY':False,
    'LineStyles':['-','--','-.',':'],
    'Markers':[''],
    'LegendPosition':'best',
    'LineWidth':1.5,
    'ms':2.0,
}

class PythonScripter:
    def __init__(self, **opts):

        self.reset()
        self.setOptions(**opts)

        # Imports that we know we'll need
        self.addImport('import numpy as np')
        #self.addImport("import warnings; warnings.filterwarnings('ignore')")
        self.addImport('import pydatview.io as weio')
        self.addImport('import matplotlib.pyplot as plt')

    def reset(self):
        self.opts = _defaultOpts
        self.import_statements = set()
        self.actions = OrderedDict()
        self.adder_actions = OrderedDict()
        self.preplot_actions = OrderedDict()
        self.filenames = []
        self.df_selections = []  # List of tuples (df_index, column_x, column_y)
        self.df_formulae   = []  # List of tuples (df_index, name, formula)
        self.dfs = []
        self.subPlots = {'i':1, 'j':1, 'x_labels':['x'], 'y_labels':['y'], 'IPD':None, 'hasLegend':[False]}  
        self.plotStyle = _defaultPlotStyle

    def setOptions(self, **opts):
        for k,v in opts.items():
            if k not in _defaultOpts.keys():
                raise Exception('Unsupported option for scripter {}'.format(v))
            if k =='libFlavor' and v not in _flavorReplaceDict.keys():
                raise Exception('libFlavor not supported' + v)
            if k =='dfsFlavor' and v not in ['dict', 'list', 'enumeration']:
                raise Exception('dfsFlavor not supported' + v)
            self.opts[k] = v

    def addImport(self, import_statement):
        self.import_statements.add(import_statement)

    def addAction(self, action_name, code, imports=None, code_init=None):
        for imp in imports:
            self.addImport(imp)
        self.actions[action_name] = (code_init, code.strip())

    def addAdderAction(self, action_name, code, imports=None, code_init=None):
        for imp in imports:
            self.addImport(imp)
        self.adder_actions[action_name] = (code_init, code.strip())

    def addPreplotAction(self, action_name, code, imports=None, code_init=None):
        if imports is not None:
            for imp in imports:
                self.addImport(imp)
        self.preplot_actions[action_name] = (code_init, code.strip())

    def setPlotType(self, plotType, plotTypeOptions=None):
        """ Setup a prePlot action depending on plot Type"""
        opts = plotTypeOptions
        action_code = None
        imports     = None
        code_init   = ''
        if plotType is not None and plotType!='Regular':
            if plotType=='PDF':
                imports=['from pydatview.tools.stats import pdf_gaussian_kde, pdf_histogram']
                if opts is None:
                    action_code="""x, y = pdf_gaussian_kde(y, nOut=30)"""
                else:
                    if opts['smooth']:
                        action_code="x, y = pdf_gaussian_kde(y, nOut={})".format(opts['nBins'])
                    else:
                        action_code="x, y = pdf_histogram(y, nBins={}, norm=True, count=False)".format(opts['nBins'])

            elif plotType=='FFT':
                imports=['from pydatview.tools.spectral import fft_wrap']
                if opts is None:
                    opts={'yType':'PSD', 'avgMethod':'Welch', 'avgWindow':'Hamming', 'nExp':8, 'nPerDecade':8, 'bDetrend':False}
                action_code = "x, y, Info = fft_wrap(x, y, output_type='{}', averaging='{}', averaging_window='{}', detrend={}, nExp={}, nPerDecade={})".format(
                        opts['yType'], opts['avgMethod'], opts['avgWindow'], opts['bDetrend'], opts['nExp'], opts['nPerDecade'])

                # TODO xType..
                # if xType=='1/x':
                #     if unit(PD.sx)=='s':
                #         PD.sx= 'Frequency [Hz]'
                #     else:
                #         PD.sx= ''
                # elif xType=='x':
                #     PD.x=1/PD.x
                #     if unit(PD.sx)=='s':
                #         PD.sx= 'Period [s]'
                #     else:
                #         PD.sx= ''
                # elif xType=='2pi/x':
                #     PD.x=2*np.pi*PD.x
                #     if unit(PD.sx)=='s':
                #         PD.sx= 'Cyclic frequency [rad/s]'
                #     else:
                #         PD.sx= ''

            elif plotType=='MinMax':
                if opts is None:
                    action_code ="x = (x-np.min(x))/(np.max(x)-np.min(x))\n"
                    action_code+="y = (y-np.min(y))/(np.max(y)-np.min(y))"
                else: 
                    action_code = []
                    if opts['xScale']:
                        action_code+=["x = (x-np.min(x))/(np.max(x)-np.min(x))"]
                    comment=''
                    if opts['yCenter'].find('ref')>0:
                        comment=' # TODO: add yRef'
                    if opts['yCenter']=='None':
                        if opts['yScale']:
                            action_code+=["y = (y-np.min(y))/(np.max(y)-np.min(y))"]
                    elif opts['yCenter'].startswith('Mean'):
                        action_code+=["y -= np.mean(y)"+comment]
                    elif opts['yCenter'].startswith('Mid'):
                        action_code+=["y -= (np.min(y)+np.max(y))/2"+comment]
                    action_code = '\n'.join(action_code)

            elif plotType=='Compare':
                print('[WARN] Scripter - compare not implemented')

        if action_code is not None:
            self.addPreplotAction('plotType:'+plotType, action_code, imports, code_init)



    def addFormula(self, df_index, name, formula):
        self.df_formulae.append((df_index, name, formula))

    def selectData(self, df_index, column_x, column_y):
        self.df_selections.append((df_index, column_x, column_y))

    def setFiles(self, filenames):
        self.filenames = [f.replace('\\','/') for f in filenames]

    def setSubPlots(self, **kwargs):
        self.subPlots=kwargs

    def setPlotParameters(self, **params):
        self.plotStyle = params

    @property
    def needIndex(self):
        for df_index, column_x, column_y in self.df_selections:
            if column_x=='Index' or column_y=='Index':
                return True

    @property
    def needFormulae(self):
        return len(self.df_formulae)>0

    def generate(self, pltshow=True):

        script = []
        verboseCommentLevel = self.opts['verboseCommentLevel']
        indent0= ''
        indent1= self.opts['indent']
        indent2= indent1 + indent1
        indent3= indent2 + indent1
        plotStyle = self.plotStyle
    
        # --- Helper functions
        def forLoopOnDFs():
            if self.opts['dfsFlavor'] == 'dict':
                script.append("for key, df in dfs.items():")
            elif self.opts['dfsFlavor'] == 'list':
                script.append("for df in dfs:")

        def onlyOneFile():
            return len(self.filenames)==1
        def oneTabPerFile():
            return self.opts['oneTabPerFile']
        def oneRawTab():
            return self.opts['oneRawTab']
        def dontListFiles():
            return oneRawTab() or (onlyOneFile() and oneTabPerFile())

        def addActionCode(actioname, actioncode, ind, codeFail='pass'):
            if verboseCommentLevel>=3: 
                script.append(ind+ "# Apply action {}".format(actioname))
            if verboseCommentLevel>=2: 
                script.append(ind+'try:')
                script.append('\n'.join(ind+indent1+l for l in actioncode.splitlines()))
                script.append(ind+'except:')
                script.append(ind+indent1+codeFail)
            else:
                script.append('\n'.join(ind        +l for l in actioncode.splitlines()))



        # --- Disclaimer
        script.append('""" Script generated by pyDatView - The script will likely need to be adapted."""')

        # --- Add import statements, different for different flavor
        replaceDict=_flavorReplaceDict[self.opts['libFlavor']]
        # pydatview imports will be last
        imports = [ 'zzzzz'+ii if ii.find('pydatview')>0 else ii for ii in self.import_statements]
        imports.sort()
        imports = [ ii.replace('zzzzz', '') for ii in imports]
        for statement in imports:
            for k,v, in replaceDict.items():
                statement = statement.replace(k,v)
            script.append(statement)

        # --- List of files
        script.append("\n# --- Script parameters")
        if dontListFiles():
            script.append("filename = '{}'".format(self.filenames[0]))
        else:
            script.append("filenames = []")
            for filename in self.filenames:
                script.append(f"filenames += ['{filename}']")

        # --- Init data/preplot/adder actions
        if len(self.actions)>0 or len(self.preplot_actions)>0 or len(self.adder_actions)>0:
            script.append("\n# --- Data for different actions")

        if len(self.actions)>0:
            if verboseCommentLevel>=3:
                script.append("# --- Data for actions")
            for actionname, actioncode in self.actions.items():
                if actioncode[0] is not None and len(actioncode[0].strip())>0:
                    if verboseCommentLevel>=3:
                        script.append("# Data for action {}".format(actionname))
                    script.append(actioncode[0].strip())

        if len(self.preplot_actions)>0:
            script_pre = []
            for actionname, actioncode in self.preplot_actions.items():
                if actioncode[0] is not None and len(actioncode[0].strip())>0:
                    if verboseCommentLevel>=3:
                        script_pre.append("# Data for preplot action {}".format(actionname))
                    script_pre.append(actioncode[0].strip())
            if len(script_pre)>0:
                if verboseCommentLevel>=3:
                    script.append("# --- Data for preplot actions")
                script+=script_pre

        if len(self.adder_actions)>0:
            if verboseCommentLevel>=3:
                script.append("# --- Data for actions that add new dataframes")
            for actionname, actioncode in self.adder_actions.items():
                if actioncode[0] is not None and len(actioncode[0].strip())>0:
                    if verboseCommentLevel>=3:
                        script.append("# Data for adder action {}".format(actionname))
                    script.append(actioncode[0].strip())


        # --- List of Dataframes
        script.append("\n# --- Open and convert files to DataFrames")
        if self.opts['dfsFlavor'] == 'dict':
            if dontListFiles():
                script.append("dfs = {}")
                script.append("dfs[0] = weio.read(filename).toDataFrame()")
            else:
                script.append("dfs = {}")
                script.append("for iFile, filename in enumerate(filenames):")
                if self.opts['oneTabPerFile']:
                    script.append(indent1 + "dfs[iFile] = weio.read(filename).toDataFrame()")
                else:
                    script.append(indent1 + "dfs_or_df = weio.read(filename).toDataFrame()")
                    #script.append(indent1 + "# NOTE: we need a different action if the file contains multiple dataframes")
                    script.append(indent1 + "if isinstance(dfs_or_df, dict):")
                    script.append(indent2 + "for k,df in dfs_or_df.items():")
                    script.append(indent3 + "dfs[k+f'{iFile}'] = df")
                    script.append(indent1 + "else:")
                    script.append(indent2 + "dfs[f'tab{iFile}'] = dfs_or_df")
        elif self.opts['dfsFlavor'] == 'list':
            script.append("dfs = []")
            if dontListFiles():
                script.append("dfs.append( weio.read(filename).toDataFrame() )")
            else:
                script.append("for iFile, filename in enumerate(filenames):")
                if self.opts['oneTabPerFile']:
                    script.append(indent1 + "df = weio.read(filenames[iFile]).toDataFrame()")
                    script.append(indent1 + "dfs.append(df)")
                else:
                    #script.append(indent1 + "# NOTE: we need a different action if the file contains multiple dataframes")
                    script.append(indent1 + "dfs_or_df = weio.read(filenames[iFile]).toDataFrame()")
                    script.append(indent1 + "if isinstance(dfs_or_df, dict):")
                    script.append(indent2 + "dfs+= list(dfs_or_df.values()) # NOTE: user will need to adapt this.")
                    script.append(indent1 + "else:")
                    script.append(indent2 + "dfs.append(dfs_or_df)")

        elif self.opts['dfsFlavor'] == 'enumeration':
            if dontListFiles():
                script.append(f"df1 = weio.read(filename).toDataFrame()")
            else:
                for iFile, filename in enumerate(self.filenames):
                    iFile1 = iFile+1
                    if self.opts['oneTabPerFile']:
                        script.append(f"df{iFile1} = weio.read(filenames[{iFile}]).toDataFrame()")
                    else:
                        if verboseCommentLevel>=1:
                            script.append("# NOTE: we need a different action if the file contains multiple dataframes")
                        script.append(f"dfs_or_df = weio.read('{filename}').toDataFrame()")
                        script.append("if isinstance(dfs_or_df, dict):")
                        script.append(indent1 + f"df{iFile1} = next(iter(dfs_or_df.values())) # NOTE: user will need to adapt this.")
                        script.append("else:")
                        script.append(indent1 + f"df{iFile1} = dfs_or_df")

        # --- Adder actions 
        nTabs = len(self.filenames) # Approximate
        if len(self.adder_actions)>0:
            script.append("\n# --- Apply adder actions to dataframes")
            script.append("dfs_add = [] ; names_add =[]")
            if self.opts['dfsFlavor'] == 'dict':
                if dontListFiles():
                    script.append('df = dfs[0] # NOTE: we assume that only one dataframe is present' )
                    for actionname, actioncode in self.adder_actions.items():
                        addActionCode(actionname, actioncode[1], indent0, codeFail='dfs_new=[]; names_new=[]')
                        script.append(indent0+"dfs_add += dfs_new ; names_add += names_new")
                else:
                    script.append("for k, (key, df) in enumerate(dfs.items()):")
                    script.append(indent1 + "filename = filenames[k] # NOTE: this is approximate..")
                    for actionname, actioncode in self.adder_actions.items():
                        addActionCode(actionname, actioncode[1], indent1, codeFail='dfs_new=[]; names_new=[]')
                        script.append(indent1+"dfs_add += dfs_new ; names_add += names_new")
                script.append("for name_new, df_new in zip(names_add, dfs_new):")
                script.append(indent1+"if df_new is not None:")
                script.append(indent2+"dfs[name_new] = df_new")

            elif self.opts['dfsFlavor'] == 'list':
                if dontListFiles():
                    script.append('df = dfs[0]')
                    for actionname, actioncode in self.adder_actions.items():
                        addActionCode(actionname, actioncode[1], indent0, codeFail='dfs_new=[]; names_new=[]')
                        script.append(indent0+"dfs_add += dfs_new ; names_add += names_new")
                else:
                    script.append("for k, df in enumerate(dfs):")
                    script.append(indent1 + "filename = filenames[k] # NOTE: this is approximate..")
                    for actionname, actioncode in self.adder_actions.items():
                        addActionCode(actionname, actioncode[1], indent1, codeFail='dfs_new=[]; names_new=[]')
                        script.append(indent1+"dfs_add += dfs_new ; names_add += names_new")
                script.append("for name_new, df_new in zip(names_add, dfs_new):")
                script.append(indent1+"if df_new is not None:")
                script.append(indent2+"dfs += [df_new]")

            elif self.opts['dfsFlavor'] == 'enumeration':
                if dontListFiles():
                    for iTab in range(nTabs):
                        script.append('df = df{}'.format(iTab+1))
                        for actionname, actioncode in self.adder_actions.items():
                            addActionCode(actionname, actioncode[1], '')
                        script.append("df{} = dfs_new[0] # NOTE: we only keep the first table here..".format(nTabs+iTab+1))
                else:
                    for iTab in range(nTabs):
                        script.append("filename = filenames[{}] # NOTE: this is approximate..".format(iTab))
                        script.append('df = df{}'.format(iTab+1))
                        for actionname, actioncode in self.adder_actions.items():
                            addActionCode(actionname, actioncode[1], '')
                        script.append("df{} = dfs_new[0] # NOTE: we only keep the first table here..".format(nTabs+iTab+1))
                nTabs += nTabs


        # --- Insert index and formulae
        if self.needIndex or self.needFormulae: 
            script.append("\n# --- Insert columns")
            if self.opts['dfsFlavor'] in ['dict' or 'list']:
                forLoopOnDFs()
                if self.needIndex:
                    script.append(indent1 + "if not 'Index' in df.columns:")
                    script.append(indent2 + "df.insert(0, 'Index', np.arange(df.shape[0]))")
                if self.needFormulae:
                    script.append(indent1 + "# Adding formulae: NOTE adjust to apply to a subset of dfs")
                    # TODO potentially sort on df_index and use an if statement on k
                    for df_index, name, formula in self.df_formulae:
                        script.append(indent1 + "try:")
                        script.append(indent2 + "df['{}'] = {}".format(name, formula))
                        #df.insert(int(i+1), name, formula)
                        script.append(indent1 + "except:")
                        script.append(indent2 + "print('[WARN] Cannot add column {} to dataframe')".format(name))

            elif self.opts['dfsFlavor'] == 'enumeration':
                for iTab in range(nTabs):
                    if self.needIndex:
                        script.append("if not 'Index' in df.columns:")
                        script.append(indent1+"df{}.insert(0, 'Index', np.arange(df.shape[0]))".format(iTab+1))
                    dfName = 'df{}'.format(iTab+1)
                    if self.needFormulae:
                        script.append("# Adding formulae: NOTE adjust to apply to a subset of dfs")
                        # TODO potentially sort on df_index and use an if statement on k
                        for df_index, name, formula in self.df_formulae:
                            formula = formula.replace('df', dfName)
                            script.append(indent0 + "try:")
                            script.append(indent1 + "{}['{}'] = {}".format(dfName, name, formula))
                            #df.insert(int(i+1), name, formula)
                            script.append(indent0 + "except:")
                            script.append(indent1 + "print('[WARN] Cannot add column {} to dataframe')".format(name))


        # --- Data Actions
        if len(self.actions)>0:
            script.append("\n# --- Apply actions to dataframes")
            if self.opts['dfsFlavor'] == 'dict':
                script.append("for k, df in dfs.items():")
                for actionname, actioncode in self.actions.items():
                    addActionCode(actionname, actioncode[1], indent1)
                script.append(indent1 + "dfs[k] = df")

            elif self.opts['dfsFlavor'] == 'list':
                script.append("for k, df in enumerate(dfs):")
                for actionname, actioncode in self.actions.items():
                    addActionCode(actionname, actioncode[1], indent1)
                script.append(indent1 + "dfs[k] = df")

            elif self.opts['dfsFlavor'] == 'enumeration':
                for iTab in range(len(self.filenames)):
                    script.append('df = df{}'.format(iTab+1))
                    for actionname, actioncode in self.actions.items():
                        addActionCode(actionname, actioncode[1], '')
                    script.append('df{} = df'.format(iTab+1))

        if len(self.preplot_actions)>0:
            script.append("\n# --- Plot preprocessing")
            script.append("def preproXY(x, y):")
            for actionname, actioncode in self.preplot_actions.items():
                script.append('\n'.join(indent1+l for l in actioncode[1].splitlines()))
            script.append(indent1+"return x, y")

        # --- Plot Styling
        script.append("\n# --- Plot")
        #  Plot Styling
        if verboseCommentLevel>=3:
            script.append("# Plot styling")
        # NOTE: dfs not known for enumerate
        script.append("lw = {} ".format(plotStyle['LineWidth']))
        script.append("stys = {} * 100".format(plotStyle['LineStyles'])) 
        if len(plotStyle['Markers'])>1:
            script.append("mrks = {} * 100".format(plotStyle['Markers'])) 
            script.append("ms = {} ".format(plotStyle['MarkerSize']))
        #script.append("cols=['r', 'g', 'b'] * 100")
        if self.opts['dfsFlavor'] == 'dict':
            script.append("tabNames = list(dfs.keys())")
        if verboseCommentLevel>=3:
            script.append("# Subplots")

        if self.subPlots['i']==1 and self.subPlots['j']==1:
            noSubplot=True
        else:
            noSubplot=False

        if noSubplot:
            script.append("fig,ax = plt.subplots({}, {}, sharex=True, figsize=(6.4,4.8))".format(self.subPlots['i'],self.subPlots['j']))
            script.append("fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)")
        else:
            script.append("fig,axes = plt.subplots({}, {}, sharex=True, figsize=(6.4,4.8))".format(self.subPlots['i'],self.subPlots['j']))
            script.append("fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)")
            script.append("axes = np.reshape(axes, ({},{}))".format(self.subPlots['i'],self.subPlots['j']))

        def getAxesString(i,j):
            if noSubplot:
                return 'ax'
            else:
                return 'axes[{},{}]'.format(i, j)

        sAxes=''
        sDF=''
        for iPD, (df_index, column_x, column_y) in enumerate(self.df_selections):
            # --- Find relationship between axis and plotdata
            iaxSel=0
            jaxSel=0 # TODO
            iPDPos = 0
            if self.subPlots['IPD'] is not None:
                for iax, axIPD in enumerate(self.subPlots['IPD']):
                    if iPD in axIPD:
                        iaxSel= iax
                        iPDPos = axIPD.index(iPD)
                        break

            if not noSubplot:
                sAxes_new = 'ax = '+getAxesString(iaxSel, jaxSel)
                if sAxes_new != sAxes: 
                    sAxes=sAxes_new
                    script.append(sAxes_new)
            if verboseCommentLevel>=3:
                script.append("\n# Selecting data and plotting for df{}".format(df_index+1))
            if self.opts['dfsFlavor'] in ['dict', 'list']:
                if self.opts['dfsFlavor'] == 'dict':
                    sDF_new = "dfs[tabNames[{}]]".format(df_index)
                else:
                    sDF_new = "dfs[{}]".format(df_index)
                if sDF_new != sDF:
                    sDF = sDF_new
                    script.append("df = "+sDF)
                sPlotXY ="df['{}'], df['{}']".format(column_x, column_y)
            elif self.opts['dfsFlavor'] == 'enumeration':
                sPlotXY ="df{}['{}'], df{}['{}']".format(df_index+1, column_x, df_index+1, column_y)

            if len(self.preplot_actions)>0:
                #script.append("x, y = preproXY({})".format(sPlotXY))
                sPlotXY="*preproXY({}), ".format(sPlotXY)
                #sPlotXY='x, y, '
            else:
                sPlotXY=sPlotXY+', '

            # --- Plot
            label =column_y.replace('_',' ') # TODO for table comparison
            plotLine = "ax.plot("
            plotLine += sPlotXY
            #if len(plotStyle['LineStyles'])>0:
            plotLine += "ls=stys[{}], ".format(iPDPos)
            plotLine += "lw=lw, "
            if len(plotStyle['Markers'])==1 and len(plotStyle['Markers'][0])>0:
                plotLine += "ms=ms, marker={}, ".format(plotStyle['Markers'][0])
            elif len(plotStyle['Markers'])>1:
                plotLine += "ms=ms, marker=mrks[{}], ".format(iPDPos)
            plotLine += "label='{}')".format(label)
            script.append(plotLine)

        k=0
        for i in range(self.subPlots['i']):
            for j in range(self.subPlots['j']):
                xlab = self.subPlots['x_labels'][k]
                ylab = self.subPlots['y_labels'][k]
                if len(xlab.strip())>0:
                    script.append(getAxesString(i,j)+".set_xlabel('{}')".format(xlab))
                if len(ylab.strip())>0:
                    script.append(getAxesString(i,j)+".set_ylabel('{}')".format(ylab))
                if self.subPlots['hasLegend'][k]:
                    script.append(getAxesString(i,j)+".legend(loc='{}')".format(plotStyle['LegendPosition'].lower()))
                k+=1

        # --- Parameters common to all axes
        if noSubplot:
            indent = indent0
        else:
            script.append(indent0 + "for ax in axes.flatten():")
            indent = indent1
        if plotStyle['grid']:
            script.append(indent + "ax.grid()")
        if plotStyle['logX']:
            script.append(indent + "ax.set_xscale('log', nonpositive='clip')")
        if plotStyle['logY']:
            script.append(indent + "ax.set_yscale('log', nonpositive='clip')")
        #script.append("ax.legend()")
        if pltshow:
            script.append("plt.show()")

        return "\n".join(script)


    def run(self, script=None, method='subprocess', pltshow=True, scriptName='./_pydatview_temp_script.py', tempDir=True):
        if script is None:
            script = self.generate(pltshow=pltshow)
        import tempfile
        import subprocess
        import os
        errors=[]

        if method=='subprocess':
            try:
                # --- Create a temporary file
                if tempDir:
                    temp_dir = tempfile.TemporaryDirectory()
                    script_file_path = os.path.join(temp_dir.name, scriptName)
                else:
                    script_file_path = scriptName
                with open(script_file_path, "w") as script_file:
                    script_file.write(script)


                # Run the script as a system call
                result = subprocess.run(["python", script_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                #result = subprocess.run(["python", '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # Print the output and errors (if any)
                #errors.append("Script Output:")
                #errors.append(result.stdout)
                if len(result.stderr)>0:
                    errors.append(result.stderr)
            except Exception as e:
                errors.append(f"An error occurred: {e}")
            finally:
                # Clean up by deleting the temporary directory and its contents
                if len(errors)==0:
                    try:
                        os.remove(script_file_path)
                        if tempDir:
                            temp_dir.cleanup()
                    except:
                        print('[FAIL] Failed to remove {}'.format(script_file_path))
        else:
            raise NotImplementedError()
        if len(errors)>0:
            raise Exception('\n'.join(errors))




if __name__ == '__main__':
    # Example usage:
    import os
    scriptDir =os.path.dirname(__file__)
    scripter = PythonScripter()
#     scripter.setFiles([os.path.join(scriptDir, '../DampingExplodingExample.csv')])
    scripter.setFiles([os.path.join(scriptDir, '../_TestFiles/CT_1.10.outb')])

    # --- Data Action
    imports = ["import numpy as np", "import scipy.stats as stats"]
    _code = """df = df"""
    code_init="""data={}; data['Misc']=2 # That's a parameter
data['Misc2']=3 # That's another parameter"""
    scripter.addAction('filter', _code, imports, code_init)

    # --- PrePlot Action
    _code="""x = x * 1\ny = y * 1"""
    scripter.addPreplotAction('Scaling', _code)

    # --- Adder Action
    imports = ["from pydatview.plugins.data_radialavg import radialAvg"]
    imports += ["from pydatview.Tables import Table"]
    _code = """
tab=Table(data=df)
dfs_new, names_new = radialAvg(tab, dataRadial)
"""
    code_init="""dataRadial={'avgMethod':'constantwindow', 'avgParam': 2}"""
    scripter.addAdderAction('radialAvg', _code, imports, code_init)


    # --- Formula
    scripter.addFormula(0, name='Time2', formula="df['Time_[s]']*20")


    #scripter.selectData(0, "Time", "TTDspFA")
    #scripter.selectData(0, "Time2", "TTDspFA")
#     scripter.selectData(0, "Time2", "Wind1VelX_[m/s]")
    scripter.selectData(1, "i/n_[-]", "B1Cl_[-]")

    plot_params = {
        'figsize': (8, 6),
        'xlabel': 'X-Axis',
        'ylabel': 'Y-Axis',
        'title': 'Sample Plot',
        'label': 'Data Series',
    }

    scripter.setPlotParameters(plot_params)


#     scripter.setFlavor(libFlavor='welib', dfsFlavor='dict')
    scripter.setOptions(libFlavor='pydatview', dfsFlavor='dict', oneTabPerFile=False)
#     scripter.setOptions(libFlavor='welib', dfsFlavor='list', oneTabPerFile=True)
#     scripter.setOptions(libFlavor='welib', dfsFlavor='enumeration', oneTabPerFile=True)
    scripter.setOptions(libFlavor='welib', dfsFlavor='enumeration', oneTabPerFile=False)
    script = scripter.generate()
    print(script)
    scripter.run()
    import matplotlib.pyplot as plt
    plt.show()

