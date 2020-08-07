#!/usr/bin/env python3

import datetime
import os
import pytz
import requests
import shutil
import sys
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

def logmsg(logfile, message, timezone):
    with open(logfile, 'a') as fp:
        fp.write("[{timestamp}] {message}\n".format(
            timestamp=datetime.datetime.now(pytz.timezone(timezone)),
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
        result = yamale.validate(schema, data, True)
    except ValueError as e:
        print("Not validated correctly.")
        sys.exit(e)

    if not result[0].isValid():
        print("Not validated correctly.")
        sys.exit(1)

    # this feels a bit awkward
    cfg = data[0][0]

    debug = False
    logfile = None
    keep = False

    if "keep" in cfg["news"]:
        if cfg["news"]["keep"]:
            keep = True

    if "logfile" in cfg["news"]:
        logfile = cfg["news"]["logfile"]
        # should we also enable debugging?
        if "debug" in cfg["news"]:
            if cfg["news"]["debug"]:
                debug = True

    now = datetime.datetime.now(pytz.timezone(cfg["news"]["timezone"]))

    # check if this is inside the intervals specified
    if not check_if_inside(now, cfg["news"]["schedule"]):
        if debug:
            logmsg(
                logfile,
                "Not inside the scheduled check times",
                cfg["news"]["timezone"]
            )
        sys.exit(0)

    # check if we're at a minute when we should check for new files
    if not check_minute(now, cfg["news"]["minutes_to_check"]):
        if debug:
            log_minutes = " / ".join(cfg["news"]["minutes_to_check"])
            logmsg(
                logfile,
                ("Not inside the minutes interval for checking: {}".format(log_minutes)),
                cfg["news"]["timezone"]

            )
            
        sys.exit(0)

    xml = XMLS[cfg["news"]["filetype"]]

    if debug:
        logmsg(
            logfile,
            "Downloading new XML from: {}".format(xml),
            cfg["news"]["timezone"]
        )

    r = requests.get(
        xml,
        auth=(
            cfg["news"]["username"],
            cfg["news"]["password"]
        )
    )

    if r.status_code == 200:

        result = xmltodict.parse(r.text)

        time = datetime.datetime.strptime(result["ads"]["ad"]["time"], TIMESTAMP_FORMAT)
        url = result["ads"]["ad"]["url"]

        if debug:
            logmsg(
                logfile,
                "XML parsed. Timestamp: {}, URL of file: {}".format(time, url),
                cfg["news"]["timezone"]
            )

        # check if there's a newer file than the one we already have downloaded
        last_downloaded = get_statefile_timestamp(cfg["news"]["statefile"])

        if last_downloaded == time:
            if debug:
                logmsg(
                    logfile,
                    ("The timestamp of the file online ({}) "
                    "is the same as the one locally ({}) - ignoring".format(time, last_downloaded)),
                    cfg["news"]["timezone"]
                )
            sys.exit(0)

        local_path = os.path.join(
            cfg["news"]["folder"],
            FILENAME_TEMPLATE.format(timestamp=time.strftime(TIMESTAMP_FORMAT))
        )

        if os.path.isfile(local_path):
            sys.exit(0)

        if debug:
            logmsg(
                logfile,
                "Downloading {} to {}".format(url, local_path),
                cfg["news"]["timezone"]
            )

        mp3_f = requests.get(
            url,
            auth=(cfg["news"]["username"], cfg["news"]["password"]),
            stream=True
        )

        if mp3_f.status_code == 200:

            with open(local_path, 'wb') as f:
                for chunk in mp3_f:
                    f.write(chunk)

            if logfile:
                logmsg(
                    cfg["news"]["logfile"],
                    "Downloaded {}".format(os.path.basename(local_path)),
                    cfg["news"]["timezone"]
                )

            if "newsfile" in cfg["news"]:

                shutil.copy(
                    local_path,
                    cfg["news"]["newsfile"]
                )

                if not keep:
                    os.remove(local_path)

            with open(cfg["news"]["statefile"], 'w') as fp:
                fp.write(time.strftime(TIMESTAMP_FORMAT))


if __name__ == '__main__':
    main(sys.argv[1:])
