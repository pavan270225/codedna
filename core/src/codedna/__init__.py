"""CodeDNA - Local AI-code attribution with in-source provenance."""

__version__ = "0.1.0"
__all__ = [
    "Attribution",
    "AttributionLabel",
    "ProvenanceRegion",
    "ProvenanceHeader",
    "Classifier",
    "ClassifierConfig",
    "EditEvent",
    "Store",
    "HeaderWriter",
    "HeaderParser",
    "round_trip_test",
    "IPCServer",
]

from .models import Attribution, AttributionLabel, ProvenanceRegion, ProvenanceHeader
from .classifier import Classifier, ClassifierConfig, EditEvent
from .store import Store
from .header import HeaderWriter, HeaderParser, round_trip_test
from .ipc import IPCServer
