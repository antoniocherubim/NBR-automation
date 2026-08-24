"""Pacote importável mínimo do projeto NBR 12721.

Disponível: registro de fontes (`sources`), índice normativo v1
(`normative`) e envelopes de artefato v1 (`artifacts`). Ainda não há motor
de regras, PDF, OCR, geometria ou XLSX.
"""

from nbr12721 import artifacts, normative, sources

__all__ = ["__version__", "artifacts", "normative", "sources"]
__version__ = "0.0.0"
