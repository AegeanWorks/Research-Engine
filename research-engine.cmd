@echo off
setlocal
set "ROOT=%~dp0"
set "BIN=%ROOT%rust\target\x86_64-pc-windows-gnu\release\research-engine.exe"
if not exist "%BIN%" set "BIN=%ROOT%rust\target\release\research-engine.exe"
if not exist "%BIN%" (
  pushd "%ROOT%rust" >nul
  cargo build --release || (popd >nul & exit /b 1)
  popd >nul
  set "BIN=%ROOT%rust\target\x86_64-pc-windows-gnu\release\research-engine.exe"
  if not exist "%BIN%" set "BIN=%ROOT%rust\target\release\research-engine.exe"
)
"%BIN%" %*
exit /b %ERRORLEVEL%
