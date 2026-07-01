import time

import local_config as config

from services.logger_service import (
    info_logger,
    error_logger
)

from services.status_service import status

from services.attendance_service import AttendanceService


attendance = AttendanceService(
    config,
    info_logger,
    error_logger,
    status
)


def main():
    
    attendance.sync()


def infinite_loop(sleep_time=15):

    info_logger.info("Service Started")

    while True:

        try:

            main()

        except Exception:

            error_logger.exception(
                "Main Loop Error"
            )

        time.sleep(sleep_time)


if __name__ == "__main__":

    infinite_loop()