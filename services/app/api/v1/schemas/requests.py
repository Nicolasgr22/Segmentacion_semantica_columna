from enum import Enum


class ModelName(str, Enum):
    MEDSAM = "medsam"
    SEGFORMER_B2 = "segformer-b2"


class ExportFormat(str, Enum):
    PNG = "png"
    MASK = "mask"
    OVERLAY = "overlay"
    REPORT = "report"
