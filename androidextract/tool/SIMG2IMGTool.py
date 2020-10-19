import stat
import os
import re

from .tool import NativeTool

class SIMG2IMGTool(NativeTool):
    def __init__(self):
        super().__init__("simg2img", "simg2img", "androidextract/sparseimg")

    def extract_to(self, files, new_path):
        self.log.info("Converting Android sparse image %s -> unsparse IMG %s",
                [os.path.basename(f) for f in files], new_path)

        files = [os.path.abspath(path) for path in files]
        output, result = self._run([*files, os.path.abspath(new_path)])

        if result != 0:
            self.log.error("%s", output)

        return result == 0

