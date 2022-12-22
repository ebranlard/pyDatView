"""
pipelines and actions
"""
import numpy as np

class Action(): 
    def __init__(self, name, 
            tableFunction    = None,
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
        self.tableFunction    = tableFunction    # applies to a full table
        self.plotDataFunction = plotDataFunction # applies to x,y arrays only

        self.guiCallback = guiCallback       # callback to update GUI after the action, 
                                             # TODO remove me, replace with generic "redraw", "update tab list"
        self.guiEditorClass = guiEditorClass # Class that can be used to edit this action
        self.guiEditorObj   = None           # Instance of guiEditorClass that can be used to edit this action

        self.data = data if data is not None else {} # Data needed by the action, can be saved to file so that the action can be restored
        self.mainframe=mainframe # If possible, dont use that...

        self.applied=False # TODO this needs to be sotred per table

        # Behavior
        self.onPlotData       = onPlotData
        self.unique           = unique
        self.removeNeedReload = removeNeedReload

        self.errorList=[]

    def apply(self, tablist, force=False, applyToAll=False):
        self.errorList=[]
        if self.tableFunction is None:
            # NOTE: this does not applyt to plotdataActions..
            raise Exception('tableFunction was not specified for action: {}'.format(self.name))

        for t in tablist:
            print('>>> Applying action', self.name, 'to', t.name)
            try:
                self.tableFunction(t)
            except e:
                err = 'Failed to apply action {} to table {}.'.format(self.name, t.name)
                self.errorList.append(e)

        self.applied = True
        return tablist


    def updateGUI(self):
        """ Typically called by a calleed after append"""
        if self.guiCallback is not None:
            print('>>> Calling GUI callback, action', self.name)
            self.guiCallback()

    def __repr__(self):
        s='<Action {}>'.format(self.name)
        return s


class PlotDataAction(Action): 
    def __init__(self, name, **kwargs):
        Action.__init__(self, name, onPlotData=True, **kwargs)

    def apply(self, *args, **kwargs):
        pass # not pretty

    def applyOnPlotData(self, x, y):
        x, y = self.plotDataFunction(x, y, self.data)
        return x, y

class IrreversibleAction(Action): 

    def __init__(self, name, **kwargs):
        Action.__init__(self, name, removeNeedReload=True, **kwargs)

    def apply(self, tablist, force=False, applyToAll=False):
        if force:
            self.applied = False
        if self.applied:
            print('>>> Skipping irreversible action', self.name)
            return
        Action.apply(self, tablist)
    
    def __repr__(self):
        s='<IrreversibleAction {}, applied: {}>'.format(self.name, self.applied)
        return s

class FilterAction(Action): 
    def cancel(self, tablist):
        raise NotImplementedError()
        return tablist


class Pipeline(object): 

    def __init__(self, data=[]):
        self.actionsData = []
        self.actionsPlotFilters = []
        self.errorList   = []
        self.plotFiltersData=[] # list of data for plot data filters, that plotData.py will use

    @property
    def actions(self):
        return self.actionsData+self.actionsPlotFilters # order matters

    def apply(self, tablist, force=False, applyToAll=False):
        """ 
        Apply the pipeline to the tablist
        If "force", then actions that are "one time only" are still applied
        If applyToAll, then the action is applied to all the tables, irrespectively of the tablist stored by the action
        """
        for action in self.actionsData:
            action.apply(tablist, force=force, applyToAll=applyToAll)
        # 
        for action in self.actionsPlotFilters:
            action.apply(tablist, force=force, applyToAll=applyToAll)
        # 
        self.collectErrors()


    def applyOnPlotData(self, x, y):
        x = np.copy(x)
        y = np.copy(y)
        for action in self.actionsPlotFilters:
            x, y = action.applyOnPlotData(x, y)
        return x, y



    def collectErrors(self):
        self.errorList=[]
        for action in self.actions:
            self.errorList+= action.errorList

#     def setPlotFiltersData(self):
#         print('>>> Setting plotFiltersData')
#         self.plotFiltersData=[]
#         for action in self.actionsPlotFilters:
#             self.plotFiltersData.append(action.data)
#             print(action.data)

    # --- Behave like a list..
    def append(self, action, cancelIfPresent=False):
        if cancelIfPresent:
            i = self.index(action)
            if i>=0:
                print('>>> Not adding action, its already present')
                return
        if action.onPlotData:
            self.actionsPlotFilters.append(action)
            # Trigger
#             self.setPlotFiltersData()
        else:
            self.actionsData.append(action)


    def remove(self, a):
        """ NOTE: the action is removed, not deleted fully (it might be readded to the pipeline later)"""
        try:
            i = self.actionsData.index(a)
            a = self.actionsData.pop(i)
        except ValueError:
            i = self.actionsPlotFilters.index(a)
            a = self.actionsPlotFilters.pop(i)
            # Trigger
#             self.setPlotFiltersData()

        # Cancel the action in Editor
        if a.guiEditorObj is not None:
            print('>>> Canceling action in guiEditor')
            a.guiEditorObj.cancelAction()

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



