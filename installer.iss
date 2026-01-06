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
Source: "dist\SekaiTranslator\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\SekaiTranslator"; Filename: "{app}\SekaiTranslator.exe"
Name: "{userdesktop}\SekaiTranslator"; Filename: "{app}\SekaiTranslator.exe"

[Run]
Filename: "{app}\SekaiTranslator.exe"; Description: "Iniciar SekaiTranslator"; Flags: nowait postinstall skipifsilent




