from enum import Enum


class ModelName(str, Enum):
    MEDSAM = "medsam"
    UNETPP_PATCHES = "unetpp-patches"


class ExportFormat(str, Enum):
    PNG = "png"
    MASK = "mask"
    OVERLAY = "overlay"
    REPORT = "report"
