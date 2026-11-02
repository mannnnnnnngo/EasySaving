@echo off
setlocal EnableDelayedExpansion
title Easy Saving - 윈도우 실행파일(.exe) 만들기

rem ============================================================
rem  1단계: 개발자가 실행 (파이썬 필요)
rem  결과물: dist\EasySaving.exe  +  배포 폴더 dist\EasySaving_설치
rem  ※ 이 파일은 CP949 로 저장되어 있습니다. chcp 를 넣지 마세요.
rem ============================================================

cd /d "%~dp0\.."
echo.
echo ============================================================
echo   Easy Saving - EasySaving.exe 빌드
echo ============================================================
echo   작업 폴더: %CD%
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [오류] 파이썬을 찾을 수 없습니다.
    echo        https://www.python.org/downloads/ 에서 파이썬 3.9 이상을 설치하고,
    echo        설치 화면에서 "Add Python to PATH" 를 꼭 체크해 주세요.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [1/5] 파이썬 %PYVER% 확인 완료

if not exist ".venv-build" (
    echo [2/5] 빌드용 가상환경 만드는 중...
    python -m venv .venv-build
    if errorlevel 1 (
        echo [오류] 가상환경을 만들지 못했습니다.
        pause
        exit /b 1
    )
) else (
    echo [2/5] 빌드용 가상환경 재사용
)
set PY=.venv-build\Scripts\python.exe

echo [3/5] 라이브러리 설치 중 (pypdf, pymupdf, python-pptx, pyinstaller)...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install --quiet -r requirements-build.txt
if errorlevel 1 (
    echo [오류] 라이브러리 설치에 실패했습니다. 인터넷 연결을 확인해 주세요.
    pause
    exit /b 1
)

echo [4/5] 아이콘 준비 중...
if not exist "assets\easysaving.ico" (
    "%PY%" tools\make_icon.py
)

echo [5/5] EasySaving.exe 만드는 중... (2~5분 걸립니다)
echo.
"%PY%" -m PyInstaller --clean --noconfirm build\EasySaving.spec
if errorlevel 1 (
    echo.
    echo [오류] 빌드에 실패했습니다. 위 메시지를 확인해 주세요.
    pause
    exit /b 1
)

if not exist "dist\EasySaving.exe" (
    echo [오류] dist\EasySaving.exe 가 만들어지지 않았습니다.
    pause
    exit /b 1
)

rem 코드 서명 (선택). 인증서가 있으면 SmartScreen / Defender 경고가 사라진다.
rem   예) set SIGN_ARGS=/fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a
rem       (Azure Trusted Signing 이면 /dlib 와 /dmdf 옵션을 넣는다 - README 참고)
if defined SIGN_ARGS (
    echo [서명] EasySaving.exe 코드 서명 중...
    signtool sign %SIGN_ARGS% "dist\EasySaving.exe"
    if errorlevel 1 (
        echo [경고] 서명에 실패했습니다. 서명 없이 계속합니다.
    )
)

set PKG=dist\EasySaving_설치
if exist "%PKG%" rmdir /s /q "%PKG%"
mkdir "%PKG%"
copy /y "dist\EasySaving.exe" "%PKG%\EasySaving.exe" >nul
copy /y "build\install.bat" "%PKG%\설치하기.bat" >nul
copy /y "build\uninstall.bat" "%PKG%\제거하기.bat" >nul
if exist "assets\easysaving.ico" copy /y "assets\easysaving.ico" "%PKG%\easysaving.ico" >nul
if exist "build\사용법.txt" copy /y "build\사용법.txt" "%PKG%\사용법.txt" >nul
if exist "build\설치하기_파이썬방식.bat" copy /y "build\설치하기_파이썬방식.bat" "%PKG%\설치하기_파이썬방식.bat" >nul

echo.
echo ============================================================
echo   완료!
echo ============================================================
echo   실행 파일 : %CD%\dist\EasySaving.exe
echo   배포 폴더 : %CD%\%PKG%
echo.
echo   이 폴더(EasySaving_설치)를 통째로 압축해서 나눠 주면,
echo   받는 사람은 "설치하기.bat" 만 더블클릭하면 됩니다.
echo   (파이썬을 따로 깔 필요 없습니다)
echo ============================================================
echo.
pause
endlocal
