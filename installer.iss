[Setup]
AppName=SekaiTranslator
AppVersion=0.3.1-alpha
DefaultDirName={localappdata}\Programs\SekaiTranslator
DefaultGroupName=SekaiTranslator
UninstallDisplayIcon={app}\SekaiTranslator.exe
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=SekaiTranslator_Setup

[Files]
Source: "dist\SekaiTranslator\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\SekaiTranslator"; Filename: "{app}\SekaiTranslator.exe"
Name: "{userdesktop}\SekaiTranslator"; Filename: "{app}\SekaiTranslator.exe"

[Run]
Filename: "{app}\SekaiTranslator.exe"; Description: "Iniciar SekaiTranslator"; Flags: nowait postinstall skipifsilent

