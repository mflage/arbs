#!/bin/bash

# Start the run once job.
echo "Docker container has been started"

#cp /app/etc/default_configuration.cfg /data/nyheter/

# Setup a cron schedule
echo "54-58 5-17 * * * cd /app ; ./grab_news.py /data/news.cfg >> /var/log/cron.log 2>&1
# This extra line makes it a valid cron" > scheduler.txt

crontab scheduler.txt
cron -f
