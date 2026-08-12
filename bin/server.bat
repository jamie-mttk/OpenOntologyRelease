@echo off
if "%OS%" == "Windows_NT" setlocal EnableDelayedExpansion

cd /d "%~dp0"
set SERVER_HOME=..
rem set JAVA_HOME=..\runtime\jre
rem set JAVA_HOME=D:\java\jdk-25
rem Check Java Home
if exist "%JAVA_HOME%\bin\java.exe" goto okJavaHome
echo The JAVA_HOME environment variable is not defined correctly
echo This environment variable is needed to run this program
goto end
:okJavaHome

rem Check Java version (requires Java 25)
set JAVA_MAJOR=
for /f "tokens=3" %%i in ('"%JAVA_HOME%\bin\java.exe" -version 2^>^&1 ^| findstr /i version') do (
  set JAVA_VER=%%i
  goto parseJavaVer
)
echo Failed to detect Java version
goto end
:parseJavaVer
set JAVA_VER=!JAVA_VER:"=!
for /f "delims=." %%m in ("!JAVA_VER!") do set JAVA_MAJOR=%%m
if not defined JAVA_MAJOR (
  echo Failed to detect Java version
  goto end
)
if !JAVA_MAJOR! LSS 25 (
  echo Java 25 is required, but found Java !JAVA_MAJOR!
  goto end
)

rem Check SERVER HOME
if exist "%SERVER_HOME%\bin\server.bat" goto okServerHome
echo The SERVER_HOME environment variable is not defined correctly
echo This environment variable is needed to run this program
goto end
:okServerHome

rem ---------------------------
rem build class path
rem ---------------------------
set CLASSPATH=%SERVER_HOME%\lib\sys\openont-bootstrap.jar
rem ----- Execute The Requested Command ---------------------------------------

echo Using SERVER_HOME:   %SERVER_HOME%
echo Using JAVA_HOME:  %JAVA_HOME%
%JAVA_HOME%\bin\java -version

set _EXECJAVA=%JAVA_HOME%\bin\java
set MAINCLASS=com.mttk.openOnt.bootstrap.Bootstrap
rem if you want to set java vm machine, here is the place
rem set JAVA_OPTS="-Xms1G -Xmx10G -Xss1M -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=512M -XX:MaxDirectMemorySize=2G"
rem If you want to dump memory info while OOM happen, please uncomment here
rem set DUMP_ON_OOM=-XX:+HeapDumpOnOutOfMemoryError
rem  -Djavax.net.debug=all Add to java parameter to debug network issues
rem -Dlog4j2.formatMsgNoLookups=true is to fix Log4j bug
set JAVA_OPTS=-XX:NativeMemoryTracking=off
%_EXECJAVA% %JAVA_OPTS% %DUMP_ON_OOM% -classpath "%CLASSPATH%" -Dserver.home="%SERVER_HOME%" -Djava.library.path="%SERVER_HOME%\lib_user\native" -Djava.net.preferIPv4Stack=true -Dlog4j2.formatMsgNoLookups=true %MAINCLASS% %1 %2 %3 %4 %5 %6

goto end

:end
