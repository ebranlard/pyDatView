"""
pipelines and actions
"""

class Action(): 
    def __init__(self, name, 
            tableFunction=None, guiCallBack=None, 
            guiEditorClass=None,
            data=None,
            mainframe=None,
            onPlotData=False, unique=True, removeNeedReload=False):

        self.name = name
        # 
        self.tableFunction = tableFunction

        self.guiCallBack = guiCallBack
        self.guiEditorClass = guiEditorClass # Class that can be used to edit this action

        self.data = data if data is not None else {}
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
        if self.guiCallBack is not None:
            print('>>> Calling GUI callback, action', self.name)
            self.guiCallBack()

    def __repr__(self):
        s='<Action {}>'.format(self.name)
        return s


class PlotDataAction(Action): 
    def __init__(self, name, **kwargs):
        Action.__init__(self, name, onPlotData=True, **kwargs)

    def applyOnPlotData(self):
        print('>>> Apply On Plot Data')

class IrreversibleAction(Action): 

    def __init__(self, name, **kwargs):
        Action.__init__(self, name, deleteNeedReload=True, **kwargs)

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
        self.actionsPlot = []
        self.errorList   = []

    @property
    def actions(self):
        return self.actionsData+self.actionsPlot # order matters

    def apply(self, tablist, force=False, applyToAll=False):
        """ 
        Apply the pipeline to the tablist
        If "force", then actions that are "one time only" are still applied
        If applyToAll, then the action is applied to all the tables, irrespectively of the tablist stored by the action
        """
        for action in self.actionsData:
            action.apply(tablist, force=force, applyToAll=applyToAll)
        # 
        for action in self.actionsPlot:
            action.apply(tablist, force=force, applyToAll=applyToAll)
        # 
        self.collectErrors()

    def collectErrors(self):
        self.errorList=[]
        for action in self.actions:
            self.errorList+= action.errorList

    # --- Behave like a list..
    def append(self, action):
        if action.onPlotData:
            self.actionsPlot.append(action)
        else:
            self.actionsData.append(action)

    def remove(self, a):
        """ NOTE: the action is removed, not deleted fully (it might be readded to the pipeline later)"""
        try:
            i = self.actionsData.index(a)
            a = self.actionsData.pop(i)
        except ValueError:
            i = self.actionsPlot.index(a)
            a = self.actionsPlot.pop(i)
        return a

    def find(self, name):
        for action in self.actions:
            if action.name==name:
                return action
        return None

    # --- Data/Options 
    def loadFromFile(self, filename):
        pass

    def saveToFile(self, filename):
        pass

    def loadData(self, data):
        pass

    def saveData(self, data):
        data['actionsData'] = {}
        data['actionsPlot'] = {}
        for ac in self.actionsData:
            data['actionsData'][ac.name] = ac.data
        for ac in self.actions:
            data['actionsPlot'][ac.name] = ac.data
        #data[] = self.Naming
        
    @staticmethod
    def defaultData():
        return {}

    def __repr__(self):
        s='<Pipeline>: '
        s+=' > '.join([ac.name for ac in self.actionsData])
        s+=' + '
        s+=' > '.join([ac.name for ac in self.actionsPlot])
        return s


