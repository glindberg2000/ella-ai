#!/bin/bash

# Create a directory to store the logs
LOG_DIR=~/ubuntu_logs
mkdir -p $LOG_DIR

# Copy system logs
cp /var/log/syslog $LOG_DIR/syslog
cp /var/log/auth.log $LOG_DIR/auth.log
cp /var/log/kern.log $LOG_DIR/kern.log
cp /var/log/dmesg $LOG_DIR/dmesg.log
cp /var/log/syslog.1 $LOG_DIR/syslog.1
cp /var/log/auth.log.1 $LOG_DIR/auth.log.1
cp /var/log/kern.log.1 $LOG_DIR/kern.log.1

# Include any additional logs you find relevant

# Create a zip file of the logs
ZIP_FILE=~/ubuntu_logs.zip
zip -r $ZIP_FILE $LOG_DIR

# Remove the temporary logs directory
rm -rf $LOG_DIR

echo "Logs have been collected and compressed into the file: $ZIP_FILE"