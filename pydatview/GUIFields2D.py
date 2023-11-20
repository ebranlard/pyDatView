""" 
"""
import os
import numpy as np
import wx
from wx.lib.splitter import MultiSplitterWindow
# Local
from pydatview.common import ellude_common
from pydatview.common import CHAR
from pydatview.GUICommon import getMonoFont
from pydatview.Fields2D import extract2Dfields
from pydatview.GUIPlot2DPanel import Plot2DPanel

# --------------------------------------------------------------------------------}
# --- Fields 2D Panel 
# --------------------------------------------------------------------------------{
class Fields2DPanel(wx.Panel):
    def __init__(self, parent, mainframe):
        wx.Panel.__init__(self, parent)
        # Data
        self.parent = parent
        self.mainframe = mainframe
        self.fileobjects = None

        multi_split = MultiSplitterWindow(self)
        self.files_panel = wx.Panel(multi_split)
        self.fields_panel = wx.Panel(multi_split)
        self.canvas_panel = Plot2DPanel(multi_split)

        # GUI
        self.btExtractFields = wx.Button(self.files_panel, label=CHAR['compute']+' '+"Extract 2D fields for all", style=wx.BU_EXACTFIT)
        self.textArgs   = wx.TextCtrl(self.files_panel, wx.ID_ANY, '', style = wx.TE_PROCESS_ENTER)
        self.lbFiles = wx.ListBox(self.files_panel, style=wx.LB_EXTENDED)
        self.lbFields = wx.ListBox(self.fields_panel, style=wx.LB_EXTENDED)
        self.textArgs.SetValue('DeltaAzi=10')
        self.lbFiles.SetFont(getMonoFont(self))
        self.lbFields.SetFont(getMonoFont(self))
        self.textArgs.SetFont(getMonoFont(self))

        # Layout
        sizer_files = wx.BoxSizer(wx.VERTICAL)
        sizer_files.Add(self.textArgs, 0, wx.EXPAND | wx.ALL, 1)
        sizer_files.Add(self.btExtractFields, 0, wx.EXPAND | wx.ALL, 1)
        sizer_files.Add(self.lbFiles, 1, wx.EXPAND | wx.ALL, 1)
        self.files_panel.SetSizer(sizer_files)

        sizer_fields = wx.BoxSizer(wx.VERTICAL)
        sizer_fields.Add(self.lbFields, 1, wx.EXPAND | wx.ALL, 1)
        self.fields_panel.SetSizer(sizer_fields)

        multi_split.AppendWindow(self.files_panel, 200)
        multi_split.AppendWindow(self.fields_panel, 200)
        multi_split.AppendWindow(self.canvas_panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(multi_split, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Bind
        self.lbFiles.Bind(wx.EVT_LISTBOX, self.on_file_selected)
        self.lbFields.Bind(wx.EVT_LISTBOX, self.on_2d_field_selected)
        self.btExtractFields.Bind(wx.EVT_BUTTON, self.onExtract)
        #self.textArgs.Bind(wx.EVT_TEXT_ENTER, self.onParamChangeEnter)

    def cleanGUI(self, event=None):
        self.lbFiles.Clear()
        self.lbFields.Clear()

    def deselect(self, event=None):
        [self.lbFiles.Deselect(i) for i in self.lbFiles.GetSelections()]

    def updateFiles(self, filenames, fileobjects):
        self.fileobjects=fileobjects
        filenames = [os.path.abspath(f).replace('/','|').replace('\\','|') for f in filenames]
        filenames = ellude_common(filenames)
        self.lbFiles.Set(filenames)
        #self.lbFiles.SetSelection(0)
        #self.on_file_selected()

    def getArgs(self):
        args = self.textArgs.GetValue().split(',')
        kwargs={}
        for arg in args:
            k, v = arg.split('=')
            kwargs[k.strip()] = v.strip()
        #print('kwargs',kwargs)
        return kwargs

    def onExtract(self, event=None):
        self.deselect()
        kwargs = self.getArgs()
        for fo in self.fileobjects:
            extract2Dfields(fo, force=True, **kwargs)

    def on_file_selected(self, event=None):
        ISelF = self.lbFiles.GetSelections()
        kwargs = self.getArgs()
        # --- Compute if not done yet
        for iself in ISelF:
            file_object = self.fileobjects[iself]
            if not hasattr(file_object, 'fields2D_tmp'):
                # Computing fields here if not already done for this file
                fields = extract2Dfields(file_object, **kwargs)
            else:
                fields  = file_object.fields2D_tmp

        iself = ISelF[0]
        fieldListByTable=[]
        for iself in ISelF:
            fields  = file_object.fields2D_tmp
            if fields is not None:
                fields_list =[]
                for ifield, field in enumerate(fields):
                    for c,_ in field['Fields'].items():
                        fields_list.append(str(ifield) + '_' + field['name'] +'_' + c)
                fieldListByTable.append(fields_list)
            else:
                print('[WARN] No 2D fields for this file')

        # --- Get common columns
        if len(fieldListByTable)>0:
            commonCols = fieldListByTable[0]
            for i in np.arange(1,len(fieldListByTable)):
                commonCols = list( set(commonCols) & set( fieldListByTable[i]))
            # Respect order of first 
            commonCols = [c for c in fieldListByTable[0] if c in commonCols]
            #commonCols.sort()
            self.lbFields.Set(commonCols)
        else:
            print('[WARN] No 2D fields')


    def on_2d_field_selected(self, event=None):
        ISelF = self.lbFiles.GetSelections()
        self.canvas_panel.fields=[]

        for iself in ISelF :
            file_object = self.fileobjects[iself]
            ISelC = self.lbFields.GetSelections()

            for iselc in ISelC:
                sfield = self.lbFields.GetString(iselc)
                sp = sfield.split('_')
                i = int(sp[0])
                kind = sp[1]
                col = '_'.join(sp[2:])

                field = file_object.fields2D_tmp[i]
                if field is not None:
                    sx, x = field['x']
                    sy, y = field['y']
                    try:
                        M = field['Fields'][col]
                        self.canvas_panel.add_field(x, y, M, sx, sy, fieldname=col)
                    except:
                        print('[FAIL] field {} for present in file {}'.format(col, file_object.filename))
                    #self.canvas_panel.plot_field(x, y, M, sx, sy, fieldname=col)
        self.canvas_panel.update_plot()




