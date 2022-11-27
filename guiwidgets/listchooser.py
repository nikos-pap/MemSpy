import tkinter as tk

from PIL import Image, ImageTk


class ListChooser(tk.Frame):

	def __init__(self, parent, item_height=20, vertical_spacing: int = 0, *args, **kwargs):
		tk.Frame.__init__(self, parent, *args, **kwargs)
		self.selected = -1
		self.button_list = []
		self.image_list = []
		self.item_height = item_height
		self.vertical_spacing = vertical_spacing
		self.list_y = 0

	def add_choice(self, text: str, image: Image.Image = None):
		_image = None
		if image is not None:
			_image = ImageTk.PhotoImage(image.resize((self.item_height, self.item_height)))
			self.image_list.append(_image)

		self.button_list.append(tk.Button(self, text=text, image=_image, relief='flat'))

	def place(self, x=0, y=0, **kwargs):
		super().place(x=x, y=y, **kwargs)
		y = self.list_y
		for button in self.button_list:
			button.place(x=0, y=y, height=self.item_height, width=self.winfo_width())
			y += self.item_height + self.vertical_spacing
