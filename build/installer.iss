; Easy Saving - Inno Setup 스크립트
; 결과물: dist\EasySaving_Setup.exe  (더블클릭 → 설치 마법사)
;
; 사용법
;   1) https://jrsoftware.org/isdl.php 에서 Inno Setup 설치
;   2) build\build_windows.bat 로 dist\EasySaving.exe 를 먼저 만든다
;   3) build\build_installer.bat 실행 (또는 이 파일을 Inno Setup 으로 열고 F9)

#define AppName "Easy Saving"
#define AppVersion "1.1.0"
#define AppExe "EasySaving.exe"

[Setup]
AppId={{7C1B4E2A-5D3F-4A6B-9E88-EASYSAVING001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Easy Saving
DefaultDirName={localappdata}\Programs\EasySaving
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
OutputDir=..\dist
OutputBaseFilename=EasySaving_Setup
SetupIconFile=..\assets\easysaving.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 관리자 권한 없이 내 계정에만 설치 (회사 PC 에서도 설치 가능)
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면에 바로가기 만들기"; GroupDescription: "추가 작업:"; Flags: checkedonce
Name: "startupicon"; Description: "윈도우를 켤 때 자동으로 실행"; GroupDescription: "추가 작업:"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\easysaving.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "지금 바로 실행하기"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\EasySaving"
