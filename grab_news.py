#!/usr/bin/env python3

import datetime
import os
import requests
import sys
# i hate having to import time as well as datetime
import time
import yamale
import xmltodict

# this needs to be fixed somehow, or maybe even embedded into the script
CONFIGURATION_SCHEMA = "news_schema.yaml"

# the timestamp format used by radionyhetene
TIMESTAMP_FORMAT = r"%Y%m%d%H%M%S%f"

# xmls
XMLS = {
    "mp3": "https://www.radionyhetene.no/download/nyheter/mp3/nyheter.xml",
    "mp3jingle": "https://www.radionyhetene.no/download/nyheter/mp3jl/nyheter.xml"
}

FILENAME_TEMPLATE = "nyheter_{timestamp}.mp3"

# the number of seconds determining if the file is too old and needs a new update
MAX_AGE = 1000


def return_weekday(daystring):
    return time.strptime(daystring, "%a").tm_wday

def get_statefile_timestamp(statefile):
    if os.path.isfile(statefile):
        with open(statefile, 'r') as fp:
            timestamp = fp.readlines()[0]

        try:
            return datetime.datetime.strptime(timestamp, TIMESTAMP_FORMAT)
        except ValueError:
            return None
    return None


def check_statefile(now, statefile):
    last_downloaded = get_statefile_timestamp(statefile)
    
    # if the file is not valid, then return True
    if not last_downloaded:
        return True
    
    if (now - last_downloaded).total_seconds() > MAX_AGE:
        return True
   
    return False


def check_if_inside(now, schedule):
    for interval in schedule:
        day_interval = range(*map(return_weekday, interval.split("-")))
        time_interval = range(*map(int, schedule[interval].split("-")))

        # this feels so wrong, but map() cannot help me here
        day_interval = range(day_interval.start, day_interval.stop + 1)
        time_interval = range(time_interval.start, time_interval.stop + 1)

        if (now.weekday() in day_interval and now.hour in time_interval):
            return True

    return False

def check_minute(now, valid_minutes):
    for m in valid_minutes:
        minute_range = range(
            int(m.split("-")[0]),
            int(m.split("-")[1]) + 1
        )
        if now.minute in minute_range:
            return True

    return False

def logmsg(logfile, message):
    with open(logfile, 'a') as fp:
        fp.write("[{timestamp}] {message}".format(
            timestamp=datetime.datetime.now(),
            message=message)
        )


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

    debug = False
    if "debug" in cfg["news"]:
        if cfg["news"]["debug"]:
            debug = True

    now = datetime.datetime.now()

    # check if this is inside the intervals specified
    if not check_if_inside(now, cfg["news"]["schedule"]):
        sys.exit(0)

    # check if we're at a minute when we should check for new files
    if not check_minute(now, cfg["news"]["minutes_to_check"]):
        sys.exit(0)

    # check if the previous file downloaded is fresh enough
    if not check_statefile(now, cfg["news"]["statefile"]):
        sys.exit(0)

    r = requests.get(
        XMLS[cfg["news"]["filetype"]],
        auth=(
            cfg["news"]["username"],
            cfg["news"]["password"]
        )
    )

    if r.status_code == 200:

        result = xmltodict.parse(r.text)

        time = datetime.datetime.strptime(result["ads"]["ad"]["time"], TIMESTAMP_FORMAT)
        url = result["ads"]["ad"]["url"]

        # check if there's a newer file than the one we already have downloaded
        last_downloaded = get_statefile_timestamp(cfg["news"]["statefile"])

        if last_downloaded == time:
            sys.exit(0)

        local_path = os.path.join(
            cfg["news"]["folder"],
            FILENAME_TEMPLATE.format(timestamp=time.strftime(TIMESTAMP_FORMAT))
        )

        if os.path.isfile(local_path):
            sys.exit(0)

        mp3_f = requests.get(
            url,
            auth=(cfg["news"]["username"], cfg["news"]["password"]),
            stream=True
        )

        if mp3_f.status_code == 200:

            with open(local_path, 'wb') as f:
                for chunk in mp3_f:
                    f.write(chunk)

            if "newsfile" in cfg["news"]:

                if os.path.isfile(cfg["news"]["newsfile"]):
                    os.remove(cfg["news"]["newsfile"])

                os.link(
                    local_path,
                    cfg["news"]["newsfile"]
                )

            with open(cfg["news"]["statefile"], 'w') as fp:
                fp.write(time.strftime(TIMESTAMP_FORMAT))


if __name__ == '__main__':
    main(sys.argv[1:])
