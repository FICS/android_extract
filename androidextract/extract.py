import logging
import os

import androidextract.vendor
import androidextract.tool
import androidextract.mime
import androidextract.util.files

from .vendor import VENDOR_LIST

log = logging.getLogger("androidextract")

def extract_container(path, output_path):
    mime_type = androidextract.mime.get(path)

    if mime_type is None:
        return False

    usable_tools = androidextract.tool.get_extractor_by_mime(mime_type)

    if len(usable_tools) == 0:
        log.error("Unhandled MIME type %s. Cannot extract", mime_type)
        return False

    tool = usable_tools[0]
    output = tool.extract_to(path, output_path)
    return output

def list_container(path):
    mime_type = androidextract.mime.get(path)

    if mime_type is None:
        return False

    usable_tools = androidextract.tool.get_extractor_by_mime(mime_type)

    if len(usable_tools) == 0:
        log.error("Unhandled MIME type %s. Cannot list contents", mime_type)
        return False

    tool = usable_tools[0]
    output = tool.list(path)
    return output

def extract(vendor, firmware_path, output_path):
    if not androidextract.tool.resolve_tools():
        return False

    found = False

    for vend in VENDOR_LIST:
        if vend.get_short_name() == vendor:
            vendor = vend
            found = True
            break

    if not found:
        raise androidextract.AndroidExtractError("Unsupported vendor %s" % vendor)

    # XXX: this breaks any MIME-resolution parallelization across vendors in the same Python process
    androidextract.mime.vendor_hint = vendor.short_name

    # make the top-level output directory
    androidextract.util.files.mkdir(output_path)

    firmware_directory_name = os.path.basename(firmware_path)

    # remove any URL parameters (sometimes happens when using wget/cURL for images)
    firmware_directory_name = firmware_directory_name.split("?")[0]

    # remove any file extension
    firmware_directory_name, _ = os.path.splitext(firmware_directory_name)

    firmware_directory_path = os.path.join(output_path, firmware_directory_name)

    # make the firmware specific output path
    androidextract.util.files.mkdir(firmware_directory_path)

    #
    # recursively extract all file containers until we reach partitions
    #
    log.info("Stage 1: recursively extract")
    files_to_process = [(firmware_path, firmware_directory_path)]

    while len(files_to_process) > 0:
        path, dir_path = files_to_process.pop()

        files = extract_once(path, dir_path)

        if files is None:
            return False

        for f in files:
            sub_file = os.path.normpath(f["name"])
            _, ext = os.path.splitext(sub_file)
            sub_file_path = os.path.join(dir_path, sub_file)
            sub_file_dir = os.path.dirname(sub_file_path)
            sub_file_mime = androidextract.mime.get(sub_file_path)

            if sub_file_mime:
                tools = androidextract.tool.get_extractor_by_mime(sub_file_mime)

                # do not process anything resembling a jar or apk at this stage
                if len(tools) > 0 and ext.lower() not in [".jar", ".apk"]:
                    files_to_process += [(sub_file_path, sub_file_dir)]

    log.info("Stage 2: cannonicalize extracted files")

    file_list = androidextract.util.files.get_all_files(firmware_directory_path)

    if vend.short_name == "motorola":
        handler = androidextract.vendor.MotorolaUnsparseTool()
        handler.unsparse_image(file_list, firmware_directory_path)

    return True

def extract_once(path, output_path):
    files = extract_container(path, output_path)

    if files is None:
        log.error("Failed to extract container")
        return None

    return files
