from utils.ConfigRead import ConfigRead


class Config:
    def __init__(self):
        self.data_config = self.get_config("config.json")
        self.database_config = self.get_config("database_config.json")

    @staticmethod
    def get_config(path):
        return ConfigRead(path)()

    @property
    def mail(self):
        sender_email = self.data_config['sender_email']
        receiver_email = self.data_config['receiver_email']
        password = self.data_config['password']
        hour = self.data_config['hour']
        minute = self.data_config['minute']
        return sender_email, receiver_email, password, hour, minute

    @property
    def database(self):
        return self.database_config
