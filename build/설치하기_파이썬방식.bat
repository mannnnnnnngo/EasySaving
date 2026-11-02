@echo off
setlocal EnableDelayedExpansion
title Easy Saving 설치 (파이썬 방식 - 차단 없음)

rem ============================================================
rem  .exe 를 만들지 않고 파이썬으로 바로 실행하는 설치 방법.
rem  윈도우 11 "스마트 앱 컨트롤" 이나 SmartScreen 에 걸리지 않습니다.
rem  ※ 이 파일은 CP949 로 저장되어 있습니다. chcp 를 넣지 마세요.
rem ============================================================

cd /d "%~dp0\.."
set PROJ=%CD%
set ESPROJ=%CD%

cls
echo.
echo  ============================================================
echo    Easy Saving 설치 (파이썬 방식)
echo    PDF 를 한 장씩 잘라 저장해 주는 프로그램입니다.
echo  ============================================================
echo    프로그램 폴더: %PROJ%
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo  [오류] 파이썬을 찾을 수 없습니다.
    echo         https://www.python.org/downloads/ 에서 파이썬 3.9 이상을 설치하고,
    echo         설치 화면에서 "Add Python to PATH" 를 꼭 체크해 주세요.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [1/4] 파이썬 %PYVER% 확인 완료

if not exist ".venv\Scripts\pythonw.exe" (
    echo  [2/4] 실행 환경 만드는 중...
    python -m venv .venv
    if errorlevel 1 (
        echo  [오류] 실행 환경을 만들지 못했습니다.
        pause
        exit /b 1
    )
) else (
    echo  [2/4] 실행 환경 재사용
)

echo  [3/4] 필요한 라이브러리 설치 중 (pypdf, pymupdf, python-pptx)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo  [오류] 라이브러리 설치 실패. 인터넷 연결을 확인해 주세요.
    pause
    exit /b 1
)

if not exist "assets\easysaving.ico" (
    ".venv\Scripts\python.exe" tools\make_icon.py >nul 2>&1
)

echo  [4/4] 바탕 화면 바로가기 만드는 중...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $p = $env:ESPROJ; $icon = Join-Path $p 'assets\easysaving.ico'; if (-not (Test-Path $icon)) { $icon = Join-Path $p '.venv\Scripts\pythonw.exe' }; foreach ($dir in @([Environment]::GetFolderPath('Desktop'), $env:APPDATA + '\Microsoft\Windows\Start Menu\Programs')) { $lnk = $ws.CreateShortcut((Join-Path $dir 'Easy Saving.lnk')); $lnk.TargetPath = Join-Path $p '.venv\Scripts\pythonw.exe'; $lnk.Arguments = 'run.py'; $lnk.WorkingDirectory = $p; $lnk.IconLocation = $icon; $lnk.Description = 'PDF 를 한 장씩 잘라 저장'; $lnk.Save() }"
if errorlevel 1 (
    echo  [경고] 바로가기를 만들지 못했습니다. 아래 방법으로 직접 실행하세요.
    echo         %PROJ%\실행하기.vbs
)

rem 언제든 직접 실행할 수 있는 파일도 만들어 둔다.
rem .bat 은 켤 때마다 콘솔 창이 번쩍 떠서, 창 없이 실행되는 .vbs 를 복사해 둔다.
if exist "%PROJ%\실행하기.bat" del "%PROJ%\실행하기.bat"
copy /y "build\launch.vbs" "%PROJ%\실행하기.vbs" >nul

echo.
set /p AUTO=  윈도우를 켤 때 자동으로 실행할까요? (Y/N) 
if /i "!AUTO!"=="Y" (
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $p = $env:ESPROJ; $lnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'Easy Saving.lnk')); $lnk.TargetPath = Join-Path $p '.venv\Scripts\pythonw.exe'; $lnk.Arguments = 'run.py'; $lnk.WorkingDirectory = $p; $lnk.Save()"
    echo   자동 실행을 켰습니다.
)

echo.
echo  ============================================================
echo    설치가 끝났습니다!
echo  ============================================================
echo    - 바탕 화면의 "Easy Saving" 아이콘을 더블클릭하세요.
echo    - 처음 실행하면 사용법 튜토리얼이 자동으로 뜹니다.
echo    - 제거: 바탕 화면/시작 메뉴의 바로가기를 지우고,
echo            이 폴더를 삭제하면 끝입니다.
echo.
set /p LAUNCH=  지금 바로 실행할까요? (Y/N) 
if /i "!LAUNCH!"=="Y" start "" ".venv\Scripts\pythonw.exe" run.py

echo.
echo   창을 닫아도 됩니다.
timeout /t 5 >nul
endlocal
