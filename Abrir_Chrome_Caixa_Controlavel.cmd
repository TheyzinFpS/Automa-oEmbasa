@echo off
setlocal

set "CHROME_EXE="

if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
  set "CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
)

if not defined CHROME_EXE if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
  set "CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
)

if not defined CHROME_EXE if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
  set "CHROME_EXE=%LocalAppData%\Google\Chrome\Application\chrome.exe"
)

if not defined CHROME_EXE (
  echo Google Chrome nao foi encontrado neste computador.
  pause
  exit /b 1
)

set "EMBASA_CHROME_PROFILE=%LocalAppData%\EMBASA\ChromeCaixa"
if not exist "%EMBASA_CHROME_PROFILE%" mkdir "%EMBASA_CHROME_PROFILE%"

start "" "%CHROME_EXE%" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%EMBASA_CHROME_PROFILE%" ^
  --no-first-run ^
  --disable-features=Translate ^
  "https://gerenciador.caixa.gov.br/"

endlocal
