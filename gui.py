import tkinter as tk
from tkinter import ttk
import struct
from sys import byteorder
from backend import Backend
from threading import Thread


class App(tk.Tk):
	def __init__(self):
		tk.Tk.__init__(self)
		self.protocol("WM_DELETE_WINDOW", self.on_closing)
		self.backend = Backend()

		# Configuring Window
		self.title("Mem Scanner")
		width = 781
		height = 562
		screenwidth = self.winfo_screenwidth()
		screenheight = self.winfo_screenheight()
		alignstr = f'{width}x{height}+{(screenwidth - width) // 2}+{(screenheight - height) // 2}'
		self.geometry(alignstr)
		self.resizable(width=False, height=False)

		treeViewStyle = ttk.Style()
		treeViewStyle.map('Treeview', background=[('selected', 'lightblue')], foreground=[('selected', 'red')])

		# Search input field
		self.searchText = tk.StringVar()
		self.searchText.trace_add('write', callback=self.inputListener)
		self.searchbox = ttk.Entry(self)
		self.searchbox['textvariable'] = self.searchText
		self.searchbox.place(x=10, y=10, width=200, height=30)

		# Search value type
		self.typeVar = tk.StringVar(value='Integer')
		self.typeButton = ttk.Button(self)
		self.typeButton["textvariable"] = self.typeVar
		self.typeButton["command"] = self.openTypeMenuCommand
		self.typeButton.place(x=220, y=10, width=70, height=30)

		self.popup = tk.Menu(self, tearoff=0)
		self.popup.add_radiobutton(label='Integer', variable=self.typeVar, value='Integer')
		self.popup.add_radiobutton(label='Float', variable=self.typeVar, value='Float')
		self.popup.add_radiobutton(label='String', variable=self.typeVar, value='String')

		bytesLabel = ttk.Label(self, text="Bytes")
		bytesLabel.place(x=375, y=10, width=50, height=30)

		# search value size
		self.sizeVar = tk.StringVar(value='4')
		self.sizeInput=ttk.Entry(self)
		self.sizeInput['justify'] = 'center'
		self.sizeInput['textvariable'] = self.sizeVar
		self.sizeInput.place(x=300, y=10, width=70, height=30)

		# Scan Button
		self.scanButton=ttk.Button(self)
		self.scanButton["text"] = "New Scan"
		self.scanButton.place(x=470, y=10, width=70, height=30)
		self.scanButton["command"] = self.scanCommand
		self.scanVar = tk.StringVar(value='Not Started')
		self.scanVar.trace_add('write', callback=self.scanStatusListener)


		# Filter Button
		self.filterButton=ttk.Button(self)
		self.filterButton["text"] = "Filter"
		self.filterButton.place(x=550, y=10, width=70, height=30)
		self.filterButton["command"] = self.filterCommand
	   
		# Search type
		self.searchTypePopup = tk.Menu(self, tearoff=0)
		self.changeVar = tk.StringVar(value='=')
		self.searchTypePopup.add_radiobutton(label='Equal to (=)', variable=self.changeVar, value='=')
		self.searchTypePopup.add_radiobutton(label='Not Equal to (!=)', variable=self.changeVar, value='!=')
		self.searchTypePopup.add_radiobutton(label='Greater than (>)', variable=self.changeVar, value='>')
		self.searchTypePopup.add_radiobutton(label='Less than (<)', variable=self.changeVar, value='<')
		self.searchTypePopup.add_separator()
		self.searchTypePopup.add_radiobutton(label='Decreaced (-)', variable=self.changeVar, value='-')
		self.searchTypePopup.add_radiobutton(label='Increased (+)', variable=self.changeVar, value='+')
		self.searchTypePopup.add_radiobutton(label='Changed (-/+)', variable=self.changeVar, value='-/+')
		self.searchTypePopup.add_radiobutton(label='Not Changed (==)', variable=self.changeVar, value='==')
		
		self.searchTypeButton=ttk.Button(self)
		self.searchTypeButton["textvariable"] = self.changeVar
		self.searchTypeButton.place(x=420, y=10, width=40, height=30)
		self.searchTypeButton["command"] = self.openSearchTypeMenuCommand

		self.selectedTree=ttk.Treeview(self, column=('c1', 'c2', 'c3', 'c4', 'c5'), show='headings')
		self.selectedTree.column("# 1",anchor=tk.CENTER, minwidth=50, width=50, stretch=False)
		self.selectedTree.heading("# 1", text= "Freeze")
		self.selectedTree.column("# 2",anchor=tk.CENTER, minwidth=225, width=225, stretch=False)
		self.selectedTree.heading("# 2", text= "Address")
		self.selectedTree.column("# 3", anchor= tk.CENTER, minwidth=225, width=225, stretch=False)
		self.selectedTree.heading("# 3", text= "value")
		self.selectedTree.bind('<Button-3>', self.rightClickAddressCommand)
		self.selectedTree.place(x=10, y=50, width=500, height=300)
		self.selectedTree.tag_configure('freeze', foreground='green')

		self.editVariable = tk.StringVar()

		self.tentry = ttk.Entry(self)
		self.tentry['textvariable'] = self.editVariable
		self.tentry['justify'] = 'right'

		self.okButton = ttk.Button(self, padding='0 0 0 0')
		self.okButton['text'] = 'ΟK'

		self.cancelButton = ttk.Button(self, padding='0 0 0 0')
		self.cancelButton['text'] = 'Cancel'
		self.cancelButton['command'] = self.closeEdit

		self.tree = ttk.Treeview(self, column=('c1', 'c2'), show='headings')
		self.tree.column("# 1",anchor=tk.W, minwidth=100, width=125, stretch=False)
		self.tree.heading("# 1", text= "Address")
		self.tree.column("# 2", anchor= tk.W, minwidth=100, width=125, stretch=False)
		self.tree.heading("# 2", text= "Value")
		self.tree.place(x=520, y=50, width=250, height=460)
		self.tree.bind('<Double-1>', self.selectAddressCommand)

		self.processSelectList = tk.Menu(self, tearoff=0)
		self.processNameVar = tk.StringVar(value='')
		for i in self.backend.running_processes:
			self.processSelectList.add_radiobutton(label=i, variable=self.processNameVar, value=i, command=self.processSelectCommand)

		self.processButton=ttk.Button(self)
		self.processButton["textvariable"] = self.processNameVar
		self.processButton.place(x=630, y=10, width=135, height=30)
		self.processButton["command"] = self.openProcessMenuCommand

		self.searchResultVar = tk.StringVar()
		self.searchResultLabel=ttk.Label(self)
		self.searchResultLabel["justify"] = "center"
		self.searchResultLabel["textvariable"] = self.searchResultVar
		self.searchResultLabel.place(x=520, y=510, width=250, height=25)

		self.selectedTreeActionVar = tk.StringVar(value='=')
		self.selectedTreeMenu = tk.Menu(self, tearoff=0)
		copy_menu = tk.Menu(self.selectedTreeMenu, tearoff=False)
		copy_menu.add_command(label='Copy address', command=self.copySelectedAddressCommand)
		copy_menu.add_command(label='Copy value', command=None)
		self.selectedTreeMenu.add_command(label='Freeze/Unfreeze', command=self.freezeAddress)
		self.selectedTreeMenu.add_command(label='Edit', command=self.editValue)
		self.selectedTreeMenu.add_cascade(label='Copy', menu=copy_menu)
		self.selectedTreeMenu.add_command(label='Delete', command=self.deleteAddress)

		self.progressBar = ttk.Progressbar(self, orient='horizontal', mode='determinate', length=100)
		self.progressBar.place(x=10, y=540, width=width-20, height=15)
	
		self.after(3000, self.updateAddressList)
	
	def updateAddressList(self):
		if len(self.selectedTree.get_children()) > 0:
			print('Updating')
			data = self.backend.update_address_list()
			for child, value in zip(self.selectedTree.get_children(), data):
				item = self.selectedTree.item(child)
				old_values = item['values']
				tags = item['tags']
				old_values[2] = self.convert_from_bytes(value, self.typeVar.get())
				self.selectedTree.item(child, values=old_values, tags=tags)
			print(data)
		self.after(3000, self.updateAddressList)

	def openTypeMenuCommand(self):
		try:
			x = self.typeButton.winfo_rootx()
			y = self.typeButton.winfo_rooty() + self.typeButton.winfo_height()
			self.popup.tk_popup(x, y, 0)
		finally:
			self.popup.grab_release()

	def openSearchTypeMenuCommand(self):
		try:         
			x = self.searchTypeButton.winfo_rootx()
			y = self.searchTypeButton.winfo_rooty() + self.searchTypeButton.winfo_height()
			self.searchTypePopup.tk_popup(x, y, 0)
		finally:
			self.searchTypePopup.grab_release()

	def scanCommand(self):
		if self.scanVar.get() == 'Started':
			return
		if self.processNameVar.get() == '':
			print('Select a process first!')
			return
		size = int(self.sizeVar.get())
		value = self.convert_to_bytes(self.searchText.get(), self.typeVar.get(), size)
		self.scanVar.set('Started')
		t = Thread(target=self.scanCommandThread, args=(value,), daemon=True)
		t.start()

	def scanCommandThread(self, value:bytes):
		self.backend.value_scan(value, self.progressBar)
		self.scanVar.set('Finished')

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
			return
		self.clear_address_table()
		self.fill_address_table()

	def openProcessMenuCommand(self):
		try:
			x = self.processButton.winfo_rootx()
			y = self.processButton.winfo_rooty() + self.processButton.winfo_height()
			self.processSelectList.tk_popup(x, y, 0)
		finally:
			self.processSelectList.grab_release()

	def processSelectCommand(self):
		self.backend.initProcessReader(self.processNameVar.get())
		self.scanVar.set('Not Started')

	def selectAddressCommand(self, event):
		item_name = self.tree.identify('item', event.x, event.y)
		item = self.tree.item(item_name)
		index = self.tree.index(item_name)
		if len(item['values']) > 0 and self.backend.selectAddress(index):
			self.selectedTree.insert('', 'end', values=['❌', *item['values']], tags=item['tags'])
	
	def rightClickAddressCommand(self, event):
		item_name = self.selectedTree.identify('item', event.x, event.y)
		item = self.selectedTree.item(item_name)
		index = self.selectedTree.index(item_name)
		self.selectedTree.selection_set(self.selectedTree.get_children()[index])
		self.selectedTree.focus(self.selectedTree.get_children()[index])
		x = self.winfo_pointerx()
		y = self.winfo_pointery()
		if len(item['values']) > 0:
			try:
				self.selectedTreeMenu.tk_popup(x, y, 0)
			finally:
				self.selectedTreeMenu.grab_release()

	def freezeAddress(self):
		item_name = self.selectedTree.focus()
		tags = self.selectedTree.item(item_name, 'tags')
		index = self.selectedTree.index(item_name)
		if 'freeze' in self.selectedTree.item(item_name, 'tags'):
			old = self.selectedTree.item(item_name)['values']
			old[0] = '❌'
			tags = [i for i in tags if i != 'freeze']
			self.selectedTree.item(item_name, values=old, tags=tags)
			self.backend.unfreezeAddress(index)
		else:
			old = self.selectedTree.item(item_name)['values']
			old[0] = '✓'
			self.selectedTree.item(item_name, values=old, tags=('freeze', *tags))
			self.backend.freezeAddress(index)
	
	def copySelectedAddressCommand(self):
		item_name = self.selectedTree.focus()
		address = self.selectedTree.item(item_name, 'values')[1]
		self.clipboard_append(address)
	
	def copySelectedValueCommand(self):
		item_name = self.selectedTree.focus()
		address = self.selectedTree.item(item_name, 'values')[2]
		self.clipboard_append(address)

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
		
		x = self.selectedTree.winfo_rootx() - self.winfo_rootx()
		y = self.selectedTree.winfo_rooty() - self.winfo_rooty() + 25 + (index + 1) * 20
		
		self.okButton['command'] = lambda: self.setValue(selection)

		self.tentry.place(x=x, y=y, width=150, height=25)
		self.okButton.place(x=x + 150, y=y, width=30, height=25)
		self.cancelButton.place(x=x + 150 + 30, y=y, width=50, height=25)

	def setValue(self, item):
		row = self.selectedTree.item(item)
		index = self.selectedTree.index(item)
		tags = row['tags']
		old_values = row['values']
		old_values[-1] = self.editVariable.get()
		self.backend.setValue(index, self.convert_to_bytes(self.editVariable.get(), tags))
		self.selectedTree.item(item, values=old_values, tags=tags)
		self.closeEdit()

	def closeEdit(self):
		self.tentry.place_forget()
		self.okButton.place_forget()
		self.cancelButton.place_forget()

	def convert_to_bytes(self, value:str, type_variable:str, size:int=4):
		if 'Integer' in type_variable:
			value = int(value).to_bytes(size, byteorder)
		if 'Float' in type_variable:
			value = struct.unpack('f', float(value))
		if 'String' in type_variable:
			value = value.decode('utf-8')
		return value

	def convert_from_bytes(self, value:bytes, value_type:str):
		if value_type == 'Integer':
			value = int.from_bytes(value, byteorder)
		if value_type == 'Float':
			value = struct.pack('f', float(value))
		if value_type == 'String':
			value = value.encode('utf-8')
		return value

	def clear_address_table(self):
		self.tree.delete(*self.tree.get_children())

	def fill_address_table(self):
		address_list = self.backend.get_address_list(self.typeVar.get())
		for address in address_list:
			self.tree.insert('', 'end', values=address['values'], tags=[self.typeVar.get()])
		self.searchResultVar.set(f'Found {len(address_list)} results.')

	def on_closing(self):
		self.backend.stop_loop()
		self.destroy()

	def inputListener(self, *args):
		print(self.searchText.get())

	def scanStatusListener(self, *args):
		if self.scanVar.get() == 'Finished':
			self.clear_address_table()
			self.fill_address_table()

if __name__ == "__main__":
	app = App()
	app.mainloop()
