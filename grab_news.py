#!/usr/bin/env python3

import os
import pydub
import re
import requests
import sys
import yaml

REGEX = r'^\<url\>(?P<url>.*)\<\/url\>$'


def main(arg):

    # first argument is the configuration file
    with open(arg[0], 'r') as configfile:
        try:
            cfg = yaml.load(configfile)
        except yaml.scanner.ScannerError as e:
            sys.exit("Error in configuration file: %s" % e)

    r = requests.get(
        cfg["news"]["xml_url"],
        auth=(
            cfg["news"]["username"],
            cfg["news"]["password"]
        )
    )

    if r.status_code == 200:
        for line in r.text.split("\n"):
            line = line.strip()
            match = re.search(REGEX, line)

            if not match:
                continue

            url = match.group("url")

            filename = os.path.basename(url)

            local_path = os.path.join(cfg["news"]["folder"], filename)

            if os.path.isfile(local_path):
                continue

            mp3_f = requests.get(
                url,
                auth=(cfg["news"]["username"], cfg["news"]["password"]),
                stream=True
            )

            if mp3_f.status_code == 200:

                intro = pydub.AudioSegment.from_file(cfg["news"]["intro"])

                with open(local_path, 'wb') as f:
                    for chunk in mp3_f:
                        f.write(chunk)

                news = pydub.AudioSegment.from_file(local_path)

                if os.path.isfile(cfg["news"]["newsfile"]):
                    os.remove(cfg["news"]["newsfile"])

                (intro + news).export(
                    cfg["news"]["newsfile"],
                    format="mp3",
                    bitrate="256k"
                )


if __name__ == '__main__':
    main(sys.argv[1:])
