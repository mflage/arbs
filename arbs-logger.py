#!/usr/bin/env python2

import sys
import yaml
import mysql.connector
import datetime

from mpd import MPDClient


class PlaylistDB:
    def __init__(self, connection, cursor):
        self.con = connection
        self.cur = cursor

    def addPlaylist(self, timestamp, song):
        sql = "INSERT INTO playlist (date, song) VALUES (%s, %s)"
        self.cur.execute(sql, [timestamp, song])
        self.con.commit()

    def addArtist(self, artist):
        sql = "INSERT INTO artists (artist) VALUES (%s)"
        self.cur.execute(sql, [artist])
        self.con.commit()

    def addSong(self, artist, title, length, filename):
        sql = ("INSERT INTO songs (artist, title, length, filename) "
               "VALUES (%s, %s, %s, %s)")
        self.cur.execute(sql, [artist, title, length, filename])
        self.con.commit()

    # this will check if the artist is in the database, if not, add it
    def validateArtist(self, artist):
        if not self.checkArtist(artist):
            self.addArtist(artist)

        return self.getArtistId(artist)

    def getSong(self, filename):
        sql = ("SELECT s.id, a.artist, s.title, s.length, s.filename "
               "FROM songs s, artists a "
               "WHERE s.artist = a.id AND filename = %s")
        self.cur.execute(sql, [filename])
        row = self.cur.fetchone()
        return row

    def getSongId(self, filename):
        sql = "SELECT id FROM songs WHERE filename = %s"
        self.cur.execute(sql, [filename])
        row = self.cur.fetchone()
        if not row:
            return None
        else:
            return int(row[0])

    def getArtistId(self, artist):
        sql = "SELECT id FROM artists WHERE artist = %s"
        self.cur.execute(sql, [artist])
        row = self.cur.fetchone()
        if not row:
            return None
        else:
            return int(row[0])

    def updateArtist(self, songid, artist):
        artistid = self.validateArtist(artist)
        sql = "UPDATE songs SET artist = %s WHERE id = %s"
        self.cur.execute(sql, (artistid, songid))
        self.con.commit()

    def update(self, songid, field, value):
        sql = "UPDATE songs SET " + field + " = %s WHERE id = %s"
        self.cur.execute(sql, [value, songid])
        self.con.commit()

    def checkArtist(self, artist):
        if not self.getArtistId(artist):
            return False
        else:
            return True


def setupDB(hostname, username, password, database):
    conn = mysql.connector.connect(user=username,
                                   password=password,
                                   database=database,
                                   host=hostname)
    return conn


def main(arg):

    with open(arg[0], 'r') as configfile:
        try:
            cfg = yaml.load(configfile)
        except yaml.scanner.ScannerError, e:
            sys.exit("Error in configuration file: %s" % e)

    m = MPDClient()
    m.timeout = 60
    m.idletimeout = None

    # connect to the local running instance
    m.connect("localhost", 6600)

    conn = setupDB(cfg["database"]["hostname"],
                   cfg["database"]["username"],
                   cfg["database"]["password"],
                   cfg["database"]["database"])

    cursor = conn.cursor(buffered=True)

    db = PlaylistDB(conn, cursor)

    # everything is set up, get ready to receive new events
    while 1:
        subsystem = m.idle()
        if "player" in subsystem:
            currentsong = m.currentsong()

            status = m.status()

            if status["state"] != "play":
                continue

            if cfg["folders"]["teasers"] in currentsong["file"]:
                print(currentsong["file"])
                continue

            now = datetime.datetime.now()

            filename = currentsong["file"]

            if filename.startswith("file://"):
                filename = filename.replace("file://", "")

            song = db.getSong(filename)

            # song is not already added
            if not song:

                artistid = db.validateArtist(currentsong["artist"])

                db.addSong(artistid,
                           currentsong["title"],
                           currentsong["time"],
                           filename)

                # we should now have a new song id
                songid = db.getSongId(filename)
            else:
                # we don't have validation in place just yet
                pass

            db.addPlaylist(now.strftime("%Y-%m-%d %H:%M:%S", songid)

            print("{} - {} ({})".format(currentsong["artist"],
                                        currentsong["title"],
                                        filename)
            )


if __name__ == '__main__':
    main(sys.argv[1:])
