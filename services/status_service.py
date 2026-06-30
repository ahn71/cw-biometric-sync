import os
import datetime
from pickledb import PickleDB

import local_config as config


class StatusService:

    def __init__(self):

        if not os.path.exists(config.LOGS_DIRECTORY):
            os.makedirs(config.LOGS_DIRECTORY)

        self.db = PickleDB(
            os.path.join(
                config.LOGS_DIRECTORY,
                "status.json"
            )
        )

    # ----------------------------------------
    # Basic Methods
    # ----------------------------------------

    def get(self, key, default=None):
        value = self.db.get(key)
        return default if value is None else value

    def set(self, key, value):
        self.db.set(key, value)

    def save(self):
        self.db.save()

    def remove(self, key):
        self.db.rem(key)
        self.db.save()

    def exists(self, key):
        return self.db.get(key) is not None

    # ----------------------------------------
    # DateTime Helpers
    # ----------------------------------------

    def get_datetime(
        self,
        key,
        fmt="%Y-%m-%d %H:%M:%S.%f"
    ):

        value = self.get(key)

        if not value:
            return None

        try:
            return datetime.datetime.strptime(
                value,
                fmt
            )

        except Exception:
            return None

    def set_datetime(
        self,
        key,
        value
    ):

        if isinstance(value, datetime.datetime):
            value = str(value)

        self.set(key, value)
        self.save()

    # ----------------------------------------
    # Sync Helpers
    # ----------------------------------------

    def update_pull_time(
        self,
        device_id
    ):

        self.set_datetime(
            f"{device_id}_pull_timestamp",
            datetime.datetime.now()
        )

    def update_push_time(
        self,
        device_id
    ):

        self.set_datetime(
            f"{device_id}_push_timestamp",
            datetime.datetime.now()
        )

    def update_provider_sync(
        self,
        provider_name
    ):

        self.set_datetime(
            f"{provider_name}_last_sync",
            datetime.datetime.now()
        )


status = StatusService()