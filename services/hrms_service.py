import json
import requests
from datetime import timezone


class HRMSService:

    def __init__(
        self,
        config,
        info_logger,
        error_logger
    ):
        self.config = config
        self.info_logger = info_logger
        self.error_logger = error_logger

    # ==========================================================
    # Public Method
    # ==========================================================

    def send_attendance(self, punch):

        if self.config.HR_SYSTEM.upper() == "CWHRMS":

            return self.send_to_cwhrms(punch)

        elif self.config.HR_SYSTEM.upper() == "ERPNEXT":

            return self.send_to_erpnext(punch)

        else:

            raise Exception(
                f"Unsupported HR_SYSTEM : {self.config.HR_SYSTEM}"
            )

    # ==========================================================
    # CW-HRMS
    # ==========================================================

    def send_to_cwhrms(self, punch):

        url = (
            f"{self.config.CWHRMS_URL}"
            "/api/Attendance/attendace/biometric/create"
        )

        headers = {

            "token": self.config.CWHRMS_API_KEY,

            "Content-Type": "application/json"

        }

        payload = {

            "empAttDeviceID": punch.employee_code,

            "punchWithDate":
                punch.timestamp
                .astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",

            "source": punch.source,

            "note": "",

            "companyId": self.config.CWHRMS_COMPANY_ID,

            "additionalInfo": json.dumps({

                "device_id": punch.device_id,

                "log_type": punch.log_type

            })

        }

        try:

            response = requests.post(

                url,

                headers=headers,

                json=payload,

                timeout=30

            )

            if response.status_code == 200:

                return True

            self.error_logger.error(response.text)

            return False

        except Exception:

            self.error_logger.exception(
                "CW-HRMS API Error"
            )

            return False

    # ==========================================================
    # ERPNext
    # ==========================================================

    def send_to_erpnext(self, punch):

        endpoint = (
            "hrms"
            if self.config.ERPNEXT_VERSION > 13
            else "erpnext"
        )

        url = (
            f"{self.config.ERPNEXT_URL}"
            "/api/method/"
            f"{endpoint}.hr.doctype.employee_checkin."
            "employee_checkin."
            "add_log_based_on_employee_field"
        )

        headers = {

            "Authorization":
                "token "
                + self.config.ERPNEXT_API_KEY
                + ":"
                + self.config.ERPNEXT_API_SECRET,

            "Accept": "application/json"

        }

        payload = {

            "employee_field_value":
                punch.employee_code,

            "timestamp":
                str(punch.timestamp),

            "device_id":
                punch.device_id,

            "log_type":
                punch.log_type

        }

        try:

            response = requests.post(

                url,

                headers=headers,

                json=payload,

                timeout=30

            )

            if response.status_code == 200:

                return True

            self.error_logger.error(
                response.text
            )

            return False

        except Exception:

            self.error_logger.exception(
                "ERPNext API Error"
            )

            return False