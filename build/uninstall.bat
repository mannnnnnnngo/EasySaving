@echo off
setlocal EnableDelayedExpansion
title Easy Saving 제거

set APPNAME=Easy Saving
set EXENAME=EasySaving.exe
set INSTALLDIR=%LOCALAPPDATA%\Programs\EasySaving
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
set REGKEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\EasySaving
set RUNKEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run
set CONFIGDIR=%APPDATA%\EasySaving

cls
echo.
echo  ============================================================
echo    %APPNAME% 제거
echo  ============================================================
echo.
set /p GO=  정말 제거할까요? (Y/N) 
if /i not "!GO!"=="Y" exit /b 0

echo.
echo  [1/4] 실행 중이면 종료...
taskkill /f /im %EXENAME% >nul 2>&1

echo  [2/4] 바로가기 삭제...
del /f /q "%USERPROFILE%\Desktop\%APPNAME%.lnk" >nul 2>&1
del /f /q "%STARTMENU%\%APPNAME%.lnk" >nul 2>&1
powershell -NoProfile -Command "Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Easy Saving.lnk') -ErrorAction SilentlyContinue" >nul 2>&1

echo  [3/4] 등록 정보 삭제...
reg delete "%REGKEY%" /f >nul 2>&1
reg delete "%RUNKEY%" /v EasySaving /f >nul 2>&1

echo  [4/4] 설정 파일 처리...
set /p KEEP=  버튼 위치/색 같은 설정도 지울까요? (Y/N) 
if /i "!KEEP!"=="Y" rmdir /s /q "%CONFIGDIR%" >nul 2>&1

echo.
echo   제거가 끝났습니다. 저장해 둔 PDF 파일은 그대로 남아 있습니다.
echo.
timeout /t 4 >nul

start "" /min cmd /c "timeout /t 2 >nul & rmdir /s /q ""%INSTALLDIR%"""
endlocal
