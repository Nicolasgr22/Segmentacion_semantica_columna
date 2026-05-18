"""
Configuración global de tests.

segment_anything no está disponible en el entorno local de CI/tests unitarios
(se instala desde GitHub y pesa ~375 MB). Se inyecta un stub en sys.modules
para que todos los imports de 'segment_anything.*' resuelvan sin errores,
manteniendo los tests Fast e Isolated.
"""

import sys
import types
from unittest.mock import MagicMock

# ─── Stub de segment_anything ────────────────────────────────────────────────
# Creamos módulos ficticios para cada sub-ruta que el código importa:
#   from segment_anything import sam_model_registry
#   from segment_anything.utils.transforms import ResizeLongestSide

_sa = types.ModuleType("segment_anything")
_sa.sam_model_registry = MagicMock()

_sa_utils = types.ModuleType("segment_anything.utils")
_sa_transforms = types.ModuleType("segment_anything.utils.transforms")
_sa_transforms.ResizeLongestSide = MagicMock()

_sa.utils = _sa_utils
_sa_utils.transforms = _sa_transforms

sys.modules.setdefault("segment_anything", _sa)
sys.modules.setdefault("segment_anything.utils", _sa_utils)
sys.modules.setdefault("segment_anything.utils.transforms", _sa_transforms)
