import ctypes
import json
import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path

def log(stage, **data):
    print(json.dumps(dict(stage=stage, seconds=round(time.monotonic()-start, 3), **data), ensure_ascii=False), flush=True)

start = time.monotonic()
if len(sys.argv) > 1 and sys.argv[1] == 'worker':
    import win32api
    import win32com.client
    import win32service
    import winreg
    desktop = win32service.GetThreadDesktop(win32api.GetCurrentThreadId())
    log('environment', user=win32api.GetUserName(), desktop=win32service.GetUserObjectInformation(desktop, 2))
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\HNC\HwpAutomation\Modules') as key:
            module, _ = winreg.QueryValueEx(key, 'FilePathCheckerModule')
        log('module', path=module, exists=Path(module).is_file())
    except OSError as e:
        log('module-error', error=str(e))
    app = None
    try:
        log('dispatch-start')
        app = win32com.client.DispatchEx('HWPFrame.HwpObject')
        log('dispatch-done')
        log('register', result=bool(app.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')))
        log('version', value=str(app.Version))
        if len(sys.argv) > 2:
            log('open-start')
            log('open-done', result=bool(app.Open(str(Path(sys.argv[2]).resolve()), 'HWPX', '')))
            log('pages', value=int(app.PageCount))
    except Exception as e:
        log('error', error=str(e))
        raise
    finally:
        if app is not None:
            log('quit-start')
            app.Quit()
            log('quit-done')
else:
    with tempfile.TemporaryFile() as out:
        try:
            r = subprocess.run([sys.executable, '-B', '-X', 'utf8', __file__, 'worker', *sys.argv[1:]], stdout=out, stderr=out, timeout=25)
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = 124
        out.seek(0)
        print(out.read().decode('utf-8', errors='replace'), end='')
        log('worker-exit', code=code)
        sys.exit(code)
