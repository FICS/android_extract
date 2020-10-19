# TODO: replace libmagic with python-only magic from binwalk
# https://github.com/ReFirmLabs/binwalk/blob/master/src/binwalk/core/magic.py
import magic
import logging
import os
from fnmatch import fnmatch

from .tool import get_by_mime

log = logging.getLogger(__name__)

# Used to help give contexts in order to disambiguate MIME types
vendor_hint = None

def require(path, pattern):
    return fnmatch(get(path), pattern)

def get(path):
    justname, ext = os.path.splitext(os.path.basename(path))
    ext = ext.lower()

    try:
        mime = magic.from_file(path, mime=True)

        # if we just get an octet stream, try for something more specific...
        if mime == "application/octet-stream":
            full_magic = magic.from_file(path)
            if full_magic.startswith("Android bootimg"):
                return "androidextract/bootimg"
            elif full_magic.startswith("Android sparse"):
                return "androidextract/sparseimg"
            elif full_magic.startswith("Linux"):
                if "ext4 filesystem data" in full_magic:
                    return "androidextract/fs-ext4"
            elif full_magic.startswith("data"):
                # LG's KDZ format
                if ext == ".kdz":
                    return "androidextract/lg-kdz"
        elif mime == "application/x-dosexec":
            if vendor_hint == "htc":
                return "androidextract/htc-ruu"

        # otherwise, just fall back to octet stream, which will likely not lead to any processing
        return mime
    except IsADirectoryError:
        return "application/directory"
