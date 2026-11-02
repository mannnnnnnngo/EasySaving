@echo off
setlocal
title Easy Saving - 설치 마법사(Setup.exe) 만들기

cd /d "%~dp0\.."

echo.
echo ============================================================
echo   Easy Saving - EasySaving_Setup.exe 만들기
echo ============================================================
echo.

if not exist "dist\EasySaving.exe" (
    echo [안내] dist\EasySaving.exe 가 없습니다. 먼저 빌드를 실행합니다.
    echo.
    call build\build_windows.bat
    if not exist "dist\EasySaving.exe" exit /b 1
)

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
    echo [오류] Inno Setup 을 찾을 수 없습니다.
    echo        https://jrsoftware.org/isdl.php 에서 Inno Setup 6 을 설치한 뒤 다시 실행해 주세요.
    echo.
    echo        설치 마법사 없이 그냥 나눠 주려면
    echo        dist\EasySaving_설치 폴더를 압축해서 전달하면 됩니다.
    echo.
    pause
    exit /b 1
)

echo Inno Setup 발견: %ISCC%
echo 설치 파일 만드는 중...
echo.
"%ISCC%" "build\installer.iss"
if errorlevel 1 (
    echo.
    echo [오류] 설치 파일을 만들지 못했습니다.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   완료!  dist\EasySaving_Setup.exe
echo   이 파일 하나만 전달하면 누구나 더블클릭으로 설치할 수 있습니다.
echo ============================================================
echo.
pause
endlocal
