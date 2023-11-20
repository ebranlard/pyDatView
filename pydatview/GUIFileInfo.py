""" 

"""
import os
import inspect
import wx
from wx.lib.splitter import MultiSplitterWindow
import wx.stc as stc
# Local
from pydatview.common import ellude_common

class FileInfoPanel(wx.Panel):
    def __init__(self, parent, mainframe, filelist=None):
        wx.Panel.__init__(self, parent)
        # Data
        self.parent = parent
        self.mainframe = mainframe
        self.fileobjects = None
        # GUI
        multi_split = MultiSplitterWindow(self)
        self.list_panel    = wx.Panel(multi_split)
        self.methods_panel = wx.Panel(multi_split) # Added panel for methods, attributes, and keys
        self.text_panel    = wx.Panel(multi_split)

        self.lbFiles = wx.ListBox(self.list_panel, style=wx.LB_SINGLE)
        self.lbFiles.Bind(wx.EVT_LISTBOX, self.on_file_selected)

        sizer_list = wx.BoxSizer(wx.VERTICAL)
        sizer_list.Add(self.lbFiles, 1, wx.EXPAND | wx.ALL, 1)
        self.list_panel.SetSizer(sizer_list)

        # Added list boxes for methods, attributes, and keys
        self.lbMethods = wx.ListBox(self.methods_panel, style=wx.LB_SINGLE)
        self.lbAttributes = wx.ListBox(self.methods_panel, style=wx.LB_EXTENDED) #, style=wx.LB_SINGLE)
        self.lbKeys = wx.ListBox(self.methods_panel, style=wx.LB_EXTENDED) #, style=wx.LB_SINGLE)

        # Static labels to explain the purpose of each list box
        label_methods = wx.StaticText(self.methods_panel, label="Methods:")
        label_attributes = wx.StaticText(self.methods_panel, label="Attributes:")
        label_keys = wx.StaticText(self.methods_panel, label="Keys:")

        # Bind events for methods, attributes, and keys
        self.lbMethods.Bind(wx.EVT_LISTBOX, self.on_method_selected)
        self.lbAttributes.Bind(wx.EVT_LISTBOX, self.on_attribute_selected)
        self.lbKeys.Bind(wx.EVT_LISTBOX, self.on_key_selected)

        sizer_methods = wx.BoxSizer(wx.VERTICAL)
        sizer_methods.Add(label_methods,    0, wx.EXPAND | wx.ALL, 1)
        sizer_methods.Add(self.lbMethods,   1, wx.EXPAND | wx.ALL, 1)
        sizer_methods.Add(label_attributes, 0, wx.EXPAND | wx.ALL, 1)
        sizer_methods.Add(self.lbAttributes, 1, wx.EXPAND | wx.ALL, 1)
        sizer_methods.Add(label_keys, 0, wx.EXPAND | wx.ALL, 1)
        sizer_methods.Add(self.lbKeys, 1, wx.EXPAND | wx.ALL, 1)
        self.methods_panel.SetSizer(sizer_methods)

        multi_split.AppendWindow(self.list_panel   , 200)
        multi_split.AppendWindow(self.methods_panel, 200)
        multi_split.AppendWindow(self.text_panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(multi_split, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Added TextCtrl "tb"
        #self.tb = wx.TextCtrl(self.text_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.tb = stc.StyledTextCtrl(self.text_panel, style=wx.TE_MULTILINE| wx.TE_READONLY)
        self.setup_textctrl()
        sizer_text = wx.BoxSizer(wx.HORIZONTAL)
        sizer_text.Add(self.tb, 1, wx.EXPAND | wx.ALL, 1)
        self.text_panel.SetSizer(sizer_text)

    def updateFiles(self, filenames, fileobjects):
        self.fileobjects = fileobjects
        filenames = [os.path.abspath(f).replace('/','|').replace('\\','|') for f in filenames]
        filenames = ellude_common(filenames)
        self.lbFiles.Set(filenames)
        self.lbFiles.SetSelection(0)
        self.on_file_selected()

        self.lbMethods.SetSelection(0)
        self.on_method_selected()

    def on_file_selected(self, event=None):
        isel = self.lbFiles.GetSelection()
        file_object = self.fileobjects[isel]

        # Show __repr__  in tb
        content = self.fileobjects[isel].__repr__()
        self.tb.SetValue(content)

        # --- Placeholder method to simulate obtaining data for the selected object

        # Populate lbMethods, lbAttributes, lbKeys with data
        #methods = getattr(file_object, "__dir__", None)() 
        methods = [name for name, member in inspect.getmembers(file_object, inspect.ismethod) if not isinstance(member, property)]

        methods = ['__repr__']+[m for m in methods if not m.startswith('_')]
        self.lbMethods.Set(methods)

        attributes = [attr for attr in dir(file_object) if not callable(getattr(file_object, attr))]
        attributes = [a for a in attributes if not a.startswith('_')]
        self.lbAttributes.Set(attributes)

        if isinstance(file_object, dict):
            keys = list(file_object.keys())
            self.lbKeys.Set(keys)
        else:
            self.lbKeys.Set([])

    def on_method_selected(self, event=None):
        [self.lbAttributes.Deselect(i) for i in self.lbAttributes.GetSelections()]
        [self.lbKeys.Deselect(i) for i in self.lbKeys.GetSelections()]
        selected_method = self.lbMethods.GetStringSelection()
        self.display_value_in_tb([selected_method], 'method')

    def on_attribute_selected(self, event=None):
        [self.lbKeys.Deselect(i) for i in self.lbKeys.GetSelections()]
        [self.lbMethods.Deselect(i) for i in self.lbMethods.GetSelections()]
        ISel = self.lbAttributes.GetSelections()
        selected_attributes = [self.lbAttributes.GetString(i) for i in ISel]
        self.display_value_in_tb(selected_attributes, 'attribute')

    def on_key_selected(self, event=None):
        [self.lbAttributes.Deselect(i) for i in self.lbAttributes.GetSelections()]
        [self.lbMethods.Deselect(i) for i in self.lbMethods.GetSelections()]
        ISel = self.lbKeys.GetSelections()
        selected_keys = [self.lbKeys.GetString(i) for i in ISel]
        self.display_value_in_tb(selected_keys, 'dict')

    def display_value_in_tb(self, keys, stype):
        isel = self.lbFiles.GetSelection()
        file_object = self.fileobjects[isel]
        content =''
        for key in keys:
            if stype=='method':
                #content = f"Value of {stype} {key}():\n"
                if key =='__repr__':
                    content += self.fileobjects[isel].__repr__()
                else:
                    content+=get_method_signature_and_docstring(file_object, key)
                #if key.lower().startswith('write'):
                #    content+= 'Skipping `write` to avoid overwriting..'
                #else:
                #    out = eval('file_object.{}()'.format(key))
                #    content+= '{}'.format(out)
            elif stype=='attribute':
                content+= f"#Value of {stype} {key}:\n"
                content+= '{}'.format(getattr(file_object, key))
            elif stype=='dict':
                content+= f"#Value of {stype} {key}:\n"
                content+= '{}'.format(file_object[key])
            content+='\n'
        self.tb.SetValue(content)

    def setup_textctrl(self):
        # --- Basic
        mono_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        #self.tb.SetFont(mono_font)
        #self.tb.StyleSetFont(stc.STC_STYLE_DEFAULT, mono_font)
        # self.tb.SetUseHorizontalScrollBar(False)
        # Remove the left margin (line number margin)
        #self.tb.SetMarginWidth(1, 0)  # Set the width of margin 1 (line number margin) to 0
        # --- Advanced 
        self.tb.StyleSetForeground(stc.STC_P_COMMENTLINE, wx.Colour(0, 128, 0))  # Comments (green)
        self.tb.StyleSetForeground(stc.STC_P_NUMBER, wx.Colour(123, 0, 0))  # Numbers (red)
        self.tb.StyleSetForeground(stc.STC_P_STRING   , wx.Colour(165, 32, 247))  # Strings
        self.tb.StyleSetForeground(stc.STC_P_CHARACTER, wx.Colour(165, 32, 247))  # Characters 
        self.tb.StyleSetForeground(stc.STC_P_WORD, wx.Colour(0, 0, 128))  # Keywords (dark blue)
        self.tb.StyleSetBold(stc.STC_P_WORD, True)  # Make keywords bold
        self.tb.SetLexer(stc.STC_LEX_PYTHON)  # Set the lexer for Python
        self.tb.StyleSetForeground(stc.STC_P_DEFAULT, wx.Colour(0, 0, 0))  # Default text color (black)
        self.tb.StyleSetBackground(stc.STC_P_DEFAULT, wx.Colour(255, 255, 255))  # Default background color (white)
        self.tb.StyleSetFont(stc.STC_STYLE_DEFAULT, mono_font)
        #self.tb.SetUseHorizontalScrollBar(False)
        # Remove the left margin (line number margin)
        self.tb.SetMarginWidth(1, 0)  # Set the width of margin 1 (line number margin) to 0

def get_method_signature_and_docstring(file_object, method_name):
    try:
        # Get the method object
        method = getattr(file_object, method_name)

        # Get the signature of the method
        signature = inspect.signature(method)

        # Get the docstring of the method
        docstring = inspect.getdoc(method)

        # Create the result string
        result = f"#Signature:\n{method_name}{signature}\n\n"
        if docstring:
            result += f"#Docstring:\n\"\"\"{docstring}\"\"\""
        else:
            result += "#No docstring available."

        return result
    except Exception as e:
        return f"Error: {e}"

