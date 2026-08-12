#!/bin/sh
cd "$(dirname "$0")"
BIN_PATH=`pwd`
SERVER_HOME=`dirname $BIN_PATH`
touch $SERVER_HOME/data/STOPME
echo "Stop signal is sent!"

