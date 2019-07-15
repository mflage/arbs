#!/usr/bin/env python2

# this script will hook up to mpd and check if it's possible to play teasers

import yaml
import sys
import os
import random

from mpd import MPDClient

# this is the list of teasers available

def main(arg):

    client = MPDClient()
    client.timeout = 60
    client.idletimeout = None
    
    client.connect("localhost", 6600)

    played = 0

    prevsong = None

    teasers = []
    
    next_number = random.randint(3, 5)
    
    while 1:
        subsystem = client.idle()
        if "player" in subsystem:

            if len(teasers) == 0:
                teasers = client.search("Filename", "teasers")
                random.shuffle(teasers)

            status = client.status()
            if status["state"] != "play":
                continue
                
            currentsong = client.currentsong()

            if prevsong:
                if currentsong["file"] == prevsong["file"]:
                    continue

            if not "teasers" in currentsong["file"]:
                played += 1

            if played >= next_number:
                teaser = teasers.pop(0)
                client.addid(teaser["file"], 1)
                next_number = random.randint(3, 5)
                played = 0
            
            prevsong = currentsong

if __name__ == '__main__':
    main(sys.argv[1:])
