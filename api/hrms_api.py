import json
import requests
from datetime import timezone
import time
import local_config as config


def send_attendance(self,
        att_source,
    employee_field_value,
    timestamp,
    device_id=None,
    log_type=None,
    latitude=None,
    longitude=None
):

    if config.HR_SYSTEM.upper() == "CWHRMS":
        return send_to_cwhrms(self,
            att_source,
            employee_field_value,
            timestamp,
            device_id,
            log_type,
            latitude,
            longitude
        )

    elif config.HR_SYSTEM.upper() == "ERPNEXT":
        return send_to_erpnext(
            employee_field_value,
            timestamp,
            device_id,
            log_type,
            latitude,
            longitude
        )

    else:
        raise Exception(
            f"Unsupported HR_SYSTEM: {config.HR_SYSTEM}"
        )


def send_to_cwhrms(self,
    att_source,
    employee_code,
    timestamp,
    device_id=None,
    log_type=None,
    latitude=None,
    longitude=None
):

    headers = {
        "token": config.CWHRMS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {

        "empAttDeviceID": employee_code,

        "punchWithDate":
            timestamp.astimezone(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",

        "source": att_source,

        "note": "",

        "companyId": config.CWHRMS_COMPANY_ID,

        "additionalInfo": json.dumps({

            "empAttDeviceID": employee_code,

            "device_id": device_id,

            "punchWithDate":
                timestamp.astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",

            "log_type": log_type
        })
    }

    try:

        url = (
            f"{config.CWHRMS_URL}"
            "/api/Attendance/attendace/biometric/create"
        )
        start_time = time.perf_counter()
        self.info_logger.info("Sending started")
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        elapsed = time.perf_counter() - start_time
        self.info_logger.info(
       f"Sending Completed. Time={elapsed:.3f}s"
       )

        response_json = response.json()
        self.info_logger.info(
        f"Sending Completed. Status Code: {response.status_code}"
        )
        if response.status_code == 200:

            try:

                

                return (
                    200,
                    response_json.get(
                        "message",
                        "SUCCESS"
                    )
                )

            except Exception:

                return 200, "SUCCESS"

        return (
            response.status_code,
            response.text
        )

    except Exception as ex:

        return (
            500,
            str(ex)
        )


def send_to_erpnext(
    employee_field_value,
    timestamp,
    device_id=None,
    log_type=None,
    latitude=None,
    longitude=None
):

    endpoint_app = (
        "hrms"
        if config.ERPNEXT_VERSION > 13
        else "erpnext"
    )

    url = (
        f"{config.ERPNEXT_URL}"
        "/api/method/"
        f"{endpoint_app}.hr.doctype.employee_checkin."
        "employee_checkin."
        "add_log_based_on_employee_field"
    )

    headers = {

        "Authorization":
            "token "
            + config.ERPNEXT_API_KEY
            + ":"
            + config.ERPNEXT_API_SECRET,

        "Accept": "application/json"

    }

    payload = {

        "employee_field_value":
            employee_field_value,

        "timestamp":
            str(timestamp),

        "device_id":
            device_id,

        "log_type":
            log_type,

        "latitude":
            latitude,

        "longitude":
            longitude
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:

            return (
                200,
                response.json()["message"]["name"]
            )

        return (
            response.status_code,
            response.text
        )

    except Exception as ex:

        return (
            500,
            str(ex)
        )