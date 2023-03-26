from dataiku.exporter import Exporter
from influx_db_common import get_credential, get_epoch_time, get_tags_from_row, get_field_value_columns_from_row
from influx_db_session import InfluxDBSession
from safe_logger import SafeLogger
from influx_db_constants import InfluxDBConstants


logger = SafeLogger("influx-db plugin", forbidden_keys=["token", "password"])


class CustomExporter(Exporter):

    def __init__(self, config, plugin_config):
        logger.info("Starting influx-db exporter v{} with {}".format(
            InfluxDBConstants.PLUGIN_VERSION, logger.filter_secrets(config))
        )
        server_url, username, password, token, is_ssh_check_disabled = get_credential(config)
        org = config.get("orgs")
        bucket_id = config.get("bucket")
        self.session = InfluxDBSession(
            server_url,
            org=org,
            username=username,
            password=password,
            token=token,
            bucket_id=bucket_id,
            is_ssh_check_disabled=is_ssh_check_disabled
        )
        self.time_column = config.get("time_column", None)
        self.measurement_column = config.get("measurement_column", None)
        self.tag_columns = config.get("tag_columns", [])
        self.field_columns = config.get("field_columns", [])
        self.field_key_columns = config.get("field_key_columns", [])
        self.field_value_columns = config.get("field_value_columns", [])
        self.plugin_config = plugin_config
        self.f = None
        self.row_index = 0
        self.columns_names = []

    def open(self, schema):
        columns = schema.get("columns", [])
        self.columns_names = []
        for column in columns:
            self.columns_names.append(column.get("name"))

    def open_to_file(self, schema, destination_file_path):
        raise NotImplementedError

    def write_row(self, row):
        json_row = self.tuple_to_json(row)
        measurement = json_row.get(self.measurement_column, "")
        time = json_row.get(self.time_column, None)
        timestamp = get_epoch_time(time)
        tags = get_tags_from_row(json_row, self.tag_columns)
        fields = get_field_value_columns_from_row(json_row, self.field_key_columns, self.field_value_columns)
        self.session.batch_write(measurement, timestamp, tags, fields)

    def close(self):
        """
        Perform any necessary cleanup
        """
        self.session.close()

    def tuple_to_json(self, row_cells):
        json_row = {}
        for row_cell, column_name in zip(row_cells, self.columns_names):
            json_row[column_name] = row_cell
        return json_row
