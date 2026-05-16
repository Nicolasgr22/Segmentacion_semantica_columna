from enum import Enum


class ModelName(str, Enum):
    MEDSAM = "medsam"
    PROGRESSIVE_UNET_BINARY = "progressive-unet-binary"


class ExportFormat(str, Enum):
    PNG = "png"
    MASK = "mask"
    OVERLAY = "overlay"
    REPORT = "report"
