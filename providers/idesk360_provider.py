import requests
import datetime

class IDesk360Provider:    

    def __init__(self, config, logger,error_logger, status):

        self.config = config
        self.logger = logger
        self.error_logger = error_logger
        self.status = status

        self.agent_map = {}
        self.idesk360_last_sync=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.config.ATT_SOURCE="IDESK360"

    # -------------------------------------------------------
    # Public
    # -------------------------------------------------------

    def get_attendance(self):

        self.logger.info("Starting IDesk360 Sync")

        self.agent_map = self.get_agents()

        from_date, to_date = self.get_sync_range()
        
        self.idesk360_last_sync=to_date

        sessions = self.get_login_sessions(
            from_date,
            to_date
        )

        punches = self.convert_sessions_to_punches(sessions)

        self.logger.info(
            f"IDesk360 Punch Count : {len(punches)}"
        )

        return punches

    # -------------------------------------------------------
    # Agents
    # -------------------------------------------------------

    def get_agents(self):

        url = (
            f"{self.config.IDESK360_URL}"
            f"/api/agents/"
        )

        params = {
            "key": self.config.IDESK360_API_KEY
        }

        headers = {
            "key": self.config.IDESK360_API_KEY
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        agents = response.json()

        mapping = {}

        for agent in agents:

            mapping[str(agent["id"])] = {
                "emp_id": agent["emp_id"],
                "name": agent["agent_name"],
                "email": agent["user_email"]
            }

        self.logger.info(
            f"Agent Loaded : {len(mapping)}"
        )

        return mapping

    # -------------------------------------------------------
    # Login Sessions
    # -------------------------------------------------------

    def get_login_sessions(
            self,
            from_date,
            to_date):

        url = (
            f"{self.config.IDESK360_URL}"
            f"/api/agent-login-sessions-report/"
        )

        date_range = f"{from_date.strftime('%d/%m/%Y %I:%M %p')} - {to_date.strftime('%d/%m/%Y %I:%M %p')}"
        print(date_range)
        params = {           
            "datetimes": date_range
        }

        headers = {
            "key": self.config.IDESK360_API_KEY
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=60
        )

        response.raise_for_status()

        sessions = response.json()
        sessions=sessions["login_session"]

        self.logger.info(
            f"Session Loaded : {len(sessions)}"
        )

        return sessions

    # -------------------------------------------------------
    # Convert
    # -------------------------------------------------------

    def convert_sessions_to_punches(
            self,
            sessions):

        punches = []

        for session in sessions:

            user_id = str(session["user_id"])

            if user_id not in self.agent_map:

                self.logger.warning(
                    f"Agent Not Found : {user_id}"
                )

                continue

            emp = self.agent_map[user_id]

            # LOGIN

            if session.get("login_time"):

                punches.append({

                    "employee_code":
                        emp["emp_id"],

                    "employee_name":
                        emp["name"],

                    "timestamp":
                        self.ms_to_datetime(
                            session["login_time"]
                        ),

                    "log_type":
                        "IN",

                    "device_id":
                        "IDESK360",

                    "source":
                        "I-Desk360"

                })

            # LOGOUT

            if session.get("logout_time"):

                punches.append({

                    "employee_code":
                        emp["emp_id"],

                    "employee_name":
                        emp["name"],

                    "timestamp":
                        self.ms_to_datetime(
                            session["logout_time"]
                        ),

                    "log_type":
                        "OUT",

                    "device_id":
                        "IDESK360",

                    "source":
                        "I-Desk360"

                })

        punches.sort(
            key=lambda x: x["timestamp"]
        )

        return punches

    # -------------------------------------------------------
    # Date
    # -------------------------------------------------------

    def get_sync_range(self):
        last_sync = self.status.get("idesk360_last_sync")
        if last_sync:
            # Notice the double datetime.datetime
            start = datetime.datetime.strptime(last_sync, "%Y-%m-%d %H:%M:%S")
        else:            
            start = datetime.datetime.strptime(self.config.IMPORT_START_DATE, "%Y%m%d")      

        end = datetime.datetime.now().replace(microsecond=0)
        return start, end

    # -------------------------------------------------------
    # Update Sync
    # -------------------------------------------------------

    def update_last_sync(self):

        self.status.set(
            "idesk360_last_sync",
            self.idesk360_last_sync.strftime("%Y-%m-%d %H:%M:%S")
            #datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        self.status.save()

    # -------------------------------------------------------
    # Helper
    # -------------------------------------------------------

    def ms_to_datetime(
            self,
            milliseconds):

        return datetime.datetime.fromtimestamp(
            milliseconds / 1000
        )