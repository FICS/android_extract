import shutil
import logging
import subprocess
import os

class Tool(object):
    def __init__(self, name, mime, vendors=[]):
        self.name = name
        self.path = ""
        self.mime = mime
        self.supported_vendors = {k : True for k in vendors}

        self.log = logging.getLogger("tool."+name)
        self.log.setLevel(logging.INFO)

    def get_supported_mimes(self):
        if isinstance(self.mime, str):
            return [self.mime]
        else:
            return self.mime

    def supports_mime(self, mime):
        return mime in self.get_supported_mimes()

class NativeTool(Tool):
    def __init__(self, name, exename, mime, vendors=[]):
        super().__init__(name, mime, vendors)
        self.exename = exename
        self.path = ""

    def _run(self, args, cwd=None):
        assert self.path != ""
        proc = subprocess.Popen([self.path] + args, executable=self.path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)

        self.log.debug("Run %s %s", self.path, args)
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            self.log.error("Process returned failure code %d", proc.returncode)

        return stdout.decode('ascii', 'ignore'), proc.returncode

    def resolve(self, reresolve=False):
        if self.path != "" and not reresolve:
            return self.path

        path = shutil.which(self.exename)

        if path is None:
            self.log.error("Unable to find tool")
            return

        self.path = os.path.abspath(path)
        self.log.debug("Found tool at %s", self.path)

        return self.path
