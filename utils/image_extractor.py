from PIL import Image
import win32ui
import win32gui
import win32con
import win32api
import os


# noinspection SpellCheckingInspection
def get_process_image(path: str):
	path = os.path.abspath(path)
	if not os.path.exists(path):
		return None
	ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)

	large, small = win32gui.ExtractIconEx(path, 0)
	if len(small) > 0:
		for icon in small:
			win32gui.DestroyIcon(icon)
	if len(large) == 0:
		return None

	# creating a destination memory DC
	hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
	hbmp = win32ui.CreateBitmap()
	hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_x)
	hdc = hdc.CreateCompatibleDC()

	hdc.SelectObject(hbmp)

	# draw icon in it
	hdc.DrawIcon((0, 0), large[0])
	for icon in large:
		win32gui.DestroyIcon(icon)

	bmpinfo = hbmp.GetInfo()
	bmpstr = hbmp.GetBitmapBits(True)
	im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
	return im
