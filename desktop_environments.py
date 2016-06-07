from __future__ import unicode_literals

import os
import abc
import six
import sqlite3 as sqlite
import subprocess
import ctypes

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

    def set_wallpaper(self, img_path):

        def _restart_dock():
            subprocess.call(["/usr/bin/killall", "Dock"])

        try:
            conn = sqlite.connect(os.path.expanduser(self.WALLPAPER_SETTINGS))
        except sqlite.OperationalError:
            error("Unable to open OS X wallpaper settings.")

        query = """
            UPDATE
                data
            SET VALUE = ("{}")
        """.format(img_path)

        try:
            conn.execute(query)
            conn.commit()
        except sqlite.DatabaseError as e:
            error("Unable to save new wallpaper: {}".format(e))
        finally:
            conn.close()

        _restart_dock()


class WindowsDesktop(DesktopEnvironment):
    SPI_SETDESKWALLPAPER = 0x14
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02

    def set_wallpaper(self, img_path):
        try:
            res = ctypes.windll.user32.SystemParametersInfoW(
                self.SPI_SETDESKWALLPAPER, 0, img_path, self.SPIF_UPDATEINIFILE | self.SPIF_SENDWININICHANGE)
        except Exception as e:
            error("Unable to change wallpaper. The following error occurred:\n{}".format(repr(e)))
        if not res:
            # call Windows's GetLastError() and print error message
            raise ctypes.WinError()
