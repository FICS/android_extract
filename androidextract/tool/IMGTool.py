import stat
import os
import re

from .tool import NativeTool

class IMGTool(NativeTool):
    def __init__(self):
        super().__init__("imgtool", "imgtool.ELF64", "androidextract/bootimg")

    def extract_to(self, path, directory):
        self.log.info("Extracting boot IMG %s -> %s", path, directory)

        output, result = self._run([os.path.abspath(path), "extract"], cwd=directory)

        # TODO: move extracted/ dir contents to provided directory

        if result != 0:
            self.log.error("%s", output)

        return result == 0

