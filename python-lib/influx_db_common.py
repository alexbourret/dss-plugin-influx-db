import time
from dateutil.parser import isoparse
from safe_logger import SafeLogger


logger = SafeLogger("influx-db plugin", forbidden_keys=["token", "password"])


def get_credential(config):
    preset_type = config.get("preset_type", "token_preset")
    preset = config.get(preset_type)
    if preset_type == 'user_preset':
        access_token = preset.get("access_token", {})
        username = access_token.get("user", None)
        password = access_token.get("password", None)
    else:
        username = preset.get("username", None)
        password = preset.get("password", None)
    token = preset.get("token", None)
    is_ssl_check_disabled = preset.get("is_ssl_check_disabled", False)
    server_url = preset.get("server_url")
    return server_url, username, password, token, is_ssl_check_disabled


def get_epoch_time(timestamp):
    if not timestamp:
        timestamp_in_seconds = int(time.time())
    elif type(timestamp) == str:
        timestamp_in_seconds = isoparse(timestamp).timestamp()
    else:
        timestamp_in_seconds = int(timestamp.timestamp())
    ret = timestamp_in_seconds * 1000000000
    return ret


def get_tags_from_row(row, tag_columns):
    tags = []
    for tag_column in tag_columns:
        tags.append({tag_column: row.get(tag_column)})
    return tags


def get_field_columns_from_row(row, field_columns):
    fields = []
    for field_column in field_columns:
        key_name = field_column.get("from")
        value = field_column.get("to")
        fields.append({
            row.get(key_name): row.get(value)
        })
    return fields


def get_field_value_columns_from_row(row, field_key_columns, field_value_columns):
    assert_same_number_of_columns(field_key_columns, field_value_columns)
    fields = []
    for field_key_column, field_value_column in zip(field_key_columns, field_value_columns):
        fields.append({
            row.get(field_key_column): row.get(field_value_column)
        })
    return fields


def assert_same_number_of_columns(columns_A, columns_B):
    if len(columns_A) != len(columns_B):
        raise ValueError("There is not 1 to 1 match between the number of field and value columns")


def parse_sql_query(sql_query):
    #  Todo
    return sql_query


def get_time_to_wait(response):
    time_to_wait = 30
    try:
        headers = response.headers
        retry_after = headers.get("Retry-After", 30)
        time_to_wait = int(retry_after)
    except Exception:
        pass
    return time_to_wait


class RecordsLimit():
    def __init__(self, records_limit=-1):
        self.has_no_limit = (records_limit == -1)
        self.records_limit = records_limit
        self.counter = 0

    def is_reached(self):
        if self.has_no_limit:
            return False
        self.counter += 1
        return self.counter > self.records_limit


def decode_csv_data(data):
    import csv
    import io
    json_data = None
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    try:
        reader = csv.DictReader(io.StringIO(data))
        json_data = list(reader)
    except Exception as error:
        logger.error("Could not extract csv data. Error={}".format(error))
        json_data = data
    return json_data
