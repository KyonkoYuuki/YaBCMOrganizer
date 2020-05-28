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
        pub.subscribe(self.reindex, 'reindex')
        pub.subscribe(self.reindex, 'expand_parents')

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

    def expand_parents(self, item):
        root = self.entry_list.GetRootItem()
        parent = self.entry_list.GetItemParent(item)
        while parent != root:
            self.entry_list.Expand(parent)
            parent = self.entry_list.GetItemParent(parent)

    def select_item(self, item):
        self.entry_list.UnselectAll()
        self.entry_list.SelectItem(item)
        self.expand_parents(item)
        if not self.entry_list.IsVisible(item):
            self.entry_list.ScrollTo(item)

    def get_selected_root_nodes(self):
        selected = self.entry_list.GetSelections()
        if not selected:
            return []
        root = self.entry_list.GetRootItem()

        nodes = []
        for item in selected:
            parent = self.entry_list.GetItemParent(item)
            while parent != root and parent.IsOk():
                if parent in selected:
                    break
                parent = self.entry_list.GetItemParent(parent)
            if parent == root:
                nodes.append(item)
        return nodes

    def add_entry(self, parent, index):
        success = False
        cdo = wx.CustomDataObject("BCMEntry")
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(cdo)
        if success:
            entries = pickle.loads(cdo.GetData())

            # Increment addresses so they don't run into existing ones.
            # Luckily....there is a limit on how big they can be.
            for entry in entries:
                entry.address += 0x100000000
                entry.child += 0x100000000
                entry.parent += 0x100000000
                entry.sibling += 0x100000000
        else:
            entries = [BCMEntry(*(35 * [0]))]
        if index == -1:
            item = self.entry_list.AppendItem(parent, '', data=entries[0])
        else:
            item = self.entry_list.InsertItem(parent, index, '', data=entries[0])

        # Get data from parent and surrounding siblings
        parent_data = self.entry_list.GetItemData(parent)
        prev_item = self.entry_list.GetPrevSibling(item)
        prev_data = self.entry_list.GetItemData(prev_item) if prev_item.IsOk() else None

        next_item = self.entry_list.GetNextSibling(item)
        next_data = self.entry_list.GetItemData(next_item) if next_item.IsOk() else None

        if next_data:
            entries[0].sibling = next_data.address

        temp_entry_list = {
            entries[0].address: item
        }
        for entry in entries[1:]:
            temp_entry_list[entry.address] = self.entry_list.AppendItem(temp_entry_list[entry.parent], '', data=entry)

        self.reindex()

        # If siblings aren't set, set them now
        update = False

        if parent_data.child == 0:
            parent_data.child = entries[0].address
            update = True

        if prev_data and next_data and prev_data.sibling == next_data.address:
            prev_data.sibling, entries[0].sibling = entries[0].address, next_data.address
            update = True

        if prev_data and prev_data.sibling == 0:
            prev_data.sibling = entries[0].address
            update = True

        if update:
            self.reindex()

        self.entry_list.Expand(parent)
        self.entry_list.UnselectAll()
        self.entry_list.SelectItem(item)
        if not self.entry_list.IsVisible(item):
            self.entry_list.ScrollTo(item)
        return entries

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
        data = self.entry_list.GetItemData(item)
        if not item:
            return
        entries = self.add_entry(item, -1)
        if data.child == 0:
            data.child = entries[0].address
            self.reindex()
        pub.sendMessage(
            'set_status_bar', text=f'Added {len(entries)} entry(s) under {self.entry_list.GetItemText(item)}')

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
        entries = self.add_entry(parent, index + 1)
        pub.sendMessage(
            'set_status_bar', text=f'Added {len(entries)} entry(s) after {self.entry_list.GetItemText(item)}')

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
        entries = self.add_entry(parent, index)
        pub.sendMessage(
            'set_status_bar', text=f'Added {len(entries)} entry(s) before {self.entry_list.GetItemText(item)}')

    def on_delete(self, _):
        selections = self.entry_list.GetSelections()
        if not selections:
            return
        if self.entry_list.GetRootItem() in selections:
            with wx.MessageDialog(self, "Cannot delete entry 0", 'Error', wx.OK) as dlg:
                dlg.ShowModal()
            return
        old_num_entries = len(self.parent.bcm.entries)

        for item in selections:
            self.entry_list.Delete(item)
        self.reindex()
        new_num_entries = len(self.parent.bcm.entries)
        pub.sendMessage('disable')
        pub.sendMessage('set_status_bar', text=f'Deleted {old_num_entries - new_num_entries} entries')

    def on_copy(self, _):
        item = self.select_single_item()
        if not item or item == self.entry_list.GetRootItem():
            return
        selections = {item}
        if self.entry_list.GetChildrenCount(item) > 0:
            with wx.MessageDialog(self, 'Copy children entries as well?', '', wx.YES | wx.NO) as dlg:
                if dlg.ShowModal() == wx.ID_YES:
                    selections.update(self.get_children(item))

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
            text = self.entry_list.GetItemText(item)
            sibling = self.entry_list.GetNextSibling(item)
            child, _ = self.entry_list.GetFirstChild(item)
            parent = self.entry_list.GetItemParent(item)

            sibling_address = self.entry_list.GetItemData(sibling).address if sibling.IsOk() else 0
            child_address = self.entry_list.GetItemData(child).address if child.IsOk() else 0

            # Root will always be one of the immediate childs to Entry 0
            if parent == self.entry_list.GetRootItem():
                root = entry.address

            # If the mapping for the sibling/child has been deleted, reset it
            if entry.sibling:
                entry.sibling = mappings.get(entry.sibling, 0)
                if not entry.sibling:
                    entry.sibling = sibling_address

            if entry.child:
                entry.child = mappings.get(entry.child, 0)
                if not entry.child:
                    entry.child = child_address

            entry.parent = self.entry_list.GetItemData(parent).address if parent != self.entry_list.GetRootItem() else 0
            entry.root = root

            if sibling_address != entry.sibling:
                text += f", Sibling: {address_to_index(entry.sibling)}"
            if child_address != entry.child:
                text += f", Child: {address_to_index(entry.child)}"
            self.entry_list.SetItemText(item, text)

            entries.append(entry)
            item = get_next_item(self.entry_list, item)
        self.parent.bcm.entries = entries



