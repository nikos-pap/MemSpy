import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
from reader import ProcessMemoryReader



class App:
    def __init__(self, root):
        self.root = root
        self.backend = ProcessMemoryReader('BleachBraveSouls.exe')
        #setting title
        root.title("Mem Scanner")
        #setting window size
        width=781
        height=562
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = f'{width}x{height}+{(screenwidth - width) // 2}+{(screenheight - height) // 2}'
        root.geometry(alignstr)
        root.resizable(width=False, height=False)

        self.searchText = tk.StringVar()
        self.searchText.trace_add('write', callback=self.inputListener)
        self.searchbox=ttk.Entry(root)
        self.searchbox['textvariable'] = self.searchText
        self.searchbox.place(x=10,y=10,width=200,height=30)

        self.type_var = tk.StringVar(value='Integer')
        self.typeButton=ttk.Button(root)
        self.typeButton["textvariable"] = self.type_var
        self.typeButton["command"] = self.openTypeMenuCommand
        self.typeButton.place(x=220,y=10,width=70,height=30)

        self.popup = tk.Menu(root, tearoff=0)
        self.popup.add_radiobutton(label='UInteger', variable=self.type_var, value='UInteger')
        self.popup.add_radiobutton(label='Integer', variable=self.type_var, value='Integer')
        self.popup.add_radiobutton(label='Float', variable=self.type_var, value='Float')
        self.popup.add_radiobutton(label='String', variable=self.type_var, value='String')

        GLabel_116=ttk.Label(root)
        ft = tkFont.Font(family='Arial',size=10)
        GLabel_116["font"] = ft
        GLabel_116["text"] = "Bytes"
        GLabel_116.place(x=375,y=10,width=50,height=30)

        self.GLineEdit_300=ttk.Entry(root)
        self.sizeVar = tk.StringVar(value='4')
        self.GLineEdit_300['justify'] = 'center'
        self.GLineEdit_300['textvariable'] = self.sizeVar
        self.GLineEdit_300.place(x=300,y=10,width=70,height=30)

        GButton_85=ttk.Button(root)
        GButton_85["text"] = "New Scan"
        GButton_85.place(x=470,y=10,width=70,height=30)
        # GButton_85["command"] = self.GButton_85_command

        GButton_659=ttk.Button(root)
        GButton_659["text"] = "Filter"
        GButton_659.place(x=550,y=10,width=70,height=30)
        # GButton_659["command"] = self.GButton_659_command
       
        self.change_popup = tk.Menu(root, tearoff=0)
        self.changeVar = tk.StringVar(value='=')
        self.change_popup.add_radiobutton(label='Equal to (=)', variable=self.changeVar, value='=')
        self.change_popup.add_radiobutton(label='Not Equal to (!=)', variable=self.changeVar, value='!=')
        self.change_popup.add_radiobutton(label='Greater than (>)', variable=self.changeVar, value='>')
        self.change_popup.add_radiobutton(label='Less than (<)', variable=self.changeVar, value='<')
        self.change_popup.add_separator()
        self.change_popup.add_radiobutton(label='Decreaced (-)', variable=self.changeVar, value='-')
        self.change_popup.add_radiobutton(label='Increased (+)', variable=self.changeVar, value='+')
        self.change_popup.add_radiobutton(label='Changed (-/+)', variable=self.changeVar, value='-/+')
        self.change_popup.add_radiobutton(label='Not Changed (==)', variable=self.changeVar, value='==')
        
        self.changeButton=ttk.Button(root)
        self.changeButton["textvariable"] = self.changeVar
        self.changeButton.place(x=420,y=10,width=40,height=30)
        self.changeButton["command"] = self.openChangeMenuCommand

        self.selectedIndexes = []
        self.selectedTree=ttk.Treeview(root, column=('Freeze', 'Address', 'Integer', 'Float', 'String'),show= 'headings')
        self.selectedTree.column("# 1",anchor=tk.CENTER, minwidth=100, width=100, stretch=False)
        self.selectedTree.heading("# 1", text= "Freeze")
        self.selectedTree.column("# 2",anchor=tk.CENTER, minwidth=100, width=100, stretch=False)
        self.selectedTree.heading("# 2", text= "Address")
        self.selectedTree.column("# 3", anchor= tk.CENTER, minwidth=100, width=100, stretch=False)
        self.selectedTree.heading("# 3", text= "Integer")
        self.selectedTree.column("# 4", anchor= tk.CENTER, minwidth=100, width=100, stretch=False)
        self.selectedTree.heading("# 4", text="Float")
        self.selectedTree.column("# 5", anchor= tk.CENTER, minwidth=100, width=100, stretch=False)
        self.selectedTree.heading("# 5", text="String")
        self.selectedTree.bind('<Button-3>', self.address_right_click)
        self.selectedTree.place(x=10,y=50,width=500,height=300)
        self.selectedTree.tag_configure('freeze', background='lightblue')
        # self.selectedTree.tag_configure('even', background='lightgreen')



        self.tree = ttk.Treeview(root, column=('Address', 'Integer', 'Float', 'String'), show= 'headings')
        self.tree.column("# 1",anchor=tk.CENTER, width=65, stretch=False)
        self.tree.heading("# 1", text= "Address")
        self.tree.column("# 2", anchor= tk.CENTER, width=65, stretch=False)
        self.tree.heading("# 2", text= "Integer")
        self.tree.column("# 3", anchor= tk.CENTER, width=65, stretch=False)
        self.tree.heading("# 3", text="Float")
        self.tree.column("# 4", anchor= tk.CENTER, width=65, stretch=False)
        self.tree.heading("# 4", text="String")
        self.tree.place(x=520,y=50,width=250,height=420)
        self.tree.insert('', 'end', text='1', values=(hex(0x123213), 15, 15.2, 'hi'))
        self.tree.insert('', 'end', text='2', values=(hex(0x123212), 14, 15.3, 'ho'))
        self.tree.bind('<Double-1>', self.address_selected)

        # tree.focus()


        GButton_749=ttk.Button(root)
        GButton_749["text"] = "Save List"
        GButton_749.place(x=700,y=10,width=70,height=30)
        # GButton_749["command"] = self.GButton_749_command

        GButton_322=ttk.Button(root)
        GButton_322["text"] = "Next"
        GButton_322.place(x=650,y=510,width=55,height=40)
        # GButton_322["command"] = self.GButton_322_command

        GButton_144=ttk.Button(root)
        GButton_144["text"] = "Previous"
        GButton_144.place(x=585,y=510,width=55,height=40)
        # GButton_144["command"] = self.GButton_144_command

        GButton_639=ttk.Button(root)
        GButton_639["text"] = "Start"
        GButton_639.place(x=520,y=510,width=55,height=40)
        # GButton_639["command"] = self.GButton_639_command

        GButton_840=ttk.Button(root)
        GButton_840["text"] = "End"
        GButton_840.place(x=715,y=510,width=55,height=40)
        # GButton_840["command"] = self.GButton_840_command

        self.SearchResultLabel=ttk.Label(root)
        self.SearchResultLabel["justify"] = "center"
        self.SearchResultLabel["text"] = "Found 500 Results"
        self.SearchResultLabel.place(x=520,y=480,width=250,height=25)

        self.selectedTreeActionVar = tk.StringVar(value='=')
        self.selectedTreePopup = tk.Menu(root, tearoff=0)
        self.selectedTreePopup.add_command(label='Freeze/Unfreeze', command=self.freezeAddress)
        self.selectedTreePopup.add_command(label='Edit', command=self.editValue)
        self.selectedTreePopup.add_command(label='Delete', command=self.deleteAddress)

    def openTypeMenuCommand(self):
        try:         
            x = self.typeButton.winfo_rootx()
            y = self.typeButton.winfo_rooty() + self.typeButton.winfo_height()
            self.popup.tk_popup(x, y, 0)
        finally:
           self.popup.grab_release()

    def openChangeMenuCommand(self):
        try:         
            x = self.changeButton.winfo_rootx()
            y = self.changeButton.winfo_rooty() + self.changeButton.winfo_height()
            self.change_popup.tk_popup(x, y, 0)
        finally:
           self.change_popup.grab_release()

    def address_selected(self, event):
        item_name = self.tree.identify('item',event.x,event.y)
        item = self.tree.item(item_name)
        index = self.tree.index(item_name)
        x = self.changeButton.winfo_rootx()
        y = self.changeButton.winfo_rooty() + self.changeButton.winfo_height()
        if len(item['values']) > 0:
            self.selectedTree.insert('', 'end', values=('False', *item['values']))
            self.selectedIndexes.append(index)
    
    def address_right_click(self, event):
        x,y = (event.x, event.y)
        item_name = self.selectedTree.identify('item', x, y)
        item = self.selectedTree.item(item_name)
        index = self.selectedTree.index(item_name)
        self.selectedTree.selection_set(self.selectedTree.get_children()[index])
        self.selectedTree.focus(self.selectedTree.get_children()[index])
        print(item)
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        if len(item['values']) > 0:
            try:         
                self.selectedTreePopup.tk_popup(x, y, 0)
            finally:
               self.selectedTreePopup.grab_release()


    def freezeAddress(self):
        item_name = self.selectedTree.focus()
        tags = self.selectedTree.item(item_name, 'tags')
        if 'freeze' in self.selectedTree.item(item_name, 'tags'):
            old = self.selectedTree.item(item_name)['values']
            old[0] = 'False'
            self.selectedTree.item(item_name, values=old, tags=[''])
        else:
            old = self.selectedTree.item(item_name)['values']
            old[0] = 'True'
            self.selectedTree.item(item_name, values=old, tags=['freeze'])

    def deleteAddress(self):
        item_name = self.selectedTree.focus()
        self.selectedTree.delete(item_name)

    def editValue(self):
        print('Edit')

    def inputListener(self, variable, a, callback_mode):
        # if self.type_var == 0:
        print(self.searchText.get())

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
