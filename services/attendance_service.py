from providers.biometric_provider import BiometricProvider
from providers.idesk360_provider import IDesk360Provider

from api.hrms_api import send_attendance


class AttendanceService:

    def __init__(
        self,
        config,
        info_logger,
        error_logger,
        status
    ):

        self.config = config
        self.info_logger = info_logger
        self.error_logger = error_logger
        self.status = status

        self.providers = []

        self.load_providers()

    # ----------------------------------------
    # Load Providers
    # ----------------------------------------

    def load_providers(self):

        self.providers.clear()

        if "BIOMETRIC" in self.config.ATTENDANCE_PROVIDERS:

            self.providers.append(
                BiometricProvider(
                    self.config,
                    self.info_logger,
                    self.error_logger,
                    self.status
                )
            )

        if "IDESK360" in self.config.ATTENDANCE_PROVIDERS:

            self.providers.append(
                IDesk360Provider(
                    self.config,
                    self.info_logger,
                    self.error_logger,
                    self.status
                )
            )

    # ----------------------------------------
    # Run All Providers
    # ----------------------------------------

    def sync(self):

        self.info_logger.info("Attendance Sync Started")

        for provider in self.providers:

            self.run_provider(provider)

        self.info_logger.info("Attendance Sync Completed")

    # ----------------------------------------
    # Run Single Provider
    # ----------------------------------------

    def run_provider(self, provider):

        provider_name = provider.__class__.__name__

        self.info_logger.info(
            f"Running {provider_name}"
        )

        try:

            punches = provider.get_attendance()

            self.info_logger.info(
                f"{provider_name} returned {len(punches)} punches."
            )

            for punch in punches:

                self.send_punch(punch)

            provider.update_last_sync()

            self.info_logger.info(
                f"{provider_name} completed successfully."
            )

        except Exception as ex:
            self.error_logger.exception(f"{provider_name} failed")

    # ----------------------------------------
    # Send Single Punch
    # ----------------------------------------

    def send_punch(self, punch):      

        status_code, message = send_attendance(
            employee_field_value=punch['employee_code'],
            timestamp=punch['timestamp'],
            device_id=punch['device_id'],
            log_type=punch['log_type']
        )

        if status_code == 200:

            self.info_logger.info(
                f"{punch['employee_code']} synced successfully."
            )

        else:

            self.error_logger.error(
                f"{punch['employee_code']} sync failed."
            )

            self.error_logger.error(message)