import requests
import datetime


class PendulumProvider:

    def __init__(self, config, logger, error_logger, status):

        self.config = config
        self.logger = logger
        self.error_logger = error_logger
        self.status = status

        self.pendulum_last_sync = datetime.datetime.now().replace(
            microsecond=0
        )

        self.config.ATT_SOURCE = "PENDULUM"

    # -------------------------------------------------------
    # Public
    # -------------------------------------------------------

    def get_attendance(self):

        self.logger.info("Starting Pendulum Sync")

        from_date, to_date = self.get_sync_range()
        last_sync_time=from_date

        self.pendulum_last_sync = to_date

        logs = self.get_login_logout_logs(
            from_date,
            to_date
        )

        punches = self.convert_logs_to_punches(logs,last_sync_time)
      
        self.logger.info(
            f"Pendulum Punch Count : {len(punches)}"
        )

        return punches

    # -------------------------------------------------------
    # Login / Logout Logs
    # -------------------------------------------------------

    def get_login_logout_logs(
            self,
            from_date,
            to_date):

        url = (
            f"{self.config.PENDULUM_URL}"
            f"/api/user_login_logout.php"
        )

        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d")
        }

        headers = {
            "x-api-key": self.config.PENDULUM_API_KEY.strip()
        }

        self.logger.info(
            f"Pendulum Request : "
            f"{params['from']} -> {params['to']}"
        )

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("success"):

            raise Exception(
                f"Pendulum API returned success=false: {result}"
            )

        logs = result.get("data", [])

        self.logger.info(
            f"Pendulum Logs Loaded : {len(logs)}"
        )

        return logs

    # -------------------------------------------------------
    # Convert
    # -------------------------------------------------------

    def convert_logs_to_punches(
            self,
            logs,last_sync_time):

        punches = []

        for log in logs:

            user_id = str(log.get("user", "")).strip()

            event = str(
                log.get("event", "")
            ).upper().strip()

            event_date = log.get("event_date")

            if not user_id:
                self.logger.warning(
                    f"Pendulum User Not Found : {log}"
                )
                continue

            if not event_date:
                self.logger.warning(
                    f"Pendulum Event Date Missing : {log}"
                )
                continue

            # compare to last push time 
            
            if last_sync_time> self.str_to_datetime(event_date):
                self.logger.warning(
                    f"Already synced : {log}"
                )
                continue

            # -----------------------------------------------
            # LOGIN
            # -----------------------------------------------

            if event == "LOGIN":

                punches.append({

                    "employee_code":
                        user_id,

                    "employee_name":
                        user_id,

                    "timestamp":
                        self.str_to_datetime(
                            event_date
                        ),

                    "log_type":
                        "IN",

                    "device_id":
                        "PENDULUM",

                    "source":
                        "Pendulum"

                })

            # -----------------------------------------------
            # LOGOUT
            # -----------------------------------------------

            elif event == "LOGOUT":

                punches.append({

                    "employee_code":
                        user_id,

                    "employee_name":
                        user_id,

                    "timestamp":
                        self.str_to_datetime(
                            event_date
                        ),

                    "log_type":
                        "OUT",

                    "device_id":
                        "PENDULUM",

                    "source":
                        "Pendulum"

                })

            else:

                self.logger.warning(
                    f"Unknown Pendulum Event : "
                    f"{event} | User : {user_id}"
                )

        punches.sort(
            key=lambda x: x["timestamp"]
        )

        return punches

    # -------------------------------------------------------
    # Date
    # -------------------------------------------------------

    def get_sync_range(self):

        last_sync = self.status.get(
            "pendulum_last_sync"
        )

        if last_sync:

            start = datetime.datetime.strptime(
                last_sync,
                "%Y-%m-%d %H:%M:%S"
            )

        else:

            start = datetime.datetime.strptime(
                self.config.IMPORT_START_DATE,
                "%Y%m%d"
            )

        end = datetime.datetime.now().replace(microsecond=0)
        #end = datetime.datetime(2026, 8, 12, 23, 59, 59)

        return start, end

    # -------------------------------------------------------
    # Update Sync
    # -------------------------------------------------------

    def update_last_sync(self):

        self.status.set(
            "pendulum_last_sync",
            self.pendulum_last_sync.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        self.status.save()

    # -------------------------------------------------------
    # Helper
    # -------------------------------------------------------

    def str_to_datetime(
            self,
            date_string):

        return datetime.datetime.strptime(
            date_string,
            "%Y-%m-%d %H:%M:%S"
        )