#!/usr/local/bin/python3.6
import os
import sys
import traceback

from pubsub import pub
import wx
from wx.lib.dialogs import ScrolledMessageDialog
from wx.lib.agw.hyperlink import HyperLinkCtrl

from pyxenoverse.bcm import BCM
from yabcm.panels.main import MainPanel
from yabcm.panels.entry import EntryPanel
from yabcm.dlg.find import FindDialog
from yabcm.dlg.replace import ReplaceDialog
from pyxenoverse.gui.file_drop_target import FileDropTarget

VERSION = '0.1.8'


class MainWindow(wx.Frame):
    def __init__(self, parent, title, dirname, filename):
        sys.excepthook = self.exception_hook
        self.dirname = ''
        self.bcm = None
        self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)

        # A "-1" in the size parameter instructs wxWidgets to use the default size.
        # In this case, we select 200px width and the default height.
        wx.Frame.__init__(self, parent, title=title, size=(1300, 900))
        self.statusbar = self.CreateStatusBar() # A Statusbar in the bottom of the window

        # Panels
        self.main_panel = MainPanel(self)
        self.entry_panel = EntryPanel(self)

        # Setting up the menu.
        file_menu= wx.Menu()
        file_menu.Append(wx.ID_OPEN)
        file_menu.Append(wx.ID_SAVE)
        file_menu.Append(wx.ID_ABOUT)
        file_menu.Append(wx.ID_EXIT)

        edit_menu = wx.Menu()
        edit_menu.Append(wx.ID_FIND)
        edit_menu.Append(wx.ID_REPLACE)

        # Creating the menubar.
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File") # Adding the "filemenu" to the MenuBar
        menu_bar.Append(edit_menu, "&Edit")
        self.SetMenuBar(menu_bar)  # Adding the MenuBar to the Frame content.

        # Publisher
        pub.subscribe(self.open_bcm, 'open_bcm')
        pub.subscribe(self.load_bcm, 'load_bcm')
        pub.subscribe(self.save_bcm, 'save_bcm')
        pub.subscribe(self.set_status_bar, 'set_status_bar')

        # Events.
        self.Bind(wx.EVT_MENU, self.open_bcm, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.save_bcm, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_find, id=wx.ID_FIND)
        self.Bind(wx.EVT_MENU, self.on_replace, id=wx.ID_REPLACE)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.main_panel.on_copy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.main_panel.on_paste, id=wx.ID_PASTE)
        self.Bind(wx.EVT_MENU, self.main_panel.on_delete, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.main_panel.on_add_child, id=wx.ID_ADD)
        self.Bind(wx.EVT_MENU, self.main_panel.on_append, id=self.main_panel.append_id)
        self.Bind(wx.EVT_MENU, self.main_panel.on_insert, id=self.main_panel.insert_id)
        accelerator_table = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('o'), wx.ID_OPEN),
            (wx.ACCEL_CTRL, ord('s'), wx.ID_SAVE),
            (wx.ACCEL_CTRL, ord('f'), wx.ID_FIND),
            (wx.ACCEL_CTRL, ord('h'), wx.ID_REPLACE),
        ])
        self.SetAcceleratorTable(accelerator_table)
        self.SetDropTarget(FileDropTarget(self, "load_bcm"))

        # Name
        self.name = wx.StaticText(self, -1, '(No file loaded)')
        font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.name.SetFont(font)

        # Buttons
        open_button = wx.Button(self, wx.ID_OPEN, "Load")
        open_button.Bind(wx.EVT_BUTTON, self.open_bcm)

        save_button = wx.Button(self, wx.ID_SAVE, "Save")
        save_button.Bind(wx.EVT_BUTTON, self.save_bcm)

        hyperlink = HyperLinkCtrl(self, -1, "What do all these things mean?",
                                  URL="https://docs.google.com/document/d/"
                                      "18gaAbNCeJyTgizz5IvvXzjWcH9K5Q1wvUHTeWnp8M-E/edit#heading=h.tx82dphejin1")

        # Sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer()
        button_sizer.Add(open_button)
        button_sizer.AddSpacer(10)
        button_sizer.Add(save_button)
        button_sizer.Add(hyperlink, 0, wx.ALL, 10)

        panel_sizer = wx.BoxSizer()
        panel_sizer.Add(self.main_panel, 1, wx.ALL | wx.EXPAND)
        panel_sizer.Add(self.entry_panel, 2, wx.ALL | wx.EXPAND)

        sizer.Add(self.name, 0, wx.CENTER)
        sizer.Add(button_sizer, 0, wx.ALL, 10)
        sizer.Add(panel_sizer, 1, wx.ALL | wx.EXPAND)

        self.SetBackgroundColour('white')
        self.SetSizer(sizer)
        self.SetAutoLayout(1)

        # Lists
        self.entry_list = self.main_panel.entry_list

        # Dialogs
        self.find = FindDialog(self, self.entry_list, -1)
        self.replace = ReplaceDialog(self, self.entry_list, -1)

        sizer.Layout()
        self.Show()

        if filename:
            self.load_bcm(dirname, filename)

    def exception_hook(self, etype, value, trace):
        dlg = ScrolledMessageDialog(self, ''.join(traceback.format_exception(etype, value, trace)), "Error")
        dlg.ShowModal()
        dlg.Destroy()

    def on_about(self, e):
        # Create a message dialog box
        dlg = wx.MessageDialog(self, f"Yet Another BCM Organizer v{VERSION} by Kyonko Yuuki",
                               "About BCM Organizer", wx.OK)
        dlg.ShowModal() # Shows it
        dlg.Destroy() # finally destroy it when finished.

    def on_exit(self, e):
        self.Close(True)  # Close the frame.

    def set_status_bar(self, text):
        self.statusbar.SetStatusText(text)

    def open_bcm(self, e):
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.bcm", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.load_bcm(dlg.GetDirectory(), dlg.GetFilename())
        dlg.Destroy()

    def load_bcm(self, dirname, filename):
        self.dirname = dirname
        path = os.path.join(self.dirname, filename)
        self.statusbar.SetStatusText("Loading...")
        new_bcm = BCM()
        if not new_bcm.load(path):
            dlg = wx.MessageDialog(self, f"{filename} is not a valid BCM", "Warning")
            dlg.ShowModal()
            dlg.Destroy()
            return
        self.bcm = new_bcm

        # Build Tree
        self.entry_list.DeleteAllItems()
        temp_entry_list = {
            0: self.entry_list.AppendItem(self.entry_list.GetRootItem(), 'Entry 0', data=self.bcm.entries[0])
        }
        for entry in sorted(self.bcm.entries[1:], key=lambda x: (x.parent, x.address)):
            temp_entry_list[entry.address] = self.entry_list.AppendItem(temp_entry_list[entry.parent], '', data=entry)
        self.main_panel.reindex()
        self.main_panel.Layout()
        self.entry_panel.Disable()
        self.name.SetLabel(filename)
        self.statusbar.SetStatusText(f"Loaded {path}")

    def save_bcm(self, e):
        if not self.bcm:
            dlg = wx.MessageDialog(self, " No BCM Loaded", "Warning", wx.OK)
            dlg.ShowModal() # Shows it
            dlg.Destroy() # finally destroy it when finished.
            return

        dlg = wx.FileDialog(self, "Save as...", self.dirname, "", "*.bcm", wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.statusbar.SetStatusText("Saving...")
            path = os.path.join(self.dirname, filename)
            self.main_panel.reindex()
            self.bcm.save(path)
            self.statusbar.SetStatusText(f"Saved {path}")
            saved = wx.MessageDialog(self, f"Saved to {path} successfully", "BCM Saved")
            saved.ShowModal()
            saved.Destroy()
        dlg.Destroy()

    def on_find(self, _):
        if not self.replace.IsShown():
            self.find.Show()

    def on_replace(self, _):
        if not self.find.IsShown():
            self.replace.Show()


if __name__ == '__main__':
    app = wx.App(False)
    dirname = filename = None
    if len(sys.argv) > 1:
        dirname, filename = os.path.split(sys.argv[1])
    frame = MainWindow(None, f"YaBCM Organizer v{VERSION}", dirname, filename)
    app.MainLoop()
