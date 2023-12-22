import os
import json


class ConfigRead:
    def __init__(self, file_name) -> None:
        self.file_name=file_name


    def __call__(self, *args, **kwargs):
        try:
            config_path = "./config/"
            with open(os.path.join(config_path, self.file_name), "r") as read_file:
                config: object = json.load(read_file)
            return config
        except Exception as e:
            print(e)
            return None
