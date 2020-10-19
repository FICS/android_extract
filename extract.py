#!/usr/bin/env python3
import logging
import argparse
import sys

import androidextract as ae

log = logging.getLogger("androidextract")

def banner():
    print("""~~~~ Android Extractor ~~~~""")
    print("""    by  Grant Hernandez""")

def enable_logging_colors():
    COLOR_RED_INTENSE = "\033[1;31m"
    COLOR_RED = "\033[31m"
    COLOR_WHITE_INTENSE = "\033[1;37m"
    COLOR_WHITE = "\033[37m"
    COLOR_YELLOW_INTENSE = "\033[1;33m"
    COLOR_YELLOW = "\033[33m"
    COLOR_DEFAULT = "\033[0m"

    color_map = {
        logging.INFO : COLOR_WHITE_INTENSE + "INFO" + COLOR_DEFAULT,
        logging.ERROR : COLOR_RED_INTENSE + "ERROR" + COLOR_DEFAULT,
        logging.WARNING : COLOR_YELLOW_INTENSE + "WARN" + COLOR_DEFAULT,
        logging.CRITICAL : COLOR_RED_INTENSE + "CRIT" + COLOR_DEFAULT,
    }

    for k, v in color_map.items():
        logging.addLevelName(k, v)

def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    enable_logging_colors()

    banner()

    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True)
    parser.add_argument("firmware")

    args = parser.parse_args()

    log.info("Extracting Android firmware %s...", args.firmware)

    # TODO: mode preserve permissions
    # TODO: use SUDO_UID to chmod after extraction for easy user access
    if not ae.extract(args.vendor, args.firmware, "./aextract"):
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
