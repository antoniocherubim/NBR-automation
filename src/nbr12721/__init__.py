"""Pacote importável mínimo do projeto NBR 12721.

Disponível: registro de fontes (`sources`) e índice normativo v1
(`normative`). Ainda não há motor de regras, PDF, OCR, geometria ou XLSX.
"""

from nbr12721 import normative, sources

__all__ = ["__version__", "normative", "sources"]
__version__ = "0.0.0"
