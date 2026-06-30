import os
import logging
from logging.handlers import RotatingFileHandler
from pickledb import PickleDB

import local_config as config


class LoggerService:

    def __init__(self):

        # Create logs directory if it doesn't exist
        if not os.path.exists(config.LOGS_DIRECTORY):
            os.makedirs(config.LOGS_DIRECTORY)

        self.info_logger = self._setup_logger(
            "info_logger",
            os.path.join(config.LOGS_DIRECTORY, "logs.log"),
            logging.INFO
        )

        self.error_logger = self._setup_logger(
            "error_logger",
            os.path.join(config.LOGS_DIRECTORY, "error.log"),
            logging.ERROR
        )

        self.status = PickleDB(
            os.path.join(config.LOGS_DIRECTORY, "status.json")
        )

    def _setup_logger(
        self,
        name,
        log_file,
        level=logging.INFO
    ):

        logger = logging.getLogger(name)

        logger.setLevel(level)

        if not logger.handlers:

            formatter = logging.Formatter(
                "%(asctime)s\t%(levelname)s\t%(message)s"
            )

            handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,   # 10 MB
                backupCount=50,
                encoding="utf-8"
            )

            handler.setFormatter(formatter)

            logger.addHandler(handler)

        return logger


# Singleton instance
logger_service = LoggerService()

# Export commonly used objects
info_logger = logger_service.info_logger
error_logger = logger_service.error_logger
status = logger_service.status