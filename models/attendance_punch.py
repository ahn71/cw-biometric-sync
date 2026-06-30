from dataclasses import dataclass
import datetime


@dataclass
class AttendancePunch:

    employee_code: str

    timestamp: datetime.datetime

    log_type: str

    device_id: str

    source: str

    employee_name: str = ""