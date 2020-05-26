import wx
import pickle
from pyxenoverse.bcm import address_to_index, index_to_address, BCMEntry
from pyxenoverse.gui import get_next_item, get_first_item, get_item_index
from pubsub import pub


class MainPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent

        self.entry_list = wx.TreeCtrl(self, style=wx.TR_MULTIPLE | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_LINES_AT_ROOT)
        self.entry_list.Bind(wx.EVT_TREE_ITEM_MENU, self.on_right_click)
        self.entry_list.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select)
        self.cdo = wx.CustomDataObject("BCMEntry")

        self.append_id = wx.NewId()
        self.insert_id = wx.NewId()
        self.Bind(wx.EVT_MENU, self.on_delete, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.on_paste, id=wx.ID_PASTE)
        self.Bind(wx.EVT_MENU, self.on_add_child, id=wx.ID_ADD)
        self.Bind(wx.EVT_MENU, self.on_append, id=self.append_id)
        self.Bind(wx.EVT_MENU, self.on_insert, id=self.insert_id)
        accelerator_table = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('a'), self.append_id),
            (wx.ACCEL_CTRL, ord('i'), self.insert_id),
            (wx.ACCEL_CTRL, ord('n'), wx.ID_ADD),
            (wx.ACCEL_CTRL, ord('c'), wx.ID_COPY),
            (wx.ACCEL_CTRL, ord('v'), wx.ID_PASTE),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, wx.ID_DELETE),
        ])
        self.entry_list.SetAcceleratorTable(accelerator_table)

        pub.subscribe(self.on_select, 'on_select')

        # Use some sizers to see layout options
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.entry_list, 1, wx.ALL | wx.EXPAND, 10)

        # Layout sizers
        self.SetSizer(sizer)
        self.SetAutoLayout(1)

    def on_right_click(self, _):
        selections= self.entry_list.GetSelections()
        if not selections:
            return
        menu = wx.Menu()
        copy = menu.Append(wx.ID_COPY, "&Copy\tCtrl+C", "Copy entry")
        paste = menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V", "Paste entry")
        delete = menu.Append(wx.ID_DELETE, "&Delete\tDelete", "Delete entry(s)")
        append = menu.Append(self.append_id, "&Append\tCtrl+A", "Append entry after")
        insert = menu.Append(self.insert_id, "&Insert\tCtrl+I", "Insert entry before")
        menu.Append(wx.ID_ADD, "Add &New Child\tCtrl+N", "Add child entry")

        enabled = len(selections) == 1 and selections[0] != self.entry_list.GetRootItem()
        copy.Enable(enabled)
        success = False
        if enabled and wx.TheClipboard.Open():
            success = wx.TheClipboard.IsSupported(wx.DataFormat("BCMEntry"))
            wx.TheClipboard.Close()
        paste.Enable(success)
        delete.Enable(enabled)
        append.Enable(enabled)
        insert.Enable(enabled)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_select(self, _):
        item = self.select_single_item()
        if not item:
            return
        pub.sendMessage('load_entry', entry=self.entry_list.GetItemData(item))

    def add_entry(self, parent, index):
        success = False
        cdo = wx.CustomDataObject("BCMEntry")
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(cdo)
        if success:
            entries = pickle.loads(cdo.GetData())
        else:
            entries = [BCMEntry(*(35 * [0]))]
        if index == -1:
            item = self.entry_list.AppendItem(parent, '', data=entries[0])
        else:
            item = self.entry_list.InsertItem(parent, index, '', data=entries[0])
        temp_entry_list = {
            entries[0].address: item
        }
        for entry in entries[1:]:
            temp_entry_list[entry.address] = self.entry_list.AppendItem(temp_entry_list[entry.parent], '', data=entry)
        self.entry_list.SelectItem(item)
        self.reindex()
        self.on_select(None)
        return len(entries)

    # TODO: Redo this
    def readjust_children(self, item):
        deleted_entry = self.entry_list.GetItemData(item)
        index = address_to_index(deleted_entry.address) + 1
        parent = self.entry_list.GetItemParent(item)
        parent_address = self.entry_list.GetItemData(parent).address
        temp_entry_list = {
            parent_address: parent
        }
        for entry in self.parent.bcm.entries[index:]:
            if entry.parent == parent_address:
                break
            if entry.parent == deleted_entry.address:
                entry.parent = deleted_entry.parent
            if entry.sibling == deleted_entry.address:
                entry.sibling = deleted_entry.sibling
            if entry.child == deleted_entry.address:
                entry.child = deleted_entry.child
            temp_entry_list[entry.address] = self.entry_list.AppendItem(temp_entry_list[entry.parent], '', data=entry)

    def get_children(self, item):
        self.entry_list.SelectChildren(item)
        selections = self.entry_list.GetSelections()
        for child in selections:
            selections.extend(self.get_children(child))
        return selections

    def select_single_item(self):
        selections = self.entry_list.GetSelections()
        if len(selections) != 1:
            return
        return selections[0]

    def on_add_child(self, _):
        item = self.select_single_item()
        if not item:
            return
        num_entries = self.add_entry(item, -1)
        pub.sendMessage(
            'set_status_bar', text=f'Added {num_entries} entry(s) under {self.entry_list.GetItemText(item)}')

    def on_append(self, _):
        item = self.select_single_item()
        if not item:
            return
        if item == self.entry_list.GetRootItem():
            with wx.MessageDialog(self, "Cannot add entry next to root entry, must be a child", "Warning") as dlg:
                dlg.ShowModal()
                return
        parent = self.entry_list.GetItemParent(item)
        index = get_item_index(self.entry_list, item)
        num_entries = self.add_entry(parent, index + 1)
        pub.sendMessage(
            'set_status_bar', text=f'Added {num_entries} entry(s) after {self.entry_list.GetItemText(item)}')

    def on_insert(self, _):
        item = self.select_single_item()
        if not item:
            return
        if item == self.entry_list.GetRootItem():
            with wx.MessageDialog(self, "Cannot add entry before root entry.", "Warning") as dlg:
                dlg.ShowModal()
                return
        parent = self.entry_list.GetItemParent(item)
        index = get_item_index(self.entry_list, item)
        num_entries = self.add_entry(parent, index)
        pub.sendMessage(
            'set_status_bar', text=f'Added {num_entries} entry(s) before {self.entry_list.GetItemText(item)}')

    def on_delete(self, _):
        item = self.select_single_item()
        if not item or item == self.entry_list.GetRootItem():
            return
        old_num_entries = len(self.parent.bcm.entries)
        if self.entry_list.GetFirstChild(item):
            with wx.MessageDialog(self, "Delete child entries as well?", '', wx.YES | wx.NO) as dlg:
                if dlg.ShowModal() != wx.ID_YES:
                    self.readjust_children(item)

        self.entry_list.Delete(item)
        self.reindex()
        new_num_entries = len(self.parent.bcm.entries)
        pub.sendMessage('disable')
        pub.sendMessage('set_status_bar', text=f'Deleted {old_num_entries - new_num_entries} entries')

    def on_copy(self, _):
        item = self.select_single_item()
        if not item or item == self.entry_list.GetRootItem():
            return
        selections = [item]
        if self.entry_list.GetChildrenCount(item) > 0:
            with wx.MessageDialog(self, 'Copy children entries as well?', '', wx.YES | wx.NO) as dlg:
                if dlg.ShowModal() == wx.ID_YES:
                    selections.extend(self.get_children(item))

                    # Reselect just the single entry
                    self.entry_list.UnselectAll()
                    self.entry_list.SelectItem(item)

        entries = sorted([self.entry_list.GetItemData(item) for item in selections], key=lambda data: data.address)

        self.cdo = wx.CustomDataObject("BCMEntry")
        self.cdo.SetData(pickle.dumps(entries))
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.cdo)
            wx.TheClipboard.Flush()
            wx.TheClipboard.Close()
        msg = 'Copied ' + self.entry_list.GetItemText(item)
        if len(entries) > 1:
            msg += f' and {len(entries) - 1} children'
        pub.sendMessage('set_status_bar', text=msg)

    def on_paste(self, _):
        item = self.select_single_item()
        if not item or item == self.entry_list.GetRootItem():
            return

        success = False
        cdo = wx.CustomDataObject("BCMEntry")
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(cdo)
            wx.TheClipboard.Close()
        if not success:
            return

        paste_data = pickle.loads(cdo.GetData())[0]
        entry = self.entry_list.GetItemData(item)

        # Keep address/parent/child
        paste_data.address = entry.address
        paste_data.parent = entry.parent
        paste_data.child = entry.child
        paste_data.sibling = entry.sibling

        self.entry_list.SetItemData(item, paste_data)
        self.reindex()
        pub.sendMessage('load_entry', entry=self.entry_list.GetItemData(item))
        pub.sendMessage('set_status_bar', text='Pasted to ' + self.entry_list.GetItemText(item))

    def reindex(self):
        # Set indexes first
        item, _ = get_first_item(self.entry_list)
        index = 1
        mappings = {}
        while item.IsOk():
            entry = self.entry_list.GetItemData(item)
            old_address, entry.address = entry.address, index_to_address(index)
            mappings[old_address] = entry.address
            self.entry_list.SetItemText(item, f'Entry {index}')
            item = get_next_item(self.entry_list, item)
            index += 1

        # Set parent/child/sibling/root
        item, _ = get_first_item(self.entry_list)
        root = 0
        entries = []
        while item.IsOk():
            entry = self.entry_list.GetItemData(item)
            # sibling = self.entry_list.GetNextSibling(item)
            # child = self.entry_list.GetFirstChild(item)
            parent = self.entry_list.GetItemParent(item)
            if parent == self.entry_list.GetRootItem():
                root = entry.address

            entry.sibling = mappings[entry.sibling] if entry.sibling else 0
            entry.child = mappings[entry.child] if entry.child else 0
            entry.parent = self.entry_list.GetItemData(parent).address if parent != self.entry_list.GetRootItem() else 0
            entry.root = root

            entries.append(entry)
            item = get_next_item(self.entry_list, item)
        self.parent.bcm.entries = entries



