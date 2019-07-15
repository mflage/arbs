#!/usr/bin/env python2

import sys
import os
import yaml
import datetime
import time
import math

from mpd import MPDClient

"""this script will run every minute by cron and check if there are
any reruns that should happen within the next minute"""

RERUNS = "/tmp/reruns.txt"

RERUN = "R %a %H %M"
ONCE = "O %d %m %H %M"
STREAM = "S %d %m %H %M"

def fader(level, fadetime, client):
    between = 0.10

    currentvol = int(client.status()["volume"])
    
    maxvol = max(level, currentvol)
    minvol = min(level, currentvol)
    
    diff = maxvol - minvol
    
    if fadetime == 0:
        client.setvol(level)
    else:
        starttime = time.time()
        while 1:
            t = time.time() - starttime
            if t > fadetime or t < 0:
                break
            ratio = float(t)/fadetime
            # fade down
            if level < currentvol:
                try:
                    sqrt = math.sqrt(1 - ratio)
                    new_level = int(diff * sqrt + minvol)
                except math.ValueError:
                    error("Shit hit the fan - fading and returning", False)
                    break
            # fade up
            else:
                try:
                    sqrt = math.sqrt(ratio)
                    new_level = int(diff * sqrt + minvol)
                except math.ValueError:
                    error("Shit hit the fan - fading and returning", False)
                    break
            if new_level <= 100 or new_level > 0:
                client.setvol(new_level)
                time.sleep(between)
        client.setvol(level)
                                                                                                                                                                        

def check_reruns(filename, timestamp):

    to_be_played = []
    
    with open(filename, 'r') as fp:
        for line in fp:
            line = line.strip()
            if line[0] == '#':
                continue
            (when, what) = line.split(" - ", 1)

            if timestamp.strftime(ONCE) == when:
                to_be_played.append(what)
            elif timestamp.strftime(RERUN) == when:
                to_be_played.append(what)

    return to_be_played

def main(arg):

    while 1:
        
        time.sleep(1)

        now = datetime.datetime.now()
        then = now + datetime.timedelta(minutes=1)
        then = then.replace(second=0).replace(microsecond=0)

        next_minute = check_reruns(
            RERUNS,
            then
        )
        
        if not next_minute:
            continue
        
        client = MPDClient()
        client.timeout = 60
        client.idletimeout = None
        client.connect("localhost", 6600)
        
        status = client.status()
        
        playback = status["time"]
        
        (played, total) = status["time"].split(":")
        
        left = int(total) - int(played)

        left_of_minute = (then - now).total_seconds()

        if left > left_of_minute + 1:
            now = datetime.datetime.now()
            then = now.replace(second=55).replace(microsecond=0)
            sleep_time = (then - now).total_seconds()
            time.sleep(sleep_time)
            fader(0, 4.9, client)
            for what in next_minute:
                client.addid(what, 1)
            client.pause()
            fader(100, 0, client)
            client.next()
            client.play()
            client.close()
        else:
            print "we do the manual playlist advance trick"
            # set to manual playlist advance
            client.single(1)
            for what in next_minute:
                client.addid(what, 1)
            now = datetime.datetime.now()
            print now
            time.sleep((then - now).total_seconds())
            print datetime.datetime.now()
            client.single(0)
            client.play()


if __name__ == '__main__':
    main(sys.argv[1:])
