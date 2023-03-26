import requests
import logging


logging.basicConfig(level=logging.INFO, format='dss-plugin-influx-db %(levelname)s - %(message)s')
logger = logging.getLogger()


class InfluxDBAuth(requests.auth.AuthBase):
    def __init__(self, server_url, username=None, password=None, token=None):
        self.token = token
        self.username = username
        self.password = password
        # Authorization: Token INFLUX_TOKEN

    def __call__(self, request):
        if self.token:
            request.headers["Authorization"] = "Token {}".format(self.token)
        else:
            request.headers["Authorization"] = "Basic {}:{}".format(self.username, self.password)
        return request
