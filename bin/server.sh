#!/bin/sh
BIN_PATH=`pwd`

SERVER_HOME=`dirname $BIN_PATH`
JAVA_HOME="$SERVER_HOME/runtime/jre"
# echo "Java home:$JAVA_HOME"
# Check Java Home
if [ ! -r "$JAVA_HOME/bin/java" ]; then
	echo The JAVA_HOME environment variable is not defined correctly
	echo This environment variable is needed to run this program
	exit 1
fi

# Check Java version (requires Java 25)
JAVA_MAJOR=$($JAVA_HOME/bin/java -version 2>&1 | awk -F\" '/version/ {print $2; exit}' | cut -d. -f1)
if [ -z "$JAVA_MAJOR" ] || [ "$JAVA_MAJOR" -lt 25 ] 2>/dev/null; then
	echo "Java 25 is required, but found Java ${JAVA_MAJOR:-unknown}"
	exit 1
fi

# Check SERVER HOME
if [ ! -r "$SERVER_HOME/bin/server.sh" ]; then
	echo The SERVER_HOME environment variable is not defined correctly
	echo This environment variable is needed to run this program
	exit 1
fi

# ---------------------------
# build class path
# ---------------------------
CLASSPATH="$SERVER_HOME/lib/sys/openont-bootstrap.jar"

# ----- Execute The Requested Command ---------------------------------------
echo "Using SERVER_HOME:$SERVER_HOME"
echo "Using JAVA_HOME:$JAVA_HOME"
$JAVA_HOME/bin/java -version

_EXECJAVA="$JAVA_HOME/bin/java"
MAINCLASS="com.mttk.openOnt.bootstrap.Bootstrap"
# if you want to set java vm machine, here is the place
#JAVA_OPTS="-Xms1G -Xmx10G -Xss1M -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=512M -XX:MaxDirectMemorySize=2G"
#If you want to dump memory info while OOM happen, please uncomment here
#DUMP_ON_OOM=-XX:+HeapDumpOnOutOfMemoryError
#-Dlog4j2.formatMsgNoLookups=true is to fix Log4j bug
eval $_EXECJAVA $JAVA_OPTS $DUMP_ON_OOM -classpath \"$CLASSPATH\" -Dserver.home=\"$SERVER_HOME\" -Djava.library.path=\"$SERVER_HOME/lib_user/native\" -Djava.net.preferIPv4Stack=true -Dlog4j2.formatMsgNoLookups=true $MAINCLASS "$@"
