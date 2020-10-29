import wx
from pubsub import pub

from pyxenoverse.gui import get_first_item, get_next_item
from yabcm.dlg.find import FindDialog


class ReplaceDialog(FindDialog):
    def __init__(self, parent, entry_list, *args, **kw):
        super().__init__(parent, entry_list, *args, **kw)
        self.SetTitle("Replace")

        self.replace_ctrl = wx.TextCtrl(self, -1, '', style=wx.TE_PROCESS_ENTER)
        self.replace_ctrl.MoveAfterInTabOrder(self.find_ctrl)

        self.grid_sizer.Add(wx.StaticText(self, -1, 'Replace: '))
        self.grid_sizer.Add(self.replace_ctrl, 0, wx.EXPAND)

        self.replace_button = wx.Button(self, -1, "Replace")
        self.replace_button.Bind(wx.EVT_BUTTON, self.on_replace)
        self.replace_button.MoveAfterInTabOrder(self.find_button)
        self.replace_all_button = wx.Button(self, -1, "Replace All")
        self.replace_all_button.Bind(wx.EVT_BUTTON, self.on_replace_all)
        self.replace_all_button.MoveAfterInTabOrder(self.replace_button)

        self.button_sizer.Insert(1, self.replace_button, 0, wx.ALL, 2)
        self.button_sizer.Insert(2, self.replace_all_button, 0, wx.ALL, 2)

        self.sizer.Fit(self)
        self.Layout()

    def on_replace(self, _):
        entry_type = self.choices[self.entry.GetSelection()]
        try:
            find = self.get_value(self.find_ctrl)
            replace = self.get_value(self.replace_ctrl)
        except ValueError:
            self.status_bar.SetStatusText("Invalid Value")
            return None
        selected = self.entry_list.GetSelection()
        data = self.entry_list.GetItemData(selected)

        # Check to see if current entry is not one we're looking for
        if data[entry_type] == find:
            data[entry_type] = replace
            pub.sendMessage('on_select', _=None)
            pub.sendMessage('focus_on', entry=entry_type)
            self.status_bar.SetStatusText('Replaced 1 entry')
            self.SetFocus()
        self.find(selected, entry_type, find)

    def on_replace_all(self, _):
        entry_type = self.choices[self.entry.GetSelection()]
        try:
            find = self.get_value(self.find_ctrl)
            replace = self.get_value(self.replace_ctrl)
        except ValueError:
            self.status_bar.SetStatusText("Invalid Value")
            return None
        count = 0
        item = get_first_item(self.entry_list)[0]
        while item.IsOk():
            data = self.entry_list.GetItemData(item)
            if data[entry_type] == find or (
                    isinstance(data[entry_type], float) and abs(data[entry_type] - find) < 0.000001):
                data[entry_type] = replace
                count += 1
            item = get_next_item(self.entry_list, item)
        pub.sendMessage('on_select', _=None)
        self.status_bar.SetStatusText(f'Replaced {count} entry(s)')
