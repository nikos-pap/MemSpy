import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass


class AddressList(tk.Frame):
	def __init__(self, parent, vertical_spacing=10, *args, **kargs):
		tk.Frame.__init__(self, parent, *args, **kargs)
		self.vertical_spacing = vertical_spacing
		self.searchText = tk.StringVar()
		self.searchText.trace_add('write', callback=self.input_listener)
		self.search_box = ttk.Entry(self)
		self.search_box['textvariable'] = self.searchText
		self.address_list = []
		self.tree = ttk.Treeview(self, columns=('c1', 'c2'), show='headings')
		self.tree.column("c1", anchor=tk.W, minwidth=149, width=149, stretch=False)
		self.tree.heading("c1", text="Address")
		self.tree.column("c2", anchor=tk.W, minwidth=149, width=149, stretch=False)
		self.tree.heading("c2", text="Value")
		self.tree.bind('<Motion>', 'break')
		self.tree_scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
		self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
		self.rowCountVar = tk.StringVar(value='Showing 0 addresses.')
		self.rowCountLabel = ttk.Label(self, text='Makaronia')
		self.rowCountLabel["textvariable"] = self.rowCountVar

	def place(self, x, y, height, width):
		super().place(x=x, y=y, height=height, width=width)
		self.search_box.place(x=0, y=self.vertical_spacing, height=30, width=width / 2)
		height = height - 30 - 2 * self.vertical_spacing - 25
		self.tree.place(x=0, y=30 + 2 * self.vertical_spacing, height=height, width=width)
		self.tree_scrollbar.place(x=width - 18, y=1, height=height - 2)
		self.rowCountLabel.place(x=0, y=30 + 2 * self.vertical_spacing + height, width=width, height=25)

	def insert(self, values, tags):
		self.address_list.append(AddressEntry(values[0], values[1], tags[0]))
		if self.searchText.get() in values[0]:
			self.tree.insert('', 'end', values=values, tags=tags + [len(self.address_list) - 1])
		self.rowCountVar.set(f'Showing {len(self.tree.get_children())} addresses.')

	def identify(self, item, x, y):
		item_name = self.tree.identify(item, x, y)
		item = self.tree.item(item_name)
		index = item['tags'][1]
		return item, index

	def clear_addresses(self):
		self.tree.delete(*self.tree.get_children())
		self.address_list = []
		self.rowCountVar.set('Showing 0 addresses.')
		self.searchText.set('')

	def input_listener(self, *args):
		row_num = 0
		self.tree.delete(*self.tree.get_children())

		for index, address in enumerate(self.address_list):
			if self.searchText.get() in address.address:
				self.tree.insert('', 'end', values=[address.address, address.value], tags=[address.value_type, index])
				row_num += 1
		self.rowCountVar.set(f'Showing {row_num} addresses.')

	def tree_command(self, command):
		self.tree.bind('<Double-1>', command)


@dataclass
class AddressEntry:
	address: str
	value: str
	value_type: str

	def __repr__(self):
		return self.address
