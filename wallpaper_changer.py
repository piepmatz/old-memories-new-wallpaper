#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from datetime import date
import sqlite3 as sqlite
import random
import subprocess
import sys
import argparse
import os

from sources import FilesystemSource, LightroomSource
from util import error

WALLPAPER_SETTINGS = "~/Library/Application Support/Dock/desktoppicture.db"


def set_wallpaper(img_path):

    def _restart_dock():
        subprocess.call(["/usr/bin/killall", "Dock"])

    if not os.path.isfile(os.path.expanduser(WALLPAPER_SETTINGS)):
        error("BUG: unable to find OS X wallpaper settings")

    try:
        conn = sqlite.connect(os.path.expanduser(WALLPAPER_SETTINGS))
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source",
                        help="The source where to take wallpapers from. "
                             "Can be a directory or an Adobe Lightroom 6 catalog.")
    parser.add_argument("-r", "-R", "--recursive",
                        action="store_true",
                        help="When the source is a directory, look for images recursively.")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Show which image would be chosen without actually changing the wallpaper.")
    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        help="Show additional information such as number of images in the source and how many images"
                             "are qualififed for the current date.")
    args = parser.parse_args()
    source_path = args.source

    if os.path.isdir(source_path):
        image_source = FilesystemSource(source_path, recursive=args.recursive)

    elif source_path.endswith(".lrcat"):
        image_source = LightroomSource(source_path)
    else:
        error("{} is neither a directory nor a Lightroom catalog.".format(source_path))

    today = date.today()

    images, dates = image_source.get_images_and_capture_dates()
    assert len(images) == len(dates)
    if len(images) == 0:
        error("Unable to find any images in the given source.")

    # replace capture dates with their absolute time deltas as seen from today considering only month and day
    dates = [abs(today - d.replace(year=today.year)).days for d in dates]

    # find minimal time delta and its index
    min_delta_index, min_delta_value = min(enumerate(dates), key=lambda delta: delta[1])

    # find all images' indexes sharing the minimal time delta
    candidates_indexes = [i for i, d in enumerate(dates) if d == min_delta_value]

    wallpaper = images[random.choice(candidates_indexes)]

    if not args.dry_run:
        set_wallpaper(wallpaper)

    if args.verbose:
        dates_cnt = len(dates)
        print("{} {} available in {}".format(dates_cnt, "image is" if dates_cnt==1 else "images are", source_path))
        candidates_cnt = len(candidates_indexes)
        print("{} {} a time delta of {} {} as seen from today."
              .format(candidates_cnt,
                      "image has" if candidates_cnt == 1 else "images have",
                      min_delta_value,
                      "day" if min_delta_value == 1 else "days"))

    if args.verbose or args.dry_run:
        print("New Wallpaper: {}".format(wallpaper))

    sys.exit(0)


if __name__ == "__main__":
    main()
