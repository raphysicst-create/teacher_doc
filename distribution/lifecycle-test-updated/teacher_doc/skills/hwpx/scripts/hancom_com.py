"""Hancom COM preflight and ownership; never changes Windows/Codex permissions."""
from contextlib import contextmanager
import os
from pathlib import Path


def preflight():
    if os.name != 'nt':
        raise RuntimeError('Hancom COM validation is only available on Windows.')
    import win32api
    import win32security
    import win32service
    import winreg

    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
    try:
        restricted = bool(win32security.IsTokenRestricted(token))
    finally:
        token.Close()
    user = win32api.GetUserName()
    desktop = win32service.GetUserObjectInformation(
        win32service.GetThreadDesktop(win32api.GetCurrentThreadId()), 2)
    if restricted or desktop.startswith('CodexSandboxDesktop-') or user.lower().startswith('codexsandbox'):
        raise RuntimeError(
            f'HANCOM_RESTRICTED_CONTEXT: user={user}; desktop={desktop}; restricted={restricted}. '
            '이 Windows 제한 실행 환경에서는 한글 COM 생성이 멈출 수 있어 호출 전에 중단했습니다. '
            '한글과 보안 모듈이 설치된 사용자 세션에서 검증하세요. '
            'Codex 권한은 자동 변경하지 않으며 이 결과는 검증 통과가 아닙니다.')
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\HNC\HwpAutomation\Modules') as key:
            module, _ = winreg.QueryValueEx(key, 'FilePathCheckerModule')
    except OSError as exc:
        raise RuntimeError('HANCOM_MODULE_MISSING: 현재 사용자 HKCU에 FilePathCheckerModule 등록이 없습니다.') from exc
    if not Path(module).is_file():
        raise RuntimeError('HANCOM_MODULE_MISSING: 보안 모듈 DLL을 찾을 수 없습니다: ' + str(module))
    return {'user': user, 'desktop': desktop, 'restricted': restricted, 'module': module}


@contextmanager
def session(*, visible=False):
    context = preflight()
    import win32com.client
    # A separately owned instance avoids attaching to and quitting the user's editor.
    app = win32com.client.DispatchEx('HWPFrame.HwpObject')
    try:
        if not app.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule'):
            raise RuntimeError('HANCOM_MODULE_REJECTED: 보안 모듈 등록 실패; 파일 열기를 중단했습니다.')
        app.XHwpWindows.Item(0).Visible = visible
        yield app, context
    finally:
        app.Quit()
