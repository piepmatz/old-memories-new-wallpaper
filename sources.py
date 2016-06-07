from __future__ import unicode_literals

import sqlite3 as sqlite
import os
import abc
import re
from datetime import datetime
import logging

import exifread
from dateutil.parser import parse as parse_date
import six

from util import error, to_unicode


@six.add_metaclass(abc.ABCMeta)
class ImageSource(object):
    @abc.abstractmethod
    def get_images_and_capture_dates(self):
        pass


class FilesystemSource(ImageSource):
    extensions_lower = ["jpg"]  # list of supported case-insensitive image file formats
    pattern_template = r"^\w+.*\.({})$"

    def __init__(self, source_path, recursive=False):
        self.path = os.path.expanduser(source_path)  # deal with ~
        if not os.path.isdir(self.path):
            error("Not a directory: {}".format(self.path))

        self.recursive = recursive

        self.extensions = []
        for ext in self.extensions_lower:
            self.extensions.append(ext.lower())
            self.extensions.append(ext.upper())
        self.pattern = re.compile(self.pattern_template.format('|'.join(self.extensions)))

        # exifread uses logging but requires us to set it up.
        exifread.exif_log.setup_logger(debug=False, color=False)
        # set logging to be less verbose
        exifread.exif_log.get_logger().setLevel(logging.ERROR)

    def get_images_and_capture_dates(self):
        img_file_names = []

        if self.recursive:
            for root, _, file_names in os.walk(self.path):
                img_file_names += [to_unicode(os.path.join(root, file_name))
                                   for file_name in file_names if self.pattern.match(file_name)]
        else:
            img_file_names = [to_unicode(os.path.join(self.path, file_name))
                              for file_name in os.listdir(self.path)
                              if os.path.isfile(os.path.join(self.path, file_name)) and self.pattern.match(file_name)]

        capture_times = []
        images_with_times = []
        for img_file_name in img_file_names:
            with open(img_file_name, 'rb') as img_file:
                try:
                    tags = exifread.process_file(img_file, stop_tag="DateTimeOriginal", details=False)
                except:
                    continue  # if a file is corrupt in any way, skip it
                date = tags.get("EXIF DateTimeOriginal") or tags.get("EXIF DateTimeDigitized") \
                       or tags.get("Image DateTime")
                if not date:
                    continue  # skip images without info when they were taken
                try:
                    # EXIF date format is YYYY:MM:DD HH:MM:SS
                    date = datetime.strptime(date.printable, "%Y:%m:%d %H:%M:%S").date()
                except ValueError:
                    continue  # skip image if parsing the date fails

                capture_times.append(date)
                images_with_times.append(img_file_name)

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
        except sqlite.DatabaseError as db_error:
            error("Unable to query Lightroom catalog: {}".format(db_error))
        finally:
            conn.close()

        return imgs, capture_times
