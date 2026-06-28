"""Benchmark annotator wrappers."""

from .base import BaseAnnotator, CandidatePrediction, SpectrumRecord
from .fragannotor import FragAnnotorAnnotator
from .cfmid import CFMIDAnnotator
from .sirius import SiriusAnnotator
from .ms2deepscore import MS2DeepScoreAnnotator

__all__ = [
    "BaseAnnotator",
    "CandidatePrediction",
    "SpectrumRecord",
    "FragAnnotorAnnotator",
    "CFMIDAnnotator",
    "SiriusAnnotator",
    "MS2DeepScoreAnnotator",
]
