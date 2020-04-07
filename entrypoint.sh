#!/bin/bash

CONFIGURATION_FILE=/data/news.cfg

# Start the run once job.
echo "Grab news container has been started"

if [ ! -f "$CONFIGURATION_FILE" ]; then
    echo "Copying the default configuration to /data"
    cp /app/default_configuration.cfg /data/
fi

# Setup a cron schedule
# it's up to the script itself to decide if it should actually connect and check for new files
echo "* * * * * cd /app ; /usr/local/bin/python3 ./grab_news.py /data/news.cfg >> /var/log/cron.log 2>&1
# This extra line makes it a valid cron" > scheduler.txt

crontab scheduler.txt
cron -f
