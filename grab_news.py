#!/usr/bin/env python3

import os
import re
import requests
import sys
import yamale

REGEX = r'^\<url\>(?P<url>.*)\<\/url\>$'
CONFIGURATION_SCHEMA = "news_schema.yaml"


def main(arg):

    # load schema and configuration
    try:
        schema = yamale.make_schema(CONFIGURATION_SCHEMA)
        data = yamale.make_data(arg[0])
    except FileNotFoundError as e:
        sys.exit("File not found: {}".format(e.filename))
    except IndexError:
        sys.exit("Please provide a configuration as the first parameter.")

    # validate and load the configuration file
    try:
        cfg = yamale.validate(schema, data, True)[0][0]
    except ValueError as e:
        print("Not validated correctly.")
        sys.exit(e)

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

                with open(local_path, 'wb') as f:
                    for chunk in mp3_f:
                        f.write(chunk)

                if os.path.isfile(cfg["news"]["newsfile"]):
                    os.remove(cfg["news"]["newsfile"])

                os.link(
                    local_path,
                    cfg["news"]["newsfile"]
                )


if __name__ == '__main__':
    main(sys.argv[1:])
