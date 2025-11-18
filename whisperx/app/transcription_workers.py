from PySide6.QtCore import QRunnable, QObject, Signal

import traceback
import time
from typing import Optional, Dict, Any, Callable

from whisperx.app.app_config import TranscriptionConfig

# Lazy imports - only import heavy modules when actually needed
# This significantly speeds up application startup time

class WorkerSignals(QObject):
    """Signals for worker thread communication."""

    # progress
    progress_updated = Signal(int)
    status_updated = Signal(str)

    # state / completion signals
    finished = Signal()
    error = Signal(str) # str = error message

    # data
    transcription_completed = Signal(dict)
    models_loaded = Signal(dict)

class ModelLoaderWorker(QRunnable):
    """Worker for loading WhisperX models in background."""

    def __init__(self, config: TranscriptionConfig):
        super().__init__()
        self.config = config
        self.signals = WorkerSignals()
        # Don't create bridge here - delay until run() to avoid importing heavy modules at startup
        self.bridge = None

        # progress
        self._progress_callback = self._on_progress_update
        self._status_callback = self._on_status_update

    def _on_progress_update(self, progress: int) -> None:
        """Handle progress updates from WhisperX."""
        self.signals.progress_updated.emit(progress)

    def _on_status_update(self, status: str) -> None:
        """Handle status updates from WhisperX."""
        self.signals.status_updated.emit(status)

    def run(self):
        # Model loading
        try:
            # Lazy import - only import when we actually need it
            import torch
            from whisperx.app.whisperx_bridge import WhisperXBridge

            # Create bridge now (not in __init__)
            self.bridge = WhisperXBridge()

            # CRITICAL: Initialize CUDA context in this worker thread
            # This prevents segmentation faults when loading CUDA models
            if torch.cuda.is_available():
                # Set thread count to 1 for better stability with CUDA
                torch.set_num_threads(1)

                # Initialize CUDA context in this thread
                device_id = self.config.device_index if self.config.device == 'cuda' else 0
                with torch.cuda.device(device_id):
                    # Force CUDA initialization in this thread
                    torch.cuda.current_device()
                    # Synchronize to ensure CUDA is ready
                    torch.cuda.synchronize()

            self.signals.status_updated.emit("Loading model")
            self.signals.progress_updated.emit(0)

            models = self.bridge.load_models(
                config = self.config,
                progress_callback = self._progress_callback,
                status_callback = self._status_callback
            )

            self.signals.progress_updated.emit(100)
            self.signals.status_updated.emit("Models loaded successfully")
            self.signals.models_loaded.emit(models)
            self.signals.finished.emit()

        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit(str(e))

class TranscriptionWorker(QRunnable):
    """Worker for WhisperX transcription processing."""

    def __init__(self, config: TranscriptionConfig, models: Optional[Dict] = None):
        super().__init__()
        self.config = config
        self.models = models
        self.signals = WorkerSignals()
        # Don't create bridge here - delay until run() to avoid importing heavy modules at startup
        self.bridge = None

        # progress trackung
        self._progress_callback = self._on_progress_update
        self._status_callback = self._on_status_update

        self._last_progress_time = 0
        self._last_progress_value = -1

    def _on_progress_update(self, progress: int) -> None:
        # Only emit progress updates every 2% or every 500ms
        current_time = time.time()
        if (progress - self._last_progress_value >= 2 or
            current_time - self._last_progress_time >= 2):
            self.signals.progress_updated.emit(progress)
            self._last_progress_time = current_time
            self._last_progress_value = progress



    def _on_status_update(self, status: str) -> None:
        self.signals.status_updated.emit(status)

    def run(self):
        # Execute transcription process
        try:
            # Lazy import - only import when we actually need it
            import torch
            from whisperx.app.whisperx_bridge import WhisperXBridge

            # Create bridge now (not in __init__)
            self.bridge = WhisperXBridge()

            # CRITICAL: Initialize CUDA context in this worker thread
            # This prevents segmentation faults when using models loaded in a different thread
            if torch.cuda.is_available():
                # Set thread count to 1 for better stability with CUDA
                torch.set_num_threads(1)

                # Initialize CUDA context in this thread
                device_id = self.config.device_index if self.config.device == 'cuda' else 0
                with torch.cuda.device(device_id):
                    # Force CUDA initialization in this thread
                    torch.cuda.current_device()
                    # Synchronize to ensure CUDA is ready
                    torch.cuda.synchronize()

            if not self.config.audio_file:
                raise ValueError("No audio file specified!")

            self.signals.status_updated.emit("Starting transcription...")
            self.signals.progress_updated.emit(0)

            # perform transcription
            print("WORKER RUN CONFIG ", str(self.config))
            result = self.bridge.transcribe_audio(
                config=self.config,
                models=self.models,
                progress_callback=self._progress_callback,
                status_callback=self._status_callback
            )

            self.signals.progress_updated.emit(100)
            self.signals.status_updated.emit("Transcription completed")
            self.signals.transcription_completed.emit(result)
            self.signals.finished.emit()

        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit(str(e))

