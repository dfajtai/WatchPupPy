import os
import logging
from logging.handlers import RotatingFileHandler
from PySide6.QtCore import QObject, Signal


class QtLogger(QObject, logging.Handler):
    """
    A logging handler that integrates Python's logging with a Qt Signal to emit log messages
    to a GUI component, while also writing logs to a rotating file.

    Signals:
        newLogMessage(str): Emitted when a new log message is available.
    """

    newLogMessage = Signal(str)

    def __init__(self, log_file="log/watchpupy.log"):
        """
        Initialize the QtLogger.

        Args:
            log_file (str): The path to the log file where logs will be written. 
                            The directory will be created if it does not exist.
        """
        QObject.__init__(self)
        logging.Handler.__init__(self)

        # Ensure the log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Set the logging level for this handler
        self.setLevel(logging.DEBUG)

        # Define the log message format including timestamp and log level
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Setup rotating file handler to manage log files (max 1MB each, keep 5 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Set the formatter for this handler (Qt signal emitter)
        self.setFormatter(formatter)

        # Create or get the logger instance for the application
        self.logger = logging.getLogger("WatchPupPy")
        self.logger.setLevel(logging.DEBUG)

        # Add the file handler and this QtLogger handler to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(self)

    def emit(self, record):
        """
        Emit a log record.

        This method is called by the logging framework when a record is logged.
        It formats the record and emits the 'newLogMessage' Qt signal with the message.

        Args:
            record (logging.LogRecord): The log record to be emitted.
        """
        msg = self.format(record)
        self.newLogMessage.emit(msg)

    def info(self, msg):
        """
        Log an informational message.
        
        Args:
            msg (str): The message to log.
        """
        self.logger.info(msg)

    def warning(self, msg):
        """
        Log a warning message.
        
        Args:
            msg (str): The message to log.
        """
        self.logger.warning(msg)

    def error(self, msg):
        """
        Log an error message.
        
        Args:
            msg (str): The message to log.
        """
        self.logger.error(msg)
