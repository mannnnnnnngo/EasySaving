@echo off
setlocal EnableDelayedExpansion
title Easy Saving 설치

rem  ※ 이 파일은 CP949 로 저장되어 있습니다. chcp 를 넣지 마세요.

set APPNAME=Easy Saving
set EXENAME=EasySaving.exe
set INSTALLDIR=%LOCALAPPDATA%\Programs\EasySaving
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
set REGKEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\EasySaving
set RUNKEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run

cd /d "%~dp0"

cls
echo.
echo  ============================================================
echo    %APPNAME% 설치
echo    PDF 를 한 장씩 잘라 저장해 주는 프로그램입니다.
echo  ============================================================
echo.

set SOURCE=%~dp0%EXENAME%
if not exist "%SOURCE%" (
    if exist "%~dp0dist\%EXENAME%" (
        set SOURCE=%~dp0dist\%EXENAME%
    ) else (
        echo  [오류] %EXENAME% 을 찾을 수 없습니다.
        echo         이 파일과 %EXENAME% 을 같은 폴더에 두고 다시 실행해 주세요.
        echo.
        pause
        exit /b 1
    )
)

echo   설치 위치 : %INSTALLDIR%
echo   바로가기  : 바탕 화면 + 시작 메뉴
echo.
set /p GO=  설치를 시작할까요? (Y/N) 
if /i not "!GO!"=="Y" (
    echo.
    echo   설치를 취소했습니다.
    timeout /t 2 >nul
    exit /b 0
)

echo.
echo  [1/5] 실행 중인 이전 버전 종료...
taskkill /f /im %EXENAME% >nul 2>&1

echo  [2/5] 파일 복사...
if not exist "%INSTALLDIR%" mkdir "%INSTALLDIR%" 2>nul
copy /y "%SOURCE%" "%INSTALLDIR%\%EXENAME%" >nul
if errorlevel 1 (
    echo  [오류] 파일을 복사하지 못했습니다. 백신이 막고 있는지 확인해 주세요.
    pause
    exit /b 1
)
rem 인터넷에서 받은 파일 표시(Mark of the Web)를 지워, 설치된 exe 를 켤 때마다
rem 파란 "Windows의 PC 보호" 창이 뜨지 않게 한다.
powershell -NoProfile -Command "Unblock-File -LiteralPath ($env:LOCALAPPDATA + '\Programs\EasySaving\EasySaving.exe')" >nul 2>&1
if exist "%~dp0easysaving.ico" copy /y "%~dp0easysaving.ico" "%INSTALLDIR%\easysaving.ico" >nul
if exist "%~dp0제거하기.bat" copy /y "%~dp0제거하기.bat" "%INSTALLDIR%\제거하기.bat" >nul
if exist "%~dp0uninstall.bat" copy /y "%~dp0uninstall.bat" "%INSTALLDIR%\제거하기.bat" >nul

echo  [3/5] 바로가기 만들기...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; foreach ($dir in @([Environment]::GetFolderPath('Desktop'), $env:APPDATA + '\Microsoft\Windows\Start Menu\Programs')) { $lnk = $ws.CreateShortcut((Join-Path $dir 'Easy Saving.lnk')); $lnk.TargetPath = $env:LOCALAPPDATA + '\Programs\EasySaving\EasySaving.exe'; $lnk.WorkingDirectory = $env:LOCALAPPDATA + '\Programs\EasySaving'; $lnk.IconLocation = $env:LOCALAPPDATA + '\Programs\EasySaving\EasySaving.exe'; $lnk.Save() }" >nul 2>&1

echo  [4/5] 프로그램 목록에 등록...
reg add "%REGKEY%" /v DisplayName /t REG_SZ /d "%APPNAME%" /f >nul
reg add "%REGKEY%" /v DisplayVersion /t REG_SZ /d "1.2.0" /f >nul
reg add "%REGKEY%" /v Publisher /t REG_SZ /d "Easy Saving" /f >nul
reg add "%REGKEY%" /v DisplayIcon /t REG_SZ /d "%INSTALLDIR%\%EXENAME%" /f >nul
reg add "%REGKEY%" /v InstallLocation /t REG_SZ /d "%INSTALLDIR%" /f >nul
reg add "%REGKEY%" /v UninstallString /t REG_SZ /d "%INSTALLDIR%\제거하기.bat" /f >nul
reg add "%REGKEY%" /v NoModify /t REG_DWORD /d 1 /f >nul
reg add "%REGKEY%" /v NoRepair /t REG_DWORD /d 1 /f >nul

echo  [5/5] 시작 프로그램 설정...
echo.
set /p AUTO=  윈도우를 켤 때 자동으로 실행할까요? (Y/N) 
if /i "!AUTO!"=="Y" (
    reg add "%RUNKEY%" /v EasySaving /t REG_SZ /d "%INSTALLDIR%\%EXENAME%" /f >nul
    echo   자동 실행을 켰습니다.
) else (
    reg delete "%RUNKEY%" /v EasySaving /f >nul 2>&1
    echo   자동 실행은 끄고 설치합니다.
)

echo.
echo  ============================================================
echo    설치가 끝났습니다!
echo  ============================================================
echo    - 바탕 화면의 "%APPNAME%" 아이콘을 더블클릭하면 실행됩니다.
echo    - 처음 실행하면 사용법 튜토리얼이 자동으로 뜹니다.
echo    - 삭제: 설정 - 앱 - 설치된 앱 에서 "%APPNAME%" 제거
echo.
set /p LAUNCH=  지금 바로 실행할까요? (Y/N) 
if /i "!LAUNCH!"=="Y" start "" "%INSTALLDIR%\%EXENAME%"

echo.
echo   창을 닫아도 됩니다.
timeout /t 5 >nul
endlocal
