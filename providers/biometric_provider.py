from zk import ZK

from models.attendance_punch import AttendancePunch


class BiometricProvider:

    def __init__(self, config, logger, error_logger, status):

        self.config = config
        self.logger = logger
        self.error_logger = error_logger
        self.status = status

    # ----------------------------------------
    # Get Attendance
    # ----------------------------------------

    def get_attendance(self):

        punches = []

        for device in self.config.devices:

            try:

                punches.extend(
                    self.get_device_attendance(device)
                )

            except Exception:

                self.error_logger.exception(
                    f"Failed to fetch attendance from {device['device_id']}"
                )

        return punches

    # ----------------------------------------
    # Single Device Attendance
    # ----------------------------------------

    def get_device_attendance(self, device):

        zk = ZK(
            device["ip"],
            port=device.get("port", 4370),
            timeout=30
        )

        conn = None
        punches = []

        try:

            conn = zk.connect()

            conn.disable_device()

            attendances = conn.get_attendance()

            self.logger.info(
                f"{device['device_id']} : {len(attendances)} punches found."
            )

            for att in attendances:

                if device["punch_direction"] == "AUTO":

                    if att.punch in self.config.device_punch_values_OUT:
                        log_type = "OUT"

                    elif att.punch in self.config.device_punch_values_IN:
                        log_type = "IN"

                    else:
                        log_type = None

                else:

                    log_type = device["punch_direction"]

                # punches.append(
                #     AttendancePunch(
                #         employee_code=str(att.user_id),
                #         employee_name="",
                #         timestamp=att.timestamp,
                #         log_type=log_type,
                #         device_id=device["device_id"],
                #         source="BIOMETRIC"
                #     )
                # )
                punches.append({
                        "employee_code": str(att.user_id),
                        "employee_name": "",
                        "timestamp": att.timestamp,
                        "log_type": log_type,
                        "device_id": device["device_id"],
                        "source": "BIOMETRIC"
                    }
                )

            if device.get("clear_from_device_on_fetch", False):

                conn.clear_attendance()

            conn.enable_device()

            return punches

        except Exception:

            self.error_logger.exception(
                f"{device['device_id']} connection failed."
            )

            return []

        finally:

            if conn:

                try:
                    conn.disconnect()
                except:
                    pass

    # ----------------------------------------
    # Update Sync
    # ----------------------------------------

    def update_last_sync(self):

        self.logger.info(
            "Biometric sync completed."
        )