#define MyAppName "Sunday Service System"
#define MyAppVersion "3.1.4"
#define MyAppPublisher "Sunday Service System"
#define MyAppExeName "SundayServiceSystem.exe"
#define MySettingsExeName "SundayServiceSystemSettings.exe"
#define MyUpdaterExeName "SundayServiceSystemUpdater.exe"

[Setup]
AppId={{67C315A9-9EA1-4EBA-9CB1-A14F2769C319}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Sunday Service System
DefaultGroupName=Sunday Service System
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer-output
OutputBaseFilename=SundayServiceSystem-Setup-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
RestartApplications=no
UninstallDisplayIcon={app}\SundayServiceSystem\{#MyAppExeName}
VersionInfoVersion=3.1.4.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription=Sunday Service System Installer
VersionInfoCompany={#MyAppPublisher}

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Dirs]
; Existing/current SSS integrations still use this compatibility runtime root.
; The installer creates it but never deletes the folder or user data.
Name: "C:\Church\SermonAI"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{commonappdata}\Sunday Service System"; Permissions: users-modify; Flags: uninsneveruninstall

[Files]
Source: "..\dist\SundayServiceSystem\*"; DestDir: "{app}\SundayServiceSystem"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\SundayServiceSystemSettings\*"; DestDir: "{app}\SundayServiceSystemSettings"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\SundayServiceSystemUpdater\*"; DestDir: "{app}\SundayServiceSystemUpdater"; Flags: ignoreversion recursesubdirs createallsubdirs

; Compatibility helper scripts are staged from an explicit allow-list during
; the Windows build. They never include .env, profile JSON, OAuth/token files,
; sunday_config.json, ptz_camera_config.json, or sermon_plan.json.
;
; onlyifdoesntexist is deliberate for the v2.8 foundation: the installer will
; not overwrite a current church's proven compatibility helper scripts.
Source: "..\installer-payload\RuntimeSupport\*"; DestDir: "C:\Church\SermonAI"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist

[Icons]
Name: "{group}\Sunday Service System"; Filename: "{app}\SundayServiceSystem\{#MyAppExeName}"; WorkingDir: "C:\Church\SermonAI"
Name: "{group}\SSS Setup && Settings"; Filename: "{app}\SundayServiceSystemSettings\{#MySettingsExeName}"; WorkingDir: "C:\Church\SermonAI"
Name: "{group}\SSS Update Manager"; Filename: "{app}\SundayServiceSystemSettings\{#MySettingsExeName}"; Parameters: "--updates"; WorkingDir: "C:\Church\SermonAI"
Name: "{group}\Uninstall Sunday Service System"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Sunday Service System"; Filename: "{app}\SundayServiceSystem\{#MyAppExeName}"; WorkingDir: "C:\Church\SermonAI"; Tasks: desktopicon

[Run]
Filename: "{app}\SundayServiceSystem\{#MyAppExeName}"; Description: "Launch Sunday Service System"; WorkingDir: "C:\Church\SermonAI"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Intentionally DO NOT delete C:\Church\SermonAI or ProgramData profiles.
; Only compiled application files inside {app} are removed by the uninstaller.
