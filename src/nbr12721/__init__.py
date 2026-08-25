"""Pacote importável mínimo do projeto NBR 12721.

Disponível: registro de fontes (`sources`), índice normativo v1
(`normative`), envelopes de artefato v1 (`artifacts`) e profiler PDF v1
(`pdf`, PDF-001). Ainda não há motor de regras, extração semântica, OCR,
geometria ou XLSX.
"""

from nbr12721 import artifacts, normative, pdf, sources

__all__ = ["__version__", "artifacts", "normative", "pdf", "sources"]
__version__ = "0.0.0"
