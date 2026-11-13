"""Common OCR contracts used by all local and future provider adapters."""

from abc import ABC, abstractmethod


class OCRUnavailable(RuntimeError):
    """Raised when a configured OCR engine cannot run in this environment."""


class OCREngine(ABC):
    name = ''
    model_name = ''

    def __init__(self, languages=('en',), device='cpu'):
        self.languages = tuple(languages) or ('en',)
        self.device = device

    @property
    def identifier(self):
        return f'{self.name}:{self.model_name}'

    @abstractmethod
    def is_available(self):
        """Return whether this adapter can run with the installed packages."""

    @abstractmethod
    def extract(self, image):
        """Return normalized OCR detections for an OpenCV image."""
