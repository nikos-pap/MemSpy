import tkinter as tk
from PIL import Image, ImageTk
from tkinter import ttk
import struct
from sys import byteorder
from backend import Backend
from threading import Thread


class App:
	def __init__(self, root):
		self.root = root
		root.protocol("WM_DELETE_WINDOW", self.on_closing)
		self.backend = Backend()

		# Configuring Window
		root.title("Mem Scanner")
		width = 781
		height = 562
		screenwidth = root.winfo_screenwidth()
		screenheight = root.winfo_screenheight()
		alignstr = f'{width}x{height}+{(screenwidth - width) // 2}+{(screenheight - height) // 2}'
		root.geometry(alignstr)
		root.resizable(width=False, height=False)

		treeViewStyle = ttk.Style()
		treeViewStyle.map('Treeview', background=[('selected', 'lightblue')], foreground=[('selected', 'red')])

		# Search input field
		self.searchText = tk.StringVar()
		self.searchText.trace_add('write', callback=self.inputListener)
		self.searchbox = ttk.Entry(root)
		self.searchbox['textvariable'] = self.searchText
		self.searchbox.place(x=10, y=10, width=200, height=30)

		# Search value type
		self.typeVar = tk.StringVar(value='Integer')
		self.typeButton = ttk.Button(root)
		self.typeButton["textvariable"] = self.typeVar
		self.typeButton["command"] = self.openTypeMenuCommand
		self.typeButton.place(x=220, y=10, width=70, height=30)

		self.popup = tk.Menu(root, tearoff=0)
		self.popup.add_radiobutton(label='Integer', variable=self.typeVar, value='Integer')
		self.popup.add_radiobutton(label='Float', variable=self.typeVar, value='Float')
		self.popup.add_radiobutton(label='String', variable=self.typeVar, value='String')

		bytesLabel = ttk.Label(root)
		bytesLabel["text"] = "Bytes"
		bytesLabel.place(x=375, y=10, width=50, height=30)

		# search value size
		self.sizeVar = tk.StringVar(value='4')
		self.sizeInput=ttk.Entry(root)
		self.sizeInput['justify'] = 'center'
		self.sizeInput['textvariable'] = self.sizeVar
		self.sizeInput.place(x=300, y=10, width=70, height=30)

		# Scan Button
		self.scanButton=ttk.Button(root)
		self.scanButton["text"] = "New Scan"
		self.scanButton.place(x=470, y=10, width=70, height=30)
		self.scanButton["command"] = self.scanCommand
		self.scanVar = tk.StringVar(value='Not Started')
		self.scanVar.trace_add('write', callback=self.scanStatusListener)


		# Filter Button
		self.filterButton=ttk.Button(root)
		self.filterButton["text"] = "Filter"
		self.filterButton.place(x=550, y=10, width=70, height=30)
		self.filterButton["command"] = self.filterCommand
	   
		# Search type
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
		self.changeButton.place(x=420, y=10, width=40, height=30)
		self.changeButton["command"] = self.openChangeMenuCommand

		self.selectedTree=ttk.Treeview(root, column=('c1', 'c2', 'c3', 'c4', 'c5'), show='headings')
		self.selectedTree.column("# 1",anchor=tk.CENTER, minwidth=50, width=50, stretch=False)
		self.selectedTree.heading("# 1", text= "Freeze")
		self.selectedTree.column("# 2",anchor=tk.CENTER, minwidth=225, width=225, stretch=False)
		self.selectedTree.heading("# 2", text= "Address")
		self.selectedTree.column("# 3", anchor= tk.CENTER, minwidth=225, width=225, stretch=False)
		self.selectedTree.heading("# 3", text= "value")
		self.selectedTree.bind('<Button-3>', self.address_right_click)
		self.selectedTree.place(x=10, y=50, width=500, height=300)
		self.selectedTree.tag_configure('freeze', foreground='green')
		# self.selectedTree.insert('', 'end', values=('True', '0x11236457', '12'), tags=['Integer'])

		self.editVariable = tk.StringVar()

		self.tentry = ttk.Entry(self.root)
		self.tentry['textvariable'] = self.editVariable
		self.tentry['justify'] = 'right'

		self.okButton = ttk.Button(self.root, padding='0 0 0 0')
		self.okButton['text'] = 'ΟK'

		self.cancelButton = ttk.Button(self.root, padding='0 0 0 0')
		self.cancelButton['text'] = 'Cancel'
		self.cancelButton['command'] = self.closeEdit

		self.tree = ttk.Treeview(root, column=('c1', 'c2'), show='headings')
		self.tree.column("# 1",anchor=tk.W, minwidth=100, width=125, stretch=False)
		self.tree.heading("# 1", text= "Address")
		self.tree.column("# 2", anchor= tk.W, minwidth=100, width=125, stretch=False)
		self.tree.heading("# 2", text= "Value")
		self.tree.place(x=520, y=50, width=250, height=460)
		self.tree.bind('<Double-1>', self.address_selected)

		self.processSelectList = tk.Menu(root, tearoff=0)
		self.processNameVar = tk.StringVar()
		for i in self.backend.running_processes:
			self.processSelectList.add_radiobutton(label=i, variable=self.processNameVar, value=i, command=self.processSelectCommand)

		self.processButton=ttk.Button(root)
		self.processButton["textvariable"] = self.processNameVar
		self.processButton.place(x=630, y=10, width=135, height=30)
		self.processButton["command"] = self.openProcessMenuCommand

		self.searchResultVar = tk.StringVar()
		self.searchResultLabel=ttk.Label(root)
		self.searchResultLabel["justify"] = "center"
		self.searchResultLabel["textvariable"] = self.searchResultVar
		self.searchResultLabel.place(x=520, y=510, width=250, height=25)

		self.selectedTreeActionVar = tk.StringVar(value='=')
		self.selectedTreeMenu = tk.Menu(root, tearoff=0)
		self.selectedTreeMenu.add_command(label='Freeze/Unfreeze', command=self.freezeAddress)
		self.selectedTreeMenu.add_command(label='Edit', command=self.editValue)
		self.selectedTreeMenu.add_command(label='Delete', command=self.deleteAddress)

		self.progressBar = ttk.Progressbar(root, orient='horizontal', mode='determinate', length=100)
		self.progressBar.place(x=10, y=540, width=width-20, height=15)

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

	def openProcessMenuCommand(self):
		try:         
			x = self.processButton.winfo_rootx()
			y = self.processButton.winfo_rooty() + self.processButton.winfo_height()
			self.processSelectList.tk_popup(x, y, 0)
		finally:
			self.processSelectList.grab_release()

	def processSelectCommand(self):
		self.backend.initProcessReader(self.processNameVar.get())

	def address_selected(self, event):
		item_name = self.tree.identify('item',event.x,event.y)
		item = self.tree.item(item_name)
		index = self.tree.index(item_name)
		x = self.changeButton.winfo_rootx()
		y = self.changeButton.winfo_rooty() + self.changeButton.winfo_height()
		if len(item['values']) > 0 and self.backend.selectAddress(index):
			self.selectedTree.insert('', 'end', values=('False', *item['values']), tags=item['tags'])
	
	def address_right_click(self, event):
		item_name = self.selectedTree.identify('item', event.x, event.y)
		item = self.selectedTree.item(item_name)
		index = self.selectedTree.index(item_name)
		self.selectedTree.selection_set(self.selectedTree.get_children()[index])
		self.selectedTree.focus(self.selectedTree.get_children()[index])
		x = self.root.winfo_pointerx()
		y = self.root.winfo_pointery()
		if len(item['values']) > 0:
			try:         
				self.selectedTreeMenu.tk_popup(x, y, 0)
			finally:
			   self.selectedTreeMenu.grab_release()

	def scanCommand(self):
		if self.processNameVar.get() == '':
			print('Select a process first!')
			return
		size = int(self.sizeVar.get())
		value = self.convert_to_bytes(self.searchText.get(), self.typeVar.get(), size)
		self.scanVar.set('Started')
		t = Thread(target=self.data_to_address_list, args= (value,), daemon=True)
		t.start()

	def data_to_address_list(self, value):
		self.backend.value_scan(value, self.progressBar)
		# self.fill_address_table()
		self.scanVar.set('Finished')

	def convert_to_bytes(self, value, type_variable, size=4):
		if 'Integer' :
			value = int(value).to_bytes(size, byteorder)
		if 'Float' in type_variable:
			value = struct.unpack('f', value)
		if 'String' in type_variable:
			value = value.decode('utf-8')
		return value

	def fill_address_table(self):
		address_list = self.backend.get_address_list(self.typeVar.get())
		for address in address_list:
			self.tree.insert('', 'end', values=address['values'], tags=[self.typeVar.get()])
		self.searchResultVar.set(f'Found {len(address_list)} results.')

	def filterCommand(self):
		scan_status = self.scanVar.get()
		if scan_status == 'Not Started':
			print('Execute a scan before you start a filter')
			return
		if scan_status == 'Started':
			print('Finish the scan before you start a filter')
			return
		if scan_status != 'Finished':
			raise Exception(f'Invalid scanVar value?: {scan_status}')

		size = int(self.sizeVar.get())
		value = self.convert_to_bytes(self.searchText.get(), self.typeVar.get(), size)

		if self.changeVar.get() == '=':
			self.backend.filter_address_list(lambda a,b: a == b, value)
		elif self.changeVar.get() == '!=':
			self.backend.filter_address_list(lambda a,b: a != b, value)
		elif self.changeVar.get() == '>':
			self.backend.filter_address_list(lambda a,b: a > b, value)
		elif self.changeVar.get() == '<':
			self.backend.filter_address_list(lambda a,b: a < b, value)
		elif self.changeVar.get() == '+':
			self.backend.filter_address_list(lambda a,b: a > b, None)
		elif self.changeVar.get() == '-':
			self.backend.filter_address_list(lambda a,b: a < b, None)
		elif self.changeVar.get() == '==':
			self.backend.filter_address_list(lambda a,b: a == b, None)
		elif self.changeVar.get() == '-/+':
			self.backend.filter_address_list(lambda a,b: a != b, None)
		else:
			print(f'Not Implemented yet {self.changeVar.get()}')
		self.tree.delete(*self.tree.get_children())
		self.fill_address_table()

	def freezeAddress(self):
		item_name = self.selectedTree.focus()
		tags = self.selectedTree.item(item_name, 'tags')
		index = self.selectedTree.index(item_name)
		if 'freeze' in self.selectedTree.item(item_name, 'tags'):
			old = self.selectedTree.item(item_name)['values']
			old[0] = 'False'
			tags = [i for i in tags if i != 'freeze']
			self.selectedTree.item(item_name, values=old, tags=tags)
			self.backend.unfreezeAddress(index)
		else:
			old = self.selectedTree.item(item_name)['values']
			old[0] = 'True'
			self.selectedTree.item(item_name, values=old, tags=('freeze', *tags))
			self.backend.freezeAddress(index)

	def deleteAddress(self):
		item_name = self.selectedTree.focus()
		index = self.selectedTree.index(item_name)
		self.backend.deleteAddress(index)
		self.selectedTree.delete(item_name)

	def editValue(self):
		selection = self.selectedTree.focus()
		item = self.selectedTree.item(selection)
		index = self.selectedTree.index(selection)
		self.editVariable.set(item['values'][-1])
		
		x = self.selectedTree.winfo_rootx() - self.root.winfo_rootx()
		y = self.selectedTree.winfo_rooty() - self.root.winfo_rooty() + 25 + (index + 1) * 20
		
		self.okButton['command'] = lambda: self.setValue(selection)

		self.tentry.place(x=x, y=y, width=150, height=25)
		self.okButton.place(x=x+150, y=y, width=30, height=25)
		self.cancelButton.place(x=x+150 + 30, y=y, width=50, height=25)

	def setValue(self, item):
		row = self.selectedTree.item(item)
		index = self.selectedTree.index(item)
		print(row)
		tags = row['tags']
		old_values = row['values']
		old_values[-1] = self.editVariable.get()
		print(self.convert_to_bytes(self.editVariable.get(), tags[0]), tags[0])
		self.backend.setValue(index, self.convert_to_bytes(self.editVariable.get(), tags))
		self.selectedTree.item(item, values=old_values,tags=tags)
		self.closeEdit()

	def closeEdit(self):
		self.tentry.place_forget()
		self.okButton.place_forget()
		self.cancelButton.place_forget()

	def on_closing(self):
		self.backend.stop_loop()
		self.root.destroy()

	def inputListener(self, variable, a, callback_mode):
		# print(variable, a, callback_mode)
		print(self.searchText.get())

	def scanStatusListener(self, variable, a, callback_mode):
		if self.scanVar.get() == 'Finished':
			self.fill_address_table()

if __name__ == "__main__":
	root = tk.Tk()
	app = App(root)
	root.mainloop()
