@echo off
cd /d "%~dp0."
set SERVER_HOME=..
set SERVER_STOP_FILE=%SERVER_HOME%\data\STOPME
dir >> %SERVER_STOP_FILE%
