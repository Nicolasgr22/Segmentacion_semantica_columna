#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from setuptools import find_packages, setup

# Metadatos del paquete
NAME = 'model-medsam'
DESCRIPTION = "Empaquetamiento de modelo de segmentación semantica de la columna basado en MEDSAM"
URL = ""
EMAIL = "af.rinconr1@uniandes.edu.co"
AUTHOR = "anferiro"
REQUIRES_PYTHON = ">=3.14"
long_description = DESCRIPTION

about = {}
ROOT_DIR = Path(__file__).resolve().parent
REQUIREMENTS_DIR = ROOT_DIR / 'requirements'
PACKAGE_DIR = ROOT_DIR / 'model'
# VERSION como diccionario.
with open(PACKAGE_DIR / "VERSION") as f:
    _version = f.read().strip()
    about["__version__"] = _version


# Lista de dependencias de paquetes
# setuptools no acepta VCS URLs (git+https://) en install_requires;
# esas líneas se instalan directamente por pip desde requirements.txt
def list_reqs(fname="requirements.txt"):
    reqs = []
    with open(REQUIREMENTS_DIR / fname) as fd:
        for line in fd:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("git+"):
                reqs.append(line)
    return reqs

# Setup con las definiciones de arriba
# Ajuste licencia, versión de Python y Trove Classifiers si hace falta
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=("tests",)),
    package_data={"model": ["VERSION", "config/config.yml"]},
    install_requires=list_reqs(),
    entry_points={
        "console_scripts": [
            "medsam-train=model.train_runner:main",
        ],
    },
    extras_require={},
    include_package_data=True,
    license="BSD-3",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)