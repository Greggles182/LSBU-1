import logging
import os


class SizeCappedFileHandler(logging.FileHandler):
    def __init__(self, filename, max_bytes=5 * 1024 * 1024, retain_bytes=1 * 1024 * 1024, **kwargs):
        self.max_bytes = max_bytes
        self.retain_bytes = min(retain_bytes, max_bytes)
        super().__init__(filename, **kwargs)
        self._trim_if_needed()

    def emit(self, record):
        super().emit(record)
        self.flush()
        self._trim_if_needed()

    def _trim_if_needed(self):
        try:
            if os.path.getsize(self.baseFilename) <= self.max_bytes:
                return

            with open(self.baseFilename, "r+b") as log_file:
                file_size = os.fstat(log_file.fileno()).st_size
                if file_size <= self.max_bytes:
                    return

                log_file.seek(max(0, file_size - self.retain_bytes))
                log_file.readline()
                source_position = log_file.tell()
                destination_position = 0

                while chunk := log_file.read(64 * 1024):
                    source_position = log_file.tell()
                    log_file.seek(destination_position)
                    log_file.write(chunk)
                    destination_position += len(chunk)
                    log_file.seek(source_position)

                log_file.truncate(destination_position)
        except OSError:
            pass