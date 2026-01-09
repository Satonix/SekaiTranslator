[Setup]
AppId={{SekaiTranslator}}
AppName=SekaiTranslator
AppVersion=0.6.2-alpha
AppVerName=SekaiTranslator 0.6.2-alpha
VersionInfoVersion=0.6.2.0

DefaultDirName={localappdata}\Programs\SekaiTranslator
DefaultGroupName=SekaiTranslator

PrivilegesRequired=lowest
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=yes

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












