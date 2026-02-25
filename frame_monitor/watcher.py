import time
import os
from astropy.io import fits
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import numpy as np


def read_telemetry(filepath, col=4):
    try:
        return np.genfromtxt(filepath, usecols=col, invalid_raise=False)
    except Exception:
        return np.array([])


class FrameMonitorHandler(FileSystemEventHandler):
    # seconds to wait before processing a new file, to allow it to be fully written
    PATIENCE = 0.5

    def __init__(self, data_queue, config):
        super().__init__()
        self.data_queue = data_queue
        self.telemetry_col = 4  # hardcoded as in original, or make configurable
        self.file_prefix = config.file_prefix
        self.last_telemetry_time = None

    def on_created(self, event):
        if event.is_directory \
                or not event.src_path.endswith(".fits") \
                or self.file_prefix not in os.path.basename(event.src_path):
            return

        time.sleep(self.PATIENCE)

        try:
            with fits.open(event.src_path) as hdul:
                exptime = float(hdul[0].header.get("EXPTIME", -1))
            if exptime <= 0:
                return

            tel_file = event.src_path.replace(".fits", ".txt")
            if not os.path.exists(tel_file):
                return

            times = read_telemetry(tel_file, col=self.telemetry_col)
            if len(times) < 1:
                return

            gap = 0.0
            if self.last_telemetry_time is not None:
                gap = times[0] - self.last_telemetry_time
                gap = max(0.0, gap)

            intra_dts = np.diff(times).astype(float) if len(times) >= 2 else np.array([])

            self.last_telemetry_time = times[-1]

            self.data_queue.put((gap, intra_dts, exptime, len(times)))

        except Exception as e:
            print(f"Error processing {event.src_path}: {e}")


def start_observer(data_queue, config):
    handler = FrameMonitorHandler(data_queue, config)
    observer = Observer()
    observer.schedule(handler, path=config.data_dir, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()