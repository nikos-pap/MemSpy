import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass


class AddressList(tk.Frame):
	def __init__(self, parent, spacing=10, *args, **kargs):
		tk.Frame.__init__(self, parent, *args, **kargs)
		self.spacing = spacing

		# controls
		self.searchAddressText = tk.StringVar()
		self.search_box = ttk.Entry(self)
		self.search_box['textvariable'] = self.searchAddressText
		self.searchAddressText.trace_add('write', callback=self.search_command)
		self.first_page_button = ttk.Button(self)
		self.first_page_button["text"] = "<<"
		self.first_page_button["command"] = self.show_first_page
		self.previous_page_button = ttk.Button(self)
		self.previous_page_button["text"] = "<"
		self.previous_page_button["command"] = self.show_previous_page
		self.next_page_button = ttk.Button(self)
		self.next_page_button["text"] = ">"
		self.next_page_button["command"] = self.show_next_page
		self.last_page_button = ttk.Button(self)
		self.last_page_button["text"] = ">>"
		self.last_page_button["command"] = self.show_last_page

		self.address_list = []
		self.filtered_list = []
		self.page_size = 200
		self.page_index = 0

		self.tree = ttk.Treeview(self, columns=('c1', 'c2'), show='headings')
		self.tree.column("c1", anchor=tk.W, minwidth=149, width=149, stretch=False)
		self.tree.heading("c1", text="Address")
		self.tree.column("c2", anchor=tk.W, minwidth=149, width=149, stretch=False)
		self.tree.heading("c2", text="Value")
		self.tree.bind('<Motion>', 'break')
		self.tree_scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
		self.tree.configure(yscrollcommand=self.tree_scrollbar.set)

		self.rowCountVar = tk.StringVar(value='')
		self.rowCountLabel = ttk.Label(self)
		self.rowCountLabel["textvariable"] = self.rowCountVar
		self.current_page = 0

	def place(self, x, y, height, width):
		super().place(x=x, y=y, height=height, width=width)
		self.search_box.place(x=0, y=self.spacing, height=30, width=width / 2)
		self.first_page_button.place(x=width / 2 + self.spacing / 2, y=self.spacing, height=30, width=30)
		self.previous_page_button.place(x=width / 2 + self.spacing + 30, y=self.spacing, height=30, width=30)
		self.next_page_button.place(x=width / 2 + self.spacing * 1.5 + 60, y=self.spacing, height=30, width=30)
		self.last_page_button.place(x=width / 2 + self.spacing * 2 + 90, y=self.spacing, height=30, width=30)
		height = height - 30 - 2 * self.spacing - 25
		self.tree.place(x=0, y=30 + 2 * self.spacing, height=height, width=width)
		self.tree_scrollbar.place(x=width - 18, y=1, height=height - 2)
		self.rowCountLabel.place(x=0, y=30 + 2 * self.spacing + height, width=width, height=25)

	def load_addresses(self, address_list, data_type:str):
		self.address_list = [AddressEntry(i[0], i[1], data_type) for i in address_list]
		self.filtered_list = self.address_list

	def show_page(self, page_num: int = 0):
		total_pages = len(self.filtered_list) / self.page_size
		if total_pages < page_num or page_num < 0:
			return
		self.page_index = page_num
		self.tree.delete(*self.tree.get_children())
		start_index = page_num * self.page_size
		for index, address in enumerate(self.filtered_list[start_index:min(start_index + self.page_size, len(self.filtered_list))]):
			self.tree.insert('', 'end', values=(address.address, address.value), tags=[address.value_type, index])
		self.rowCountVar.set(f'Page {page_num + 1}/{int(total_pages) + 1}, Total addresses {len(self.filtered_list)}.')

	def show_next_page(self):
		self.show_page(self.page_index + 1)

	def show_previous_page(self):
		self.show_page(self.page_index - 1)

	def show_last_page(self):
		self.show_page(len(self.filtered_list) // self.page_size)

	def show_first_page(self):
		self.show_page(0)

	def fill_address_list(self, address_list):
		for address in address_list:
			self.address_list.append(address)

	def identify(self, item, x, y):
		item_name = self.tree.identify(item, x, y)
		item = self.tree.item(item_name)
		index = item['tags'][1]
		return item, index

	def clear_addresses(self):
		self.tree.delete(*self.tree.get_children())
		self.address_list = []
		self.filtered_list = []
		self.rowCountVar.set('')
		self.searchAddressText.set('')

	def tree_command(self, command):
		self.tree.bind('<Double-1>', command)

	def search_command(self, *args):
		text = self.searchAddressText.get().strip()
		if not text:
			return

		self.filtered_list = list(filter(lambda a: text in a.address, self.address_list))
		self.show_page()


@dataclass
class AddressEntry:
	address: str
	value: str
	value_type: str

	def __repr__(self):
		return self.address
