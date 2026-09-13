"""Isolated COM availability probe, called under the runner's cross-process lock."""
import json
import sys

def main():
    app = None
    try:
        import winreg
        import win32com.client
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\HNC\HwpAutomation\Modules') as key:
            module, _ = winreg.QueryValueEx(key, 'FilePathCheckerModule')
        app = win32com.client.DispatchEx('HWPFrame.HwpObject')
        registered = bool(app.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule'))
        print(json.dumps({'registered': registered, 'module': module, 'version': str(app.Version)}, ensure_ascii=False))
        return 0 if registered else 1
    except Exception as exc:
        print(str(exc)); return 1
    finally:
        if app is not None:
            app.Quit()

if __name__ == '__main__':
    sys.exit(main())
