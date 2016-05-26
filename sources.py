import sqlite3 as sqlite
import os
import abc
import six
import re
import exifread
from datetime import datetime
from dateutil.parser import parse as parse_date

from util import error


@six.add_metaclass(abc.ABCMeta)
class ImageSource:
    @abc.abstractmethod
    def get_images_and_capture_dates(self):
        pass


class FilesystemSource(ImageSource):
    extensions_lower = ["jpg"]  # list of supported case-insensitive image file formats
    pattern_template = "^\w+.*\.({})$"

    def __init__(self, source_path, recursive=False):
        self.path = os.path.expanduser(source_path)  # deal with ~
        if not os.path.isdir(self.path):
            error("Not a directory: {}".format(self.path))

        self.recursive = recursive

        self.extensions = []
        for e in self.extensions_lower:
            self.extensions.append(e.lower())
            self.extensions.append(e.upper())
        self.pattern = re.compile(self.pattern_template.format('|'.join(self.extensions)))

    def get_images_and_capture_dates(self):
        img_files = []

        if self.recursive:
            for root, dir, files in os.walk(self.path):
                img_files += [os.path.join(root, file) for file in files if self.pattern.match(file)]
        else:
            img_files = [os.path.join(self.path, file) for file in os.listdir(self.path)
                         if os.path.isfile(os.path.join(self.path, file)) and self.pattern.match(file)]

        capture_times = []
        images_with_times = []
        for img in img_files:
            with open(img, 'rb') as f:
                try:
                    tags = exifread.process_file(f, stop_tag="DateTimeOriginal", details=False)
                except:
                    continue  # if a file is corrupt in any way, skip it
                date = tags.get("EXIF DateTimeOriginal") or tags.get("EXIF DateTimeDigitized")\
                       or tags.get("Image DateTime")
                if not date:
                    continue  # skip images without info when they were taken
                try:
                    # EXIF date format is YYYY:MM:DD HH:MM:SS
                    date = datetime.strptime(date.printable, "%Y:%m:%d %H:%M:%S").date()
                except ValueError:
                    continue  # skip image if parsing the date fails

                capture_times.append(date)
                images_with_times.append(img)

        return images_with_times, capture_times


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
