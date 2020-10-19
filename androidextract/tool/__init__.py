import logging

log = logging.getLogger("androidextract")

from .ZIPTool import TARTool, UNZIPTool, UNRARTool
from .IMGTool import IMGTool
from .SIMG2IMGTool import SIMG2IMGTool
from .RUUTool import RUUTool

EXTRACTION_TOOL_LIST = [
    TARTool(),
    UNZIPTool(),
    UNRARTool(),
    RUUTool(),
]

TOOL_LIST = [
    *EXTRACTION_TOOL_LIST,
    IMGTool(),
    SIMG2IMGTool(),
    #Tool("7z", "7z"),
    #Tool("LZ4", "lz4", vendors=[samsung]),
]

TOOL_MAP = {tool.name : tool for tool in TOOL_LIST }

def get(name):
    return TOOL_MAP[name]

def get_by_mime(mime):
    usable_tools = []
    for tool in TOOL_LIST:
        if tool.supports_mime(mime):
            usable_tools += [tool]

    return usable_tools

def get_extractor_by_mime(mime):
    usable_tools = []
    for tool in EXTRACTION_TOOL_LIST:
        if tool.supports_mime(mime):
            usable_tools += [tool]

    return usable_tools

def resolve_tools():
    for tool in TOOL_LIST:
        if isinstance(tool, NativeTool) and tool.resolve() is None:
            log.error("Failed to resolve tool")
            return False

    return True

from .tool import *
