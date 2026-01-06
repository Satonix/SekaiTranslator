[Setup]
AppId={{SekaiTranslator}}
AppName=SekaiTranslator
AppVersion=0.3.2-alpha
AppVerName=SekaiTranslator 0.3.2-alpha
VersionInfoVersion=0.3.2.0

DefaultDirName={localappdata}\Programs\SekaiTranslator
DefaultGroupName=SekaiTranslator
UninstallDisplayIcon={app}\SekaiTranslator.exe
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UsePreviousAppDir=yes

OutputDir=installer
OutputBaseFilename=SekaiTranslator_Setup


[Files]
Source: "dist\SekaiTranslator\_internal\*"; DestDir: "{app}\_internal"; Flags: recursesubdirs ignoreversion
Source: "dist\SekaiTranslator\SekaiTranslator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\SekaiTranslator\updater.exe"; DestDir: "{app}"; Flags: ignoreversion


[Icons]
Name: "{group}\SekaiTranslator"; Filename: "{app}\SekaiTranslator.exe"
Name: "{userdesktop}\SekaiTranslator"; Filename: "{app}\SekaiTranslator.exe"

[Run]
Filename: "{app}\SekaiTranslator.exe"; Description: "Iniciar SekaiTranslator"; Flags: nowait postinstall skipifsilent





