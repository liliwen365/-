; 文件整理系统 Inno Setup 安装脚本

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=文件整理系统
AppVersion=1.0.0
AppPublisher=Liliwen365
AppPublisherURL=https://github.com/liliwen365/file-organizer
AppSupportURL=https://github.com/liliwen365/file-organizer
DefaultDirName={autopf}\FileOrganizer
DisableProgramGroupPage=yes
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\FileOrganizer.exe
SolidCompression=yes
Compression=lzma2/ultra64
OutputDir=Output
OutputBaseFilename=FileOrganizer_v1.0.0_Setup
PrivilegesRequired=admin

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "dist\FileOrganizer\FileOrganizer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\FileOrganizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\文件整理系统"; Filename: "{app}\FileOrganizer.exe"
Name: "{autodesktop}\文件整理系统"; Filename: "{app}\FileOrganizer.exe"; AppUserModelID: "com.liliwen365.fileorganizer.pro.v1"; Tasks: desktopicon

[Run]
Filename: "{app}\FileOrganizer.exe"; Description: "{cm:LaunchProgram,文件整理系统}"; Flags: nowait postinstall skipifsilent
