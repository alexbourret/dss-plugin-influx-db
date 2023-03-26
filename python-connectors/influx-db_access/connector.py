from influx_db_session import InfluxDBSession
from influx_db_common import get_credential, parse_sql_query, RecordsLimit
from influx_db_constants import InfluxDBConstants
from dataiku.connector import Connector
from safe_logger import SafeLogger


logger = SafeLogger("influx-db plugin", forbidden_keys=["token", "password"])


class InfluxDBConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)  # pass the parameters to the base class
        logger.info("Starting influx-db connector v{} with {}".format(
            InfluxDBConstants.PLUGIN_VERSION, logger.filter_secrets(config))
        )
        server_url, username, password, token, is_ssh_check_disabled = get_credential(config)
        bucket_id = config.get("bucket_id")
        org = config.get("org")
        self.session = InfluxDBSession(
            server_url, org=org, username=username, password=password, token=token,
            bucket_id=bucket_id, is_ssh_check_disabled=is_ssh_check_disabled
        )
        self.sql_query = parse_sql_query(config.get("sql_query"))

    def get_read_schema(self):
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        results = self.session.query(self.sql_query)
        for result in results:
            yield result
            if limit.is_reached():
                return

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        raise NotImplementedError

    def get_partitioning(self):
        raise NotImplementedError

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        raise NotImplementedError


class CustomDatasetWriter(object):
    def __init__(self):
        pass

    def write_row(self, row):
        raise NotImplementedError

    def close(self):
        pass
