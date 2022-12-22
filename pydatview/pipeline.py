"""
pipelines and actions
"""
import numpy as np

class Action(): 
    # TODO: store data per table and for all
    def __init__(self, name, 
            tableFunctionApply = None,
            tableFunctionCancel = None,
            tableFunctionAdd   = None,
            plotDataFunction = None,
            guiCallback=None, 
            guiEditorClass=None,
            data=None,
            mainframe=None,
            onPlotData=False, unique=True, removeNeedReload=False):
        """ 
        tableFunction:    signature: f(tab)               # TODO that's inplace
        plotDataFunction: signature: xnew, ynew = f(x, y, data) 
        # TODO 

        """

        self.name = name
        # 
        self.tableFunctionAdd    = tableFunctionAdd      # applies to a full table, create a new one
        self.tableFunctionApply  = tableFunctionApply    # applies to a full table
        self.tableFunctionCancel = tableFunctionCancel   # cancel action on a full table
        self.plotDataFunction    = plotDataFunction      # applies to x,y arrays only

        self.guiCallback = guiCallback       # callback to update GUI after the action, 
                                             # TODO remove me, replace with generic "redraw", "update tab list"
        self.guiEditorClass = guiEditorClass # Class that can be used to edit this action
        self.guiEditorObj   = None           # Instance of guiEditorClass that can be used to edit this action

        self.mainframe=mainframe # If possible, dont use that...

        # TODO this needs to be stored per table 
        self.data = data if data is not None else {} # Data needed by the action, can be saved to file so that the action can be restored
        self.applied=False # TODO this needs to be sotred per table

        # Behavior
        self.onPlotData       = onPlotData # True for plotDataActions...
        self.unique           = unique
        self.removeNeedReload = removeNeedReload

        self.errorList=[]

    def apply(self, tabList, force=False, applyToAll=False):
        self.errorList=[]
        if self.tableFunctionApply is None:
            # NOTE: this does not applyt to plotdataActions..
            raise Exception('tableFunction was not specified for action: {}'.format(self.name))

        if tabList is None:
            raise Exception('{}: cannot apply on None tabList'.format(self))

        for t in tabList:
            print('>>> Applying action', self.name, 'to', t.name)
            try:
                self.tableFunctionApply(t, data=self.data)
            except:
                err = 'Failed to apply action {} to table {}.'.format(self.name, t.name)
                self.errorList.append(err)

        self.applied = True
        return tabList


    def applyAndAdd(self, tabList):
        """ 
        Loop through tabList, perform the action and create new tables
        """
        if self.tableFunctionAdd is None:
            raise Exception('tableFunctionAdd was not specified for action: {}'.format(self.name))

        dfs_new   = []
        names_new = []
        errors=[]
        for i,t in enumerate(tabList):
#             try:
            df_new, name_new = self.tableFunctionAdd(t, self.data)
            if df_new is not None: 
                # we don't append when string is empty
                dfs_new.append(df_new)
                names_new.append(name_new)
#             except:
#                 errors.append('Resampling failed for table: '+t.active_name) # TODO
        return dfs_new, names_new, errors




    def updateGUI(self):
        """ Typically called by a callee after append"""
        if self.guiCallback is not None:
            print('>>> Action: Calling GUI callback, action', self.name)
            self.guiCallback()

    def __repr__(self):
        s='<Action {}>'.format(self.name)
        return s


# --------------------------------------------------------------------------------}
# --- Plot data actions (applied on the fly)
# --------------------------------------------------------------------------------{
# TODO: handle how they generate new tables
# TODO: handle how they are applied to few tables
class PlotDataAction(Action): 
    def __init__(self, name, **kwargs):
        Action.__init__(self, name, onPlotData=True, **kwargs)

    def apply(self, *args, **kwargs):
        pass # nothing to do

    def cancel(self, *args, **kwargs):
        pass # nothing to do

    def applyOnPlotData(self, x, y, tabID):
        # TODO apply only based on tabID 
        x, y = self.plotDataFunction(x, y, self.data)
        return x, y

    def __repr__(self):
        s='<PlotDataAction {}>'.format(self.name, self.applied)
        return s
# --------------------------------------------------------------------------------}
# --- Table actions (apply on a full table)
# --------------------------------------------------------------------------------{
# TODO: store data per table and for all
class IrreversibleTableAction(Action): 

    def __init__(self, name, **kwargs):
        Action.__init__(self, name, removeNeedReload=True, **kwargs)

    def apply(self, tabList, force=False, applyToAll=False):
        if force:
            self.applied = False
        if self.applied:
            print('>>> Action: Skipping irreversible action', self.name)
            return
        Action.apply(self, tabList)

    def cancel(self, *args, **kwargs):
        print('>>> Action: Cancel: skipping irreversible action', self.name)
        pass
    
    def __repr__(self):
        s='<IrreversibleAction {} (applied:{})>'.format(self.name, self.applied)
        return s

