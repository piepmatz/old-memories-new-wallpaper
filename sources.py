import sqlite3 as sqlite
import os
import abc
import six
from dateutil.parser import parse as parse_date

from util import error


@six.add_metaclass(abc.ABCMeta)
class ImageSource:
    @abc.abstractmethod
    def get_images_and_capture_dates(self):
        pass


class LightroomSource(ImageSource):
    def __init__(self, source_path):
        self.path = os.path.expanduser(source_path)  # deal with ~

        if not os.path.isfile(self.path):
            error("No such file: {}".format(self.path))

    def get_images_and_capture_dates(self):
        imgs = []
        capture_times = []

        try:
            conn = sqlite.connect(self.path)
        except sqlite.OperationalError:
            error("Unable to open Lightroom catalog.")

        query = """
            SELECT
                AgLibraryRootFolder.absolutePath,
                AgLibraryFolder.pathFromRoot,
                AgLibraryFile.idx_filename,
                Adobe_images.captureTime
            FROM Adobe_images
                INNER JOIN AgLibraryFile
                    ON Adobe_images.rootFile = AgLibraryFile.id_local
                INNER JOIN AgLibraryFolder
                    ON AgLibraryFile.folder = AgLibraryFolder.id_local
                INNER JOIN AgLibraryRootFolder
                    ON AgLibraryFolder.rootFolder = AgLibraryRootFolder.id_local
            WHERE Adobe_images.captureTime IS NOT NULL AND fileFormat = "JPG"
            """

        try:
            for (root, file_path, name, capture_time) in conn.execute(query):
                try:
                    capture_time = parse_date(capture_time).date()
                except:
                    continue  # skip image if parsing the date fails
                capture_times.append(capture_time)
                imgs.append(root + file_path + name)
        except sqlite.DatabaseError as e:
            error("Unable to query Lightroom catalog: {}".format(e))
        finally:
            conn.close()

        return imgs, capture_times
