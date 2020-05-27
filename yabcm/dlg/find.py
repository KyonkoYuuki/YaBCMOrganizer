import re

import wx

from pubsub import pub
from pyxenoverse.bcm import BCMEntry
from pyxenoverse.gui import get_first_item, get_next_item
from pyxenoverse.gui.ctrl.hex_ctrl import HexCtrl
from pyxenoverse.gui.ctrl.single_selection_box import SingleSelectionBox
from pyxenoverse.gui.ctrl.multiple_selection_box import MultipleSelectionBox

pattern = re.compile(r'([ \n/_])([a-z0-9]+)')
BLACK_LIST = ['address', 'sibling', 'child', 'parent', 'root']


class FindDialog(wx.Dialog):
    def __init__(self, parent, entry_list, *args, **kw):
        super().__init__(parent, *args, **kw, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        self.entry_list = entry_list
        self.SetTitle("Find")

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.hsizer = wx.BoxSizer()
        self.sizer.Add(self.hsizer)
        self.choices = [attr for attr in BCMEntry.__fields__ if attr not in BLACK_LIST]

        self.entry = wx.Choice(self, -1, choices=self.choices)

        # Setup Selections
        self.entry.SetSelection(1)

        self.find_ctrl = wx.TextCtrl(self, -1, '', size=(150, -1), style=wx.TE_PROCESS_ENTER)
        self.find_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_find)
        self.find_ctrl.SetFocus()

        self.grid_sizer = wx.FlexGridSizer(rows=3, cols=2, hgap=10, vgap=10)
        self.grid_sizer.Add(wx.StaticText(self, -1, 'Entry: '))
        self.grid_sizer.Add(self.entry, 0, wx.EXPAND)
        self.grid_sizer.Add(wx.StaticText(self, -1, 'Find: '))
        self.grid_sizer.Add(self.find_ctrl, 0, wx.EXPAND)
        self.hsizer.Add(self.grid_sizer, 0, wx.ALL, 10)

        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.find_button = wx.Button(self, -1, "Find Next")
        self.find_button.Bind(wx.EVT_BUTTON, self.on_find)

        self.button_sizer.Add(self.find_button, 0, wx.ALL, 2)
        self.button_sizer.Add(wx.Button(self, wx.ID_CANCEL, "Cancel"), 0, wx.ALL, 2)
        self.hsizer.Add(self.button_sizer, 0, wx.ALL, 8)

        self.status_bar = wx.StatusBar(self)
        self.sizer.Add(self.status_bar, 0, wx.EXPAND)

        self.Bind(wx.EVT_SHOW, self.on_show)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        self.SetAutoLayout(0)

    def on_show(self, e):
        if not e.IsShown():
            return
        try:
            ctrl = self.FindFocus()
            if type(ctrl.GetParent()) in (wx.SpinCtrlDouble, SingleSelectionBox, MultipleSelectionBox):
                ctrl = ctrl.GetParent()
            elif type(ctrl.GetParent().GetParent()) in (SingleSelectionBox, MultipleSelectionBox):
                ctrl = ctrl.GetParent().GetParent()
            name = pattern.sub(r'_\2', ctrl.GetName().lower())
            try:
                self.entry.SetSelection(self.choices.index(name))
                if type(ctrl) in (HexCtrl, SingleSelectionBox, MultipleSelectionBox):
                    self.find_ctrl.SetValue(f'0x{ctrl.GetValue():X}')
                else:
                    self.find_ctrl.SetValue(str(ctrl.GetValue()))
            except ValueError:
                pass
        except AttributeError:
            pass

    def select_found(self, item, entry_type):
        # Select found item
        self.entry_list.UnselectAll()
        self.entry_list.SelectItem(item)

        # If not visible, scroll to it
        if not self.entry_list.IsVisible(item):
            self.entry_list.ScrollTo(item)

        # Focus on entry
        pub.sendMessage('focus', entry=entry_type)
        self.SetFocus()
        self.status_bar.SetStatusText('')

    def find(self, selected, entry_type, find):
        if not selected.IsOk():
            self.status_bar.SetStatusText('No matches found')
            return
        item = get_next_item(self.entry_list, selected)
        while item != selected:
            data = self.entry_list.GetItemData(item)
            if data[entry_type] == find:
                self.select_found(item, entry_type)
                break

            item = get_next_item(self.entry_list, item)
            if not item.IsOk():
                item = get_first_item(self.entry_list)[0]
        else:
            self.status_bar.SetStatusText('No matches found')

    def on_find(self, _):
        entry_type = self.choices[self.entry.GetSelection()]
        value = self.find_ctrl.GetValue()
        if value:
            try:
                find = int(value, 0)
            except ValueError:
                self.status_bar.SetStatusText("Invalid Value")
                return
        else:
            find = None
        selected = self.entry_list.GetSelections()
        if len(selected) == 1 and selected[0] != self.entry_list.GetRootItem():
            selected = selected[0]
        else:
            selected = get_first_item(self.entry_list)[0]
        self.find(selected, entry_type, find)
