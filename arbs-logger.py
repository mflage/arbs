#!/usr/bin/env python2

import sys
import os
import yaml

from mpd import MPDClient

client = MPDClient()
client.timeout = 60
client.idletimeout = None

client.connect("localhost", 6600)

while 1:
    subsystem = client.idle()
    if "player" in subsystem:
        currentsong = client.currentsong()

        status = client.status()
        if status["state"] != "play":
            continue

        if "teasers" in currentsong["file"]:
            print currentsong["file"]
            continue
        
        print("{} - {} ({})".format(currentsong["artist"],
                                    currentsong["title"],
                                    currentsong["file"]))
