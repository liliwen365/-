; 本地自动化平台 Inno Setup 安装脚本
; 用法: ISCC setup.iss
; 前置: python build.py 已产出 dist/LocalAgent/

#define AppName "LocalAgent"
#define AppDisplayName "本地自动化平台"
#define AppVersion "0.1.0"
#define AppPublisher "Liliwen365"
#define AppExeName "LocalAgent.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppDisplayName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
SolidCompression=yes
Compression=lzma2/ultra64
OutputDir=dist
OutputBaseFilename=LocalAgent-Setup
PrivilegesRequired=lowest
WizardStyle=modern

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: checkedonce
Name: "startupicon"; Description: "开机自动启动"; GroupDescription: "附加选项:"; Flags: unchecked

[Files]
Source: "dist\LocalAgent\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\LocalAgent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppDisplayName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppDisplayName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "立即启动{#AppDisplayName}"; Flags: nowait postinstall skipifsilent
