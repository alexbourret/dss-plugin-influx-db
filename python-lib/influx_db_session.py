import requests
import time
from influx_db_auth import InfluxDBAuth
from influx_db_common import decode_csv_data, get_time_to_wait
from safe_logger import SafeLogger
from influx_db_constants import InfluxDBConstants


TRY_AGAIN_LATER = 409


logger = SafeLogger("influx-db plugin", forbidden_keys=["token", "password"])


class InfluxDBSessionError(ValueError):
    pass


class InfluxDBSession(object):
    def __init__(self, server_url, org=None, bucket_id=None, username=None,
                 password=None, token=None, generate_verbose_logs=False,
                 is_ssh_check_disabled=False):
        assert_valid_url(server_url)
        self.server_url = server_url.strip("/")
        self.session = requests.Session()
        if is_ssh_check_disabled:
            self.session.verify = True
        if token:
            self.session.auth = InfluxDBAuth(server_url, username, password, token)
        else:
            self.session.auth = (username, password)
        self.buffer = []
        self.buffer_size = 0
        self.bucket_id = bucket_id
        self.org = org

    def get_bucket_list(self):
        url = "{}/api/v2/buckets".format(self.server_url)
        response = self.get(url)
        json_response = response.json()
        buckets = json_response.get("buckets", [])
        return buckets

    def get_organization_list(self):
        url = "{}/api/v2/orgs".format(self.server_url)
        response = self.get(url)
        json_response = response.json()
        orgs = json_response.get("orgs", [])
        return orgs

    def get(self, url, headers=None, params=None):
        headers = headers or {}
        headers.update({
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json"
        })
        retry_number = 0
        while retry_number < InfluxDBConstants.MAX_RETRY:
            response = self.session.get(url, headers=headers, params=params)
            if response.status_code == TRY_AGAIN_LATER:
                time_to_wait = get_time_to_wait(response)
                retry_number = retry_number + 1
                logger.warning("Error 409 on attempt {}, waiting {} seconds".format(retry_number, time_to_wait))
                time.sleep(time_to_wait)
            else:
                break
        assert_response_ok(response)
        return response

    def batch_write(self, measurement, timestamp, tags, fields):
        self.buffer.append(to_influx_line_format(measurement, timestamp, tags, fields))
        self.buffer_size += 1
        if self.buffer_size > InfluxDBConstants.DEFAULT_BATCH_SIZE:
            logger.info("Max batch size reached, flushing")
            self.flush()

    def write(self, buffer):
        url = "{}/api/v2/write".format(self.server_url)
        params = {
            "bucket": self.bucket_id,
            "org": self.org
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "text/plain; charset=utf-8"
        }
        data = '\n'.join(buffer)
        response = self.post(url, data=data, params=params, headers=headers)
        return response

    def post(self, url, headers=None, data=None, params=None):
        headers = headers or {}
        retry_number = 0
        while retry_number < InfluxDBConstants.MAX_RETRY:
            response = self.session.post(url, data=data, headers=headers, params=params)
            if response.status_code == TRY_AGAIN_LATER:
                time_to_wait = 30
                time.sleep(time_to_wait)
                logger.warning("Error 409, waiting {} seconds".format(time_to_wait))
                retry_number = retry_number + 1
            else:
                break
        assert_response_ok(response)
        return response

    def flush(self):
        self.write(self.buffer)
        self.buffer = []
        self.buffer_size = 0
        return 0

    def close(self):
        row_processed = self.flush()
        return row_processed

    def query(self, sql_query):
        results = []
        url = "{}/api/v2/query".format(self.server_url)
        params = {"org": self.org}
        headers = {
            "Content-Type": "application/vnd.flux",
            "Accept": "application/csv"
        }
        response = self.post(url, params=params, headers=headers, data=sql_query)
        results = decode_csv_data(response.content)
        for result in results:
            yield result


def assert_response_ok(response, context=None, can_raise=True, generate_verbose_logs=False):
    error_message = ""
    error_context = " while {} ".format(context) if context else ""
    if not isinstance(response, requests.models.Response):
        error_message = "Did not return a valide response"
    else:
        status_code = response.status_code
        if status_code >= 400:
            error_message = "Error {}{}".format(status_code, error_context)
            json_content = ""
            message = ""
            json_content = safe_json_extract(response, default={})
            message = json_content.get("message")
            content = response.content
            if message:
                error_message += ". " + message
            elif json_content:
                error_message += ". " + json_content
            logger.error(error_message)
            logger.error(content)
    if error_message and can_raise:
        if generate_verbose_logs:
            logger.error("last requests url={}, body={}".format(response.request.url, response.request.body))
            pass
        raise Exception(error_message)
    return error_message


def safe_json_extract(response, default=None):
    json = default
    try:
        json = response.json()
    except Exception as error_message:
        logging.error("Error '{}' while decoding json".format(error_message))
        pass
    return json


def to_influx_line_format(measurement, timestamp, tags, fields):
    # batch_write:timestamp=0, tags=[{'location': 'Kalmath'}], fields=[{'census': 23}]
    tag_tokens = []
    for tag in tags:
        for key in tag:
            tag_tokens.append("{}={}".format(key, tag.get(key)))
    tags_string = ",".join(tag_tokens)
    if tag_tokens:
        tags_string = ","+tags_string
    fields_tokens = []
    for field in fields:
        for key in field:
            fields_tokens.append("{}={}".format(key, field.get(key)))
    fields_string = ",".join(fields_tokens)
    line = "{}{} {} {}".format(measurement, tags_string, fields_string, timestamp)
    # airSensors,sensor_id=TLM0201 temperature=73.97038159354763,humidity=35.23103248356096,co=0.48445310567793615 1630424257000000000
    # <measurement>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>]
    return line


def assert_valid_url(url):
    if not url:
        raise InfluxDBSessionError("Server URL not valid")
