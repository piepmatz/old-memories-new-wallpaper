from __future__ import unicode_literals

import os
import abc
import sqlite3 as sqlite
import subprocess
import ctypes

import six

from util import error


@six.add_metaclass(abc.ABCMeta)
class DesktopEnvironment(object):
    @abc.abstractmethod
    def get_current_wallpaper(self):
        pass

    @abc.abstractmethod
    def set_wallpaper(self, img_path):
        pass


class OSXDesktop(DesktopEnvironment):
    WALLPAPER_SETTINGS = "~/Library/Application Support/Dock/desktoppicture.db"

    def __init__(self):
        if not os.path.isfile(os.path.expanduser(self.WALLPAPER_SETTINGS)):
            error("BUG: unable to find OS X wallpaper settings")

    def _get_db(self):
        try:
            conn = sqlite.connect(os.path.expanduser(self.WALLPAPER_SETTINGS))
            cursor = conn.cursor()
            return conn, cursor
        except sqlite.OperationalError:
            error("Unable to open OS X wallpaper settings.")

    def get_current_wallpaper(self):
        conn, cursor = self._get_db()

        query = "SELECT value FROM data"

        try:
            cursor.execute(query)
            paths = cursor.fetchall()
            if not len(paths) > 0:
                error("Unable to get current wallpaper.")
            # we expect all rows to have the same content
            if not paths.count(paths[0]) == len(paths):
                return "You seem to have different wallpapers."
            return paths[0][0]
        except sqlite.DatabaseError as db_error:
            error("Unable to get current wallpaper: {}".format(db_error))
        finally:
            conn.close()

        return ""

    def set_wallpaper(self, img_path):

        def _restart_dock():
            subprocess.call(["/usr/bin/killall", "Dock"])

        conn, cursor = self._get_db()

        query = "UPDATE data SET value = (?)"

        try:
            cursor.execute(query, (img_path,))
            conn.commit()
        except sqlite.DatabaseError as db_error:
            error("Unable to save new wallpaper: {}".format(db_error))
        finally:
            conn.close()

        _restart_dock()


class WindowsDesktop(DesktopEnvironment):
    SPI_GETDESKWALLPAPER = 0x73
    SPI_SETDESKWALLPAPER = 0x14
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02
    BUFFER_SIZE = 256

    def get_current_wallpaper(self):
        wallpaper = ctypes.create_unicode_buffer(self.BUFFER_SIZE)
        res = ctypes.windll.user32.SystemParametersInfoW(
            self.SPI_GETDESKWALLPAPER, self.BUFFER_SIZE, wallpaper, 0)
        if not res:
            # call Windows's GetLastError() and print error message
            raise ctypes.WinError()
        if not wallpaper.value:
            return "Unable to get current wallpaper."
        return wallpaper.value

    def set_wallpaper(self, img_path):
        res = ctypes.windll.user32.SystemParametersInfoW(
            self.SPI_SETDESKWALLPAPER, 0, img_path, self.SPIF_UPDATEINIFILE | self.SPIF_SENDWININICHANGE)
        if not res:
            # call Windows's GetLastError() and print error message
            raise ctypes.WinError()
