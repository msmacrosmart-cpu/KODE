#!/bin/sh

# Gradle wrapper script
APP_HOME=$(cd "$(dirname "$0")" && pwd)

# Use JAVA_HOME if set, otherwise fall back to system java
if [ -n "$JAVA_HOME" ]; then
    JAVA_EXE="$JAVA_HOME/bin/java"
else
    JAVA_EXE=java
fi

if [ ! -x "$JAVA_EXE" ]; then
    echo "ERROR: Java not found at $JAVA_EXE"
    echo "Please install OpenJDK 17 and set JAVA_HOME, or ensure 'java' is on your PATH."
    exit 1
fi

exec "$JAVA_EXE" -jar "$APP_HOME/gradle/wrapper/gradle-wrapper.jar" "$@"
