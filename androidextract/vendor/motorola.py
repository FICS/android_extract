import os

from fnmatch import fnmatch
from . import Vendor, register_vendor
from ..tool import Tool

import androidextract.tool

class MotorolaVendor(Vendor):
    def __init__(self):
        super().__init__("motorola", "Motorola")

register_vendor(MotorolaVendor)

class MotorolaUnsparseTool(Tool):
    def __init__(self):
        super().__init__("MotoUnsparse", "androidextract/sparseimg")

    def unsparse_image(self, files, destination):
        sparse_files = {}

        for f in files:
            base = os.path.basename(f["name"])
            if fnmatch(base, "*sparsechunk*"):
                tokens = base.split("_")

                if len(tokens) != 2:
                    self.log.error("Sparse chunk name '%s' not in expected format (PARTITION_CHUNKNAME)",
                            base)
                    return None

                (partition_name, chunk_name,) = tokens

                # sparse chunk with numbers after a period need a skip after processing
                skip_needed = fnmatch(chunk_name, "*sparsechunk.*")

                if partition_name not in sparse_files:
                    sparse_files[partition_name] = {"skip_needed" : skip_needed, "chunks" : [f]}
                else:
                    if skip_needed != sparse_files[partition_name]["skip_needed"]:
                        self.log.error("Sparse chunks for %s both require a skip and dont", partition_name)
                        return None
                    sparse_files[partition_name]["chunks"] += [f]

        if len(sparse_files) == 0:
            self.log.error("No sparse chunks to be processed found")
            return None

        for partition_name, data in sparse_files.items():
            chunks = data["chunks"]
            tool = androidextract.tool.get("simg2img")
            output_path = os.path.join(destination, partition_name)
            tool.extract_to([chunk["name"] for chunk in chunks], output_path)

            if data["skip_needed"]:
                self.log.info("Sparse format requires header skip. Finding skip point...")
                offset = 0
                found_offset = -1

                in_file = open(output_path, 'rb')
                out_file = None

                while True:
                    data = in_file.read(16*1024*1024)

                    if len(data) == 0:
                        if found_offset == -1:
                            self.log.error("EOF reached when trying to skip sparse file header")
                            in_file.close()
                            os.unlink(output_path)
                            return None

                        in_file.close()
                        out_file.close()

                        os.rename(output_path+".skip", output_path)
                        break

                    if found_offset == -1:
                        # XXX: Technically this could be spread across two chunks...
                        off = data.find(b"\x53\xEF")

                        if off != -1:
                            found_offset = offset + off - 1080
                            self.log.info("Sparse skip-point found at offset 0x%x", found_offset)
                            self.log.info("Now writing truncated file...")
                            in_file.seek(found_offset)
                            out_file = open(output_path+".skip", 'wb')
                            continue

                        offset += len(data)

                    if out_file:
                        out_file.write(data)

            mime = androidextract.mime.require(output_path)
            expected_mime = "androidextract/fs-*"

            if not fnmatch(mime, expected_mime):
                self.log.error("Final unsparsed image '%s' does not have expected MIME type (got %s, expected %s)",
                        partition_name, mime, expected_mime)
                return None

        return
