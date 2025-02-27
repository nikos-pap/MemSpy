from utils.types import convert_to_bytes, convert_from_bytes, Type
from guiwidgets.address_list import AddressList
from PIL import ImageTk
from threading import Thread
from backend import Backend
from tkinter import ttk
import tkinter as tk


class App(tk.Tk):
	def __init__(self):
		tk.Tk.__init__(self)
		self.protocol("WM_DELETE_WINDOW", self.on_closing)
		self.backend = Backend()
		self.images = []
		# Configuring Window
		self.title("Mem Scanner")
		width = 1000
		height = 700
		horizontal_spacing = 10
		screenwidth = self.winfo_screenwidth()
		screenheight = self.winfo_screenheight()
		alignstr = f'{width}x{height}+{(screenwidth - width) // 2}+{(screenheight - height) // 2}'
		self.geometry(alignstr)
		self.resizable(width=False, height=False)
		self.isAttached = False
		tree_view_style = ttk.Style()
		tree_view_style.map('Treeview', background=[('selected', 'lightblue')], foreground=[('selected', 'red')])

		# Search input field
		self.searchText = tk.StringVar()
		self.searchText.trace_add('write', callback=self.input_listener)
		self.searchbox = ttk.Entry(self)
		self.searchbox['textvariable'] = self.searchText

		# Search value type
		self.typeVar = tk.StringVar(value='UInt32')
		self.typeButton = ttk.Button(self)
		self.typeButton["textvariable"] = self.typeVar
		self.typeButton["command"] = self.open_value_type_menu_command

		self.popup = tk.Menu(self, tearoff=0)
		self.popup.add_radiobutton(label='SByte', variable=self.typeVar, value='SByte')
		self.popup.add_radiobutton(label='Int16', variable=self.typeVar, value='Int16')
		self.popup.add_radiobutton(label='Int32', variable=self.typeVar, value='Int32')
		self.popup.add_radiobutton(label='Int64', variable=self.typeVar, value='Int64')
		self.popup.add_radiobutton(label='UInt16', variable=self.typeVar, value='UInt16')
		self.popup.add_radiobutton(label='UInt32', variable=self.typeVar, value='UInt32')
		self.popup.add_radiobutton(label='UInt64', variable=self.typeVar, value='UInt64')
		self.popup.add_radiobutton(label='Float', variable=self.typeVar, value='Float')
		self.popup.add_radiobutton(label='Double', variable=self.typeVar, value='Double')
		self.popup.add_radiobutton(label='String', variable=self.typeVar, value='String')

		# Scan Button
		self.scanButton = ttk.Button(self)
		self.scanButton["text"] = "New Scan"
		self.scanButton["command"] = self.scan_command
		self.scanVar = tk.StringVar(value='Not Started')
		self.scanVar.trace_add('write', callback=self.scan_status_command)

		# Filter Button
		self.filterButton = ttk.Button(self)
		self.filterButton["text"] = "Filter"
		self.filterButton["command"] = self.filter_command

		# Search type
		self.searchTypePopup = tk.Menu(self, tearoff=0)
		self.changeVar = tk.StringVar(value='=')
		self.searchTypePopup.add_radiobutton(label='Equal to (=)', variable=self.changeVar, value='=')
		self.searchTypePopup.add_radiobutton(label='Not Equal to (!=)', variable=self.changeVar, value='!=')
		self.searchTypePopup.add_radiobutton(label='Greater than (>)', variable=self.changeVar, value='>')
		self.searchTypePopup.add_radiobutton(label='Less than (<)', variable=self.changeVar, value='<')
		self.searchTypePopup.add_separator()
		self.searchTypePopup.add_radiobutton(label='Decreased (-)', variable=self.changeVar, value='-')
		self.searchTypePopup.add_radiobutton(label='Increased (+)', variable=self.changeVar, value='+')
		self.searchTypePopup.add_radiobutton(label='Changed (-/+)', variable=self.changeVar, value='-/+')
		self.searchTypePopup.add_radiobutton(label='Not Changed (==)', variable=self.changeVar, value='==')

		self.searchTypeButton = ttk.Button(self)
		self.searchTypeButton["textvariable"] = self.changeVar
		self.searchTypeButton["command"] = self.open_search_type_menu_command

		tree_view_style.configure('T1.Treeview', rowheight=35)
		self.processTree = ttk.Treeview(self, columns=('c1',), padding=[-15, 0, 0, 0], show='tree', style='T1.Treeview')
		self.processTree.column('#0', width=55, stretch=False)
		self.processTree.column('c1', width=150, anchor='w')

		self.choose_process = ttk.Button(self, text='Select', command=self.process_select_command)
		tree_view_style.configure('R.TButton', font=('Helvetica', 12, 'bold'), foreground='green')
		self.refreshProcessButton = ttk.Button(self, text='⟳', style='R.TButton', command=self.update_process_list_command)
		process_scrollbar = ttk.Scrollbar(self.processTree, orient="vertical", command=self.processTree.yview)

		self.processTree.configure(yscrollcommand=process_scrollbar.set)

		# selected item list
		self.selectedTree = ttk.Treeview(self, columns=('c1', 'c2', 'c3'), show='headings')
		self.selectedTree.column("c1", anchor=tk.CENTER, minwidth=50, width=50, stretch=False)
		self.selectedTree.heading("c1", text="Freeze")
		self.selectedTree.column("c2", anchor=tk.CENTER, minwidth=309, width=309, stretch=False)
		self.selectedTree.heading("c2", text="Address")
		self.selectedTree.column("c3", anchor=tk.CENTER, minwidth=309, width=309, stretch=False)
		self.selectedTree.heading("c3", text="value")
		self.selectedTree.bind('<Button-3>', self.right_click_address_command)
		self.selectedTree.bind('<Motion>', 'break')

		self.selectedTree.tag_configure('freeze', foreground='green')

		# edit value menu
		self.editVariable = tk.StringVar()

		self.tentry = ttk.Entry(self)
		self.tentry['textvariable'] = self.editVariable
		self.tentry['justify'] = 'right'
		self.okButton = ttk.Button(self, padding='0 0 0 0')
		self.okButton['text'] = 'ΟK'

		self.cancelButton = ttk.Button(self, padding='0 0 0 0')
		self.cancelButton['text'] = 'Cancel'
		self.cancelButton['command'] = self.close_edit

		# search result list
		self.tree = AddressList(self)
		self.tree.tree_command(self.select_address_command)

		self.selectedTreeActionVar = tk.StringVar(value='=')
		self.selectedTreeMenu = tk.Menu(self, tearoff=0)
		copy_menu = tk.Menu(self.selectedTreeMenu, tearoff=False)
		copy_menu.add_command(label='Copy address', command=self.copy_selected_address_command)
		copy_menu.add_command(label='Copy value', command=self.copy_selected_value_command)
		self.selectedTreeMenu.add_command(label='Freeze/Unfreeze', command=self.freeze_address)
		self.selectedTreeMenu.add_command(label='Edit', command=self.edit_value)
		self.selectedTreeMenu.add_cascade(label='Copy', menu=copy_menu)
		self.selectedTreeMenu.add_command(label='Delete', command=self.delete_address)
		self.progressBar = ttk.Progressbar(self, orient='horizontal', mode='determinate', length=100)
		w_width = 130
		button_bar_height = 30
		vertical_spacing = 10
		x = horizontal_spacing
		y = vertical_spacing
		self.searchbox.place(x=x, y=y, width=w_width, height=button_bar_height)
		x += horizontal_spacing + w_width
		w_width = 50
		self.typeButton.place(x=x, y=y, width=w_width, height=button_bar_height)
		x += horizontal_spacing + w_width
		w_width = 40
		self.searchTypeButton.place(x=x, y=y, width=w_width, height=button_bar_height)
		x += horizontal_spacing + w_width
		w_width = 70
		self.scanButton.place(x=x, y=y, width=w_width, height=button_bar_height)
		x += horizontal_spacing + w_width
		w_width = 70
		self.filterButton.place(x=x, y=y, width=w_width, height=button_bar_height)
		x = horizontal_spacing
		y += button_bar_height + vertical_spacing
		w_width = 250
		self.processTree.place(x=x, y=y, width=w_width, height=320)
		process_scrollbar.place(x=232, y=1, height=318)
		y += 320 + 5
		self.choose_process.place(x=x, y=y, height=30, width=50)
		self.refreshProcessButton.place(x=x + 55, y=y, height=30, width=30)
		w_width = 300
		x = width - w_width - horizontal_spacing
		self.tree.place(x=x, y=0, width=w_width, height=670)
		w_height = 250
		self.selectedTree.place(x=horizontal_spacing, y=height - w_height - 35, width=width - w_width - 30, height=w_height)
		w_height = 15
		y = height - vertical_spacing - w_height
		self.progressBar.place(x=horizontal_spacing, y=y, width=width - horizontal_spacing * 2, height=w_height)

		self.update_process_list_command()
		self.after(3000, self.update_address_list)
	
	def update_address_list(self):
		if len(self.selectedTree.get_children()) > 0:
			data = self.backend.update_address_list()
			for child, value in zip(self.selectedTree.get_children(), data):
				item = self.selectedTree.item(child)
				old_values = item['values']
				tags = item['tags']
				old_values[2] = convert_from_bytes(value, Type[self.typeVar.get()])
				self.selectedTree.item(child, values=old_values, tags=tags)
		self.after(3000, self.update_address_list)

	def open_value_type_menu_command(self):
		x = self.typeButton.winfo_rootx()
		y = self.typeButton.winfo_rooty() + self.typeButton.winfo_height()
		try:
			self.popup.tk_popup(x, y, 0)
		finally:
			self.popup.grab_release()

	def open_search_type_menu_command(self):
		x = self.searchTypeButton.winfo_rootx()
		y = self.searchTypeButton.winfo_rooty() + self.searchTypeButton.winfo_height()
		try:
			self.searchTypePopup.tk_popup(x, y, 0)
		finally:
			self.searchTypePopup.grab_release()

	def scan_command(self):
		if self.scanVar.get() == 'Started':
			return
		if not self.isAttached:
			print('Select a process first!')
			return
		value = convert_to_bytes(self.searchText.get(), Type[self.typeVar.get()])
		if value is None:
			return
		self.scanVar.set('Started')
		t = Thread(target=self.scan_command_thread, args=(value,), daemon=True)
		t.start()

	def scan_command_thread(self, value: bytes):
		self.backend.value_scan(value, self.progressBar)
		self.scanVar.set('Finished')

	def filter_command(self):
		scan_status = self.scanVar.get()
		if scan_status == 'Not Started':
			print('Execute a scan before you start a filter')
			return
		if scan_status == 'Started':
			print('Finish the scan before you start a filter')
			return
		if scan_status != 'Finished':
			raise Exception(f'Invalid scanVar value?: {scan_status}')

		value = convert_to_bytes(self.searchText.get(), Type[self.typeVar.get()])
		if value is None:
			return
		if self.changeVar.get() == '=':
			self.backend.filter_address_list(lambda a, b: a == b, value)
		elif self.changeVar.get() == '!=':
			self.backend.filter_address_list(lambda a, b: a != b, value)
		elif self.changeVar.get() == '>':
			self.backend.filter_address_list(lambda a, b: a > b, value)
		elif self.changeVar.get() == '<':
			self.backend.filter_address_list(lambda a, b: a < b, value)
		elif self.changeVar.get() == '+':
			self.backend.filter_address_list(lambda a, b: a > b, None)
		elif self.changeVar.get() == '-':
			self.backend.filter_address_list(lambda a, b: a < b, None)
		elif self.changeVar.get() == '==':
			self.backend.filter_address_list(lambda a, b: a == b, None)
		elif self.changeVar.get() == '-/+':
			self.backend.filter_address_list(lambda a, b: a != b, None)
		else:
			print(f'Not Implemented yet {self.changeVar.get()}')
			return
		self.clear_address_table()
		self.fill_address_table()

	def update_process_list_command(self):
		self.processTree.delete(*self.processTree.get_children())
		names, images, pids = self.backend.running_processes
		self.images = []
		for image, name, pid in zip(images, names, pids):
			if image is not None:
				img = ImageTk.PhotoImage(image)
				self.images.append(img)
				self.processTree.insert('', 'end', image=img, values=[f'{name} ({pid})'], tags=[name])
			else:
				self.processTree.insert('', 'end', values=[f'{name} ({pid})'], tags=[name])

	def process_select_command(self):
		self.tree.clear_addresses()
		self.selectedTree.delete(*self.selectedTree.get_children())
		item = self.processTree.item(self.processTree.focus())
		self.backend.init_process_reader(item["tags"][0])
		self.scanVar.set('Not Started')
		self.title(f'Mem Scanner - {item["values"][0]}')
		self.isAttached = True

	def select_address_command(self, event):
		item, index = self.tree.identify('item', event.x, event.y)
		if len(item['values']) > 0 and self.backend.select_address(index):
			self.selectedTree.insert('', 'end', values=['❌', *item['values']], tags=item['tags'])
	
	def right_click_address_command(self, event):
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

	def freeze_address(self):
		item_name = self.selectedTree.focus()
		tags = self.selectedTree.item(item_name, 'tags')
		index = self.selectedTree.index(item_name)
		if 'freeze' in self.selectedTree.item(item_name, 'tags'):
			old = self.selectedTree.item(item_name)['values']
			old[0] = '❌'
			tags = [i for i in tags if i != 'freeze']
			self.selectedTree.item(item_name, values=old, tags=tags)
			self.backend.unfreeze_address(index)
		else:
			old = self.selectedTree.item(item_name)['values']
			old[0] = '✓'
			self.selectedTree.item(item_name, values=old, tags=('freeze', *tags))
			self.backend.freeze_address(index)
	
	def copy_selected_address_command(self):
		address = self.selectedTree.item(self.selectedTree.focus(), 'values')[1]
		self.clipboard_clear()
		self.clipboard_append(address)
	
	def copy_selected_value_command(self):
		address = self.selectedTree.item(self.selectedTree.focus(), 'values')[2]
		self.clipboard_clear()
		self.clipboard_append(address)

	def delete_address(self):
		item_name = self.selectedTree.focus()
		index = self.selectedTree.index(item_name)
		self.backend.delete_address(index)
		self.selectedTree.delete(item_name)

	def edit_value(self):
		selection = self.selectedTree.focus()
		item = self.selectedTree.item(selection)
		index = self.selectedTree.index(selection)
		self.editVariable.set(item['values'][-1])
		
		x = self.selectedTree.winfo_rootx() - self.winfo_rootx()
		y = self.selectedTree.winfo_rooty() - self.winfo_rooty() + 25 + (index + 1) * 20
		
		self.okButton['command'] = lambda: self.set_value(selection)

		self.tentry.place(x=x, y=y, width=150, height=25)
		self.okButton.place(x=x + 150, y=y, width=30, height=25)
		self.cancelButton.place(x=x + 150 + 30, y=y, width=50, height=25)

	def set_value(self, item):
		row = self.selectedTree.item(item)
		index = self.selectedTree.index(item)
		tags = row['tags']
		old_values = row['values']
		old_values[-1] = self.editVariable.get()
		value_type = Type['Int32']
		for tag in tags:
			if tag in Type.__members__:
				value_type = Type[tag]
		self.backend.set_value(index, convert_to_bytes(self.editVariable.get(), value_type))
		self.selectedTree.item(item, values=old_values, tags=tags)
		self.close_edit()

	def close_edit(self):
		self.tentry.place_forget()
		self.okButton.place_forget()
		self.cancelButton.place_forget()

	def clear_address_table(self):
		self.tree.clear_addresses()

	def fill_address_table(self):
		address_list = self.backend.get_address_list(Type[self.typeVar.get()])
		self.tree.load_addresses(address_list, self.typeVar.get())
		self.tree.show_page()

	def on_closing(self):
		self.backend.stop_loop()
		self.destroy()

	def input_listener(self, *args):
		print(self.searchText.get())

	def scan_status_command(self, *args):
		if self.scanVar.get() == 'Finished':
			self.clear_address_table()
			self.fill_address_table()


if __name__ == "__main__":
	app = App()
	app.mainloop()