class ReversibleTableAction(Action): 

    def __init__(self, name, tableFunctionApply, tableFunctionCancel, **kwargs):
        Action.__init__(self, name, tableFunctionApply=tableFunctionApply, tableFunctionCancel=tableFunctionCancel, **kwargs)

    def apply(self, tabList, force=False, applyToAll=False):
        if force:
            self.applied = False
        if self.applied:
            print('>>> Action: Apply: Skipping irreversible action', self.name)
            return
        Action.apply(self, tabList)

    def cancel(self, tabList):
        self.errorList=[]
        if tabList is None:
            print('[WARN] Cannot cancel action {} on None tablist'.format(self))
            return
        for t in tabList:
            print('>>> Action: Cancel: ', self, 'to', t.name)
            try:
                self.tableFunctionCancel(t, data=self.data)
            except:
                self.errorList.append('Failed to apply action {} to table {}.'.format(self.name, t.name))
    
    def __repr__(self):
        s='<ReversibleTableAction {} (applied:{})>'.format(self.name, self.applied)
        return s


# --------------------------------------------------------------------------------}
# --- Pipeline 
# --------------------------------------------------------------------------------{
class Pipeline(object): 

    def __init__(self, data=[]):
        self.actionsData = []
        self.actionsPlotFilters = []
        self.errorList   = []
        self.plotFiltersData=[] # list of data for plot data filters, that plotData.py will use

    @property
    def actions(self):
        return self.actionsData+self.actionsPlotFilters # order matters

    def apply(self, tabList, force=False, applyToAll=False):
        """ 
        Apply the pipeline to the tabList
        If "force", then actions that are "one time only" are still applied
        If applyToAll, then the action is applied to all the tables, irrespectively of the tabList stored by the action
        """
        for action in self.actionsData:
            action.apply(tabList, force=force, applyToAll=applyToAll)
        # 
        for action in self.actionsPlotFilters:
            action.apply(tabList, force=force, applyToAll=applyToAll)
        # 
        self.collectErrors()


    def applyOnPlotData(self, x, y, tabID):
        x = np.copy(x)
        y = np.copy(y)
        for action in self.actionsPlotFilters:
            x, y = action.applyOnPlotData(x, y, tabID)
        return x, y

    def collectErrors(self):
        self.errorList=[]
        for action in self.actions:
            self.errorList+= action.errorList

    # --- Behave like a list..
    def append(self, action, overwrite=False, apply=True, updateGUI=True, tabList=None):
        i = self.index(action)
        if i>=0 and not overwrite:
            print('[Pipe] Not adding action, its already present')
        else:
            if action.onPlotData:
                self.actionsPlotFilters.append(action)
            else:
                self.actionsData.append(action)

        if apply:
            action.apply(tabList=tabList, force=True)
            self.collectErrors()

        # trigger GUI update (guiCallback)
        if updateGUI:
            action.updateGUI()


    def remove(self, a, cancel=True, updateGUI=True, tabList=None):
        """ NOTE: the action is removed, not deleted fully (it might be readded to the pipeline later)
         -  If a GUI edtor is attached to this action, we make sure that it shows the action as cancelled
        """
        try:
            i = self.actionsData.index(a)
            a = self.actionsData.pop(i)
        except ValueError:
            i = self.actionsPlotFilters.index(a)
            a = self.actionsPlotFilters.pop(i)

        # Cancel the action
        if cancel:
            a.cancel(tabList)
            self.collectErrors()

        # Cancel the action in Editor
        print('>>> GUI EDITOR', a.guiEditorObj)
        if a.guiEditorObj is not None:
            print('[Pipe] Canceling action in guiEditor because the action is removed')
            a.guiEditorObj.cancelAction() # NOTE: should not trigger a plot

        # trigger GUI update (guiCallback)
        if updateGUI:
            a.updateGUI()

        return a

    def find(self, name):
        for action in self.actions:
            if action.name==name:
                return action
        return None

    def index(self, action_):
        for i, action in enumerate(self.actions):
            if action==action_:
                return i
        else:
            return -1

    # --- Data/Options 
    def loadFromFile(self, filename):
        pass

    def saveToFile(self, filename):
        pass

    def loadData(self, data):
        pass

    def saveData(self, data):
        data['actionsData'] = {}
        data['actionsPlotFilters'] = {}
        for ac in self.actionsData:
            data['actionsData'][ac.name] = ac.data
        for ac in self.actions:
            data['actionsPlotFilters'][ac.name] = ac.data
        #data[] = self.Naming
        
    @staticmethod
    def defaultData():
        return {}

    def __repr__(self):
        s='<Pipeline>: '
        s+=' > '.join([ac.name for ac in self.actionsData])
        s+=' + '
        s+=' > '.join([ac.name for ac in self.actionsPlotFilters])
        return s
    def __reprFilters__(self):
        s='<PipelineFilters>: '
        s+=' > '.join([ac.name for ac in self.actionsPlotFilters])
        return s



