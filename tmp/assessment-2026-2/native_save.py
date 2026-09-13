from pathlib import Path
import win32com.client as win32
w=Path(__file__).resolve().parent
h=win32.DispatchEx('HWPFrame.HwpObject')
try:
 h.RegisterModule('FilePathCheckDLL','FilePathCheckerModule')
 h.XHwpWindows.Item(0).Visible=False
 assert h.Open(str(w/'notice.hwpx'),'HWPX','forceopen:true')
 print('pages',h.PageCount)
 assert h.SaveAs(str(w/'notice-native.hwpx'),'HWPX','')
finally:h.Quit()
