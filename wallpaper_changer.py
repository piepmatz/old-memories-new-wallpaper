#!/usr/bin/env python

from __future__ import unicode_literals, print_function

from datetime import date
import random
import sys
import argparse
import os

from sources import FilesystemSource, LightroomSource
from desktop_environments import OSXDesktop, WindowsDesktop
from util import error


def load_source(args):
    if os.path.isdir(args.source):
        return FilesystemSource(args.source, recursive=args.recursive)
    elif args.source.endswith(".lrcat"):
        return LightroomSource(args.source)
    else:
        error("{} is neither a directory nor a Lightroom catalog.".format(args.source))


def load_desktop_environment():
    platform = sys.platform
    if platform == "darwin":
        return OSXDesktop()
    elif platform == "win32":
        return WindowsDesktop()
    else:
        error("Your operating system is not supported.")


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

    desktop = load_desktop_environment()
    current_wallpaper = desktop.get_current_wallpaper()

    image_source = load_source(args)

    today = date.today().replace(year=2020) # use 2020, it's a leap year, so pics taken on Feb 29 are valid

    images, dates = image_source.get_images_and_capture_dates()
    assert len(images) == len(dates)
    if len(images) == 0:
        error("Unable to find any images in the given source." +
              (" Consider the -r switch." if isinstance(image_source, FilesystemSource) and not args.recursive else ""))

    # replace capture dates with their absolute time deltas as seen from today considering only month and day
    deltas = [abs(today - d.replace(year=today.year)).days for d in dates]

    # find minimal time delta
    min_delta_value = min(deltas)

    # find all images sharing the minimal time delta
    candidates = [images[i] for i, d in enumerate(deltas) if d == min_delta_value]
    candidates_cnt = len(candidates)

    if candidates_cnt > 1 and current_wallpaper in candidates:
        candidates.remove(current_wallpaper)

    wallpaper = random.choice(candidates)

    if not args.dry_run:
        desktop.set_wallpaper(wallpaper)

    if args.verbose:
        dates_cnt = len(dates)
        print("Current wallpaper: {}".format(current_wallpaper))
        print("{} {} available in {}".format(dates_cnt, "image is" if dates_cnt == 1 else "images are", args.source))
        print("{} {} a time delta of {} {} as seen from today."
              .format(candidates_cnt,
                      "image has" if candidates_cnt == 1 else "images have",
                      min_delta_value,
                      "day" if min_delta_value == 1 else "days"))

    if args.verbose or args.dry_run:
        print("New wallpaper: {}".format(wallpaper))

    sys.exit(0)


if __name__ == "__main__":
    main()
