; ============================================================
; VCG Deinterlacer - Inno Setup Installer Script
; ============================================================
;
; Beta-01
; Automatically downloads and installs FFmpeg and VapourSynth
; (plus required VS plugins) if not already present.
;
; PREREQUISITES:
;   1. Run build_vcg_deinterlacer.bat first to produce:
;        dist\VCG_Deinterlacer.exe
;   2. Inno Setup 6.x installed:
;        https://jrsoftware.org/isinfo.php
;
; To build:  Open this file in Inno Setup -> Build -> Compile
;
; ============================================================

#define MyAppName        "VCG Deinterlacer"
#define MyAppVersion     "Beta-01"
#define MyAppVersionFull "Beta-01"
#define MyAppPublisher   "VideoCaptureGuide"
#define MyAppURL         "https://www.youtube.com/@VideoCaptureGuide"
#define MyAppExeName     "VCG_Deinterlacer.exe"
#define MyAppCopyright   "Copyright (c) 2026 VideoCaptureGuide"

[Setup]
; Unique application ID -- do NOT change once released
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersionFull}
AppVerName={#MyAppName} {#MyAppVersionFull}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppCopyright}

; Install to user AppData -- no admin rights needed, no Program Files issues
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; Output
OutputDir=installer_output
OutputBaseFilename=VCG_Deinterlacer_{#MyAppVersion}_Setup
SetupIconFile=vcg_icon.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Appearance
WizardStyle=modern
WizardResizable=no

; Per-user install -- no admin required
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Misc
Uninstallable=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main executable
Source: "dist\VCG_Deinterlacer.exe"; DestDir: "{app}"; Flags: ignoreversion

; App assets
Source: "logo.png";     DestDir: "{app}"; Flags: ignoreversion
Source: "vcg_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "README.md";   DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}";                       Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// ============================================================
// URLs for dependency downloads
// ============================================================
const
  FFMPEG_URL = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';
  VS_R73_URL = 'https://github.com/vapoursynth/vapoursynth/releases/download/R73/VapourSynth64-R73.exe';

// ============================================================
// Global variables (must be declared before any functions)
// ============================================================
var
  ProgressPage: TOutputProgressWizardPage;

// ============================================================
// Detection helpers
// ============================================================

function FFmpegInstalled: Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{app}\ffmpeg\bin\ffmpeg.exe')) or
    FileExists('C:\ffmpeg\bin\ffmpeg.exe') or
    FileExists(ExpandConstant('{localappdata}\Programs\ffmpeg\bin\ffmpeg.exe')) or
    FileExists(ExpandConstant('{pf}\ffmpeg\bin\ffmpeg.exe')) or
    FileExists(ExpandConstant('{pf64}\ffmpeg\bin\ffmpeg.exe'));
end;

function VapourSynthInstalled: Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\VapourSynth\core\vspipe.exe')) or
    FileExists('C:\Program Files\VapourSynth\core\vspipe.exe') or
    FileExists(ExpandConstant('{pf}\VapourSynth\core\vspipe.exe')) or
    FileExists(ExpandConstant('{pf64}\VapourSynth\core\vspipe.exe'));
end;

function FindVspipe: String;
var
  Candidates: TArrayOfString;
  i: Integer;
begin
  Result := '';
  SetArrayLength(Candidates, 4);
  Candidates[0] := ExpandConstant('{localappdata}\Programs\VapourSynth\core\vspipe.exe');
  Candidates[1] := 'C:\Program Files\VapourSynth\core\vspipe.exe';
  Candidates[2] := ExpandConstant('{pf}\VapourSynth\core\vspipe.exe');
  Candidates[3] := ExpandConstant('{pf64}\VapourSynth\core\vspipe.exe');
  for i := 0 to 3 do
    if FileExists(Candidates[i]) then
    begin
      Result := Candidates[i];
      Exit;
    end;
end;

// ============================================================
// Escape backslashes for JSON (replace \ with \\)
// ============================================================

function EscapeBackslashes(S: String): String;
var
  i:      Integer;
  Result2: String;
begin
  Result2 := '';
  for i := 1 to Length(S) do
  begin
    if S[i] = '\' then
      Result2 := Result2 + '\\'
    else
      Result2 := Result2 + S[i];
  end;
  Result := Result2;
end;

// ============================================================
// Write paths.json so the app finds FFmpeg and VapourSynth
// ============================================================

procedure WritePaths;
var
  FFmpegBin:  String;
  VspipePath: String;
  Json:       String;
  HasFFmpeg:  Boolean;
  HasVS:      Boolean;
begin
  // Prefer FFmpeg bundled inside {app}\ffmpeg\bin\
  FFmpegBin := ExpandConstant('{app}\ffmpeg\bin\');
  HasFFmpeg := FileExists(FFmpegBin + 'ffmpeg.exe');
  if not HasFFmpeg then
  begin
    if FileExists('C:\ffmpeg\bin\ffmpeg.exe') then
    begin
      FFmpegBin := 'C:\ffmpeg\bin\';
      HasFFmpeg := True;
    end;
  end;

  VspipePath := FindVspipe;
  HasVS := VspipePath <> '';

  if not HasFFmpeg and not HasVS then
    Exit;

  Json := '{' + #13#10;

  if HasFFmpeg then
  begin
    Json := Json + '  "ffmpeg_path": "' +
            EscapeBackslashes(FFmpegBin + 'ffmpeg.exe') + '",' + #13#10;
    Json := Json + '  "ffprobe_path": "' +
            EscapeBackslashes(FFmpegBin + 'ffprobe.exe') + '"';
    if HasVS then
      Json := Json + ','
    else
      Json := Json + '';
    Json := Json + #13#10;
  end;

  if HasVS then
    Json := Json + '  "vspipe_path": "' +
            EscapeBackslashes(VspipePath) + '"' + #13#10;

  Json := Json + '}' + #13#10;
  SaveStringToFile(ExpandConstant('{app}\paths.json'), Json, False);
end;

// ============================================================
// Download progress callback -- required by Inno Setup 6.x
// ============================================================

function OnDownloadProgress(const Url, FileName: String;
                            const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax > 0 then
    ProgressPage.SetProgress(Progress, ProgressMax)
  else
    ProgressPage.SetProgress(0, 100);
  Result := True;
end;

// ============================================================
// Install FFmpeg -- download zip, extract, copy binaries
// ============================================================

procedure InstallFFmpeg;
var
  ResultCode: Integer;
  FFmpegDest: String;
  PSExtract:  String;
  PSCopy:     String;
begin
  FFmpegDest := ExpandConstant('{app}\ffmpeg\bin');

  ProgressPage.SetText('Installing FFmpeg',
    'Downloading FFmpeg (this may take a minute)...');
  ProgressPage.SetProgress(0, 100);
  ProgressPage.Show;

  try
    try
      DownloadTemporaryFile(FFMPEG_URL, 'ffmpeg.zip', '', @OnDownloadProgress);
    except
      MsgBox(
        'Could not download FFmpeg automatically.' + #13#10 + #13#10 +
        'You can install it manually:' + #13#10 +
        '1. Go to https://www.gyan.dev/ffmpeg/builds/' + #13#10 +
        '2. Download ffmpeg-release-essentials.zip' + #13#10 +
        '3. Extract to C:\ffmpeg so that C:\ffmpeg\bin\ffmpeg.exe exists',
        mbInformation, MB_OK);
      Exit;
    end;

    ProgressPage.SetText('Installing FFmpeg', 'Extracting FFmpeg...');
    ProgressPage.SetProgress(50, 100);

    // Extract zip via PowerShell
    PSExtract :=
      '-NoProfile -Command "Expand-Archive -LiteralPath ''' +
      ExpandConstant('{tmp}\ffmpeg.zip') + ''' ' +
      '-DestinationPath ''' + ExpandConstant('{tmp}\ffmpeg_extracted') + ''' -Force"';

    Exec('powershell.exe', PSExtract, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    ProgressPage.SetProgress(75, 100);
    ProgressPage.SetText('Installing FFmpeg', 'Copying FFmpeg files...');

    // Copy just ffmpeg.exe and ffprobe.exe from the versioned subfolder
    PSCopy :=
      '-NoProfile -Command "' +
      '$src = (Get-ChildItem ''' + ExpandConstant('{tmp}\ffmpeg_extracted') +
      ''' -Directory | Select-Object -First 1).FullName + ''\bin''; ' +
      'New-Item -ItemType Directory -Force -Path ''' + FFmpegDest + ''' | Out-Null; ' +
      'Copy-Item (Join-Path $src ''ffmpeg.exe'')  ''' + FFmpegDest + ''' -Force; ' +
      'Copy-Item (Join-Path $src ''ffprobe.exe'') ''' + FFmpegDest + ''' -Force"';

    Exec('powershell.exe', PSCopy, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    ProgressPage.SetProgress(100, 100);

  finally
    ProgressPage.Hide;
  end;
end;

// ============================================================
// Install VapourSynth + plugins
// ============================================================

procedure InstallVapourSynth;
var
  ResultCode: Integer;
  PSPlugins:  String;
begin
  ProgressPage.SetText('Installing VapourSynth',
    'Downloading VapourSynth R73 (this may take a minute)...');
  ProgressPage.SetProgress(0, 100);
  ProgressPage.Show;

  try
    try
      DownloadTemporaryFile(VS_R73_URL, 'VapourSynth_Setup.exe', '', @OnDownloadProgress);
    except
      MsgBox(
        'Could not download VapourSynth automatically.' + #13#10 + #13#10 +
        'You can install it manually:' + #13#10 +
        '1. Go to https://github.com/vapoursynth/vapoursynth/releases' + #13#10 +
        '2. Download VapourSynth64-R73.exe and run it' + #13#10 +
        '3. Then open a command prompt and run:' + #13#10 +
        '   pip install vsrepo' + #13#10 +
        '   vsrepo install havsfunc lsmas mvtools fmtconv',
        mbInformation, MB_OK);
      Exit;
    end;

    ProgressPage.SetText('Installing VapourSynth',
      'Running VapourSynth installer (please wait)...');
    ProgressPage.SetProgress(35, 100);

    // Run VapourSynth installer silently
    Exec(ExpandConstant('{tmp}\VapourSynth_Setup.exe'),
         '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    ProgressPage.SetText('Installing VapourSynth plugins',
      'Installing vsrepo and plugins (havsfunc, lsmas, mvtools, fmtconv)...');
    ProgressPage.SetProgress(65, 100);

    // Install vsrepo via pip (required since R74 packaging changes; works on R73 too)
    Exec('powershell.exe',
         '-NoProfile -Command "pip install vsrepo --quiet"',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    ProgressPage.SetProgress(80, 100);

    // Install required plugins via vsrepo
    PSPlugins :=
      '-NoProfile -Command "vsrepo install havsfunc lsmas mvtools fmtconv"';

    Exec('powershell.exe', PSPlugins, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    ProgressPage.SetProgress(100, 100);

  finally
    ProgressPage.Hide;
  end;
end;

// ============================================================
// Wizard init
// ============================================================

procedure InitializeWizard;
begin
  ProgressPage := CreateOutputProgressPage(
    'Setting Up Dependencies',
    'Please wait while VCG Deinterlacer sets up required components...'
  );
end;

// ============================================================
// After files are installed -- run dependency setup
// ============================================================

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not FFmpegInstalled then
      InstallFFmpeg;

    if not VapourSynthInstalled then
      InstallVapourSynth;

    // Always write paths.json after installs complete
    WritePaths;
  end;
end;
