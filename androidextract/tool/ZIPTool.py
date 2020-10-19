import stat
import os
import re

from .tool import NativeTool

class UNRARTool(NativeTool):
    def __init__(self):
        super().__init__("UNRAR", "unrar", "application/x-rar")

    def list(self, rarfile):
        # list, bare
        output, result = self._run(["lb", rarfile])

        if result != 0:
            self.log.error("%s", output)
            return None

        files = []

        for entry in output.split("\n"):
            if entry.strip() == "":
                continue
            files += [{"name" : entry }]

        return files

    def extract_to(self, rarfile, directory):
        self.log.info("Extracting RAR %s -> %s", rarfile, directory)

        output, result = self._run(["x", os.path.abspath(rarfile)], cwd=directory)

        if result != 0:
            self.log.error("%s", output)
            return None

        return self.list(rarfile)

class TARTool(NativeTool):
    def __init__(self):
        super().__init__("tar", "tar", "application/x-tar")

    def list(self, tarfile):
        # test, file
        output, result = self._run(["tf", tarfile])

        if result != 0:
            self.log.error("%s", output)
            return None

        files = []

        for entry in output.split("\n"):
            if entry.strip() == "":
                continue
            files += [{"name" : entry }]

        return files

    def extract_to(self, tarfile, directory):
        tarfile = os.path.abspath(tarfile)
        self.log.info("Extracting TAR %s -> %s", tarfile, directory)

        output, result = self._run(["xf", tarfile], cwd=directory)

        if result != 0:
            self.log.error("%s", output)
            return None

        return self.list(tarfile)

class UNZIPTool(NativeTool):
    def __init__(self):
        super().__init__("UNZIP", "unzip", ["application/zip", "application/java-archive"])

    def list(self, zipfile):
        # extra quiet, list
        output, result = self._run(["-qql", os.path.abspath(zipfile)])

        if result != 0:
            self.log.error("%s", output)
            return None

        files = []
        for entry in output.split("\n"):
            if entry.strip() == "":
                continue

            match = re.match("\s*(?P<size>\d+)\s+(?P<date>[^\s]+)\s+(?P<time>[^\s]+)\s+(?P<name>.*)", entry)

            if not match:
                log.error("Unable to get ZIP list as output does not match")
                return None

            name = match.group(4)

            files += [{"name" : match.group(4), "date" : match.group(2), "time" : match.group(3), "size" : match.group(1)}]

        return files

    def extract_to(self, zipfile, directory):
        zipfile = os.path.abspath(zipfile)
        self.log.info("Extracting ZIP %s -> %s", zipfile, directory)

        # overwrite always
        #output, result = self._run(["-o", zipfile], cwd=directory)
        output, result = self._run(["-n", zipfile], cwd=directory)

        if result != 0:
            self.log.error("%s", output)
            return None

        return self.list(zipfile)
