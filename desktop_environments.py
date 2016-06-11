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
    SPI_SETDESKWALLPAPER = 0x14
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02

    def set_wallpaper(self, img_path):
        res = ctypes.windll.user32.SystemParametersInfoW(
            self.SPI_SETDESKWALLPAPER, 0, img_path, self.SPIF_UPDATEINIFILE | self.SPIF_SENDWININICHANGE)
        if not res:
            # call Windows's GetLastError() and print error message
            raise ctypes.WinError()
