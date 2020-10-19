import stat
import os
import re
import shutil

from ..util.files import get_all_files
from .tool import Tool

class RUUTool(Tool):
    def __init__(self):
        super().__init__("HTC-RUU-Decrypt", "RUU_Decrypt_Tool", "androidextract/htc-ruu")

    def extract_to(self, path, directory):
        self.log.info("Decrypting HTC RUU %s -> %s", path, directory)

        # RUU decrypter creates a directory like OUT_*/ as a sibling to the firmware path
        # This is not good for keeping extracted results in the same folder
        # Use some hard link magic to fool the tool
        abspath = os.path.abspath(path)
        target_path = os.path.abspath(os.path.join(directory, os.path.basename(path)))

        try:
            os.link(abspath, target_path)
        except FileExistsError as e:
            self.log.error("Failed to create hard link: %s", e)
            return None

        # remove old OUT directories as they may have not completely properly
        for f in os.listdir(directory):
            if f.startswith("OUT"):
                self.log.warn("Removing old RUU OUT directory %s", f)
                shutil.rmtree(os.path.join(directory, f))

        # get the system image and other parts of the firmware
        output, result = self._run(["--system", "--firmware", target_path])
        #output = ""
        #result = 0

        # cleanup the hard link
        os.unlink(target_path)

        if result != 0:
            self.log.error("%s", output)
            return None

        produced_files = os.listdir(directory)
        out_dir = None

        # find the OUT directory and return a list of its contents for listing
        for f in produced_files:
            if f.startswith("OUT"):
                if out_dir:
                    log.error("Multiple OUT directories found!")
                    return None

                out_dir = os.path.join(directory, f)

        if not out_dir:
            self.log.error("RUU tool returned success but failed to produce a recognizable OUTput directory")
            self.log.error("%s", output)
            return None

        # find all files and folders in the out dir and move them upwards
        files = get_all_files(out_dir, depth=1)

        for f in files:
            name = f["name"]
            dir_name = os.path.basename(name)
            dest = os.path.join(directory, dir_name)

            try:
                os.stat(dest)
                self.log.warn("Removing existing destination directory %s", dir_name)
                shutil.rmtree(dest)
            except FileNotFoundError:
                pass

            os.rename(name, dest)

        # finally remove the OUT directory
        os.rmdir(out_dir)

        files = get_all_files(directory, relative=True)
        print(files)

        return files
