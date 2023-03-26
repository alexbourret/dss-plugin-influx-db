from influx_db_session import InfluxDBSession
from influx_db_common import get_credential


def build_select_choices(choices=None):
    if not choices:
        return {"choices": []}
    if isinstance(choices, str):
        return {"choices": [{"label": "{}".format(choices)}]}
    if isinstance(choices, list):
        return {"choices": choices}
    if isinstance(choices, dict):
        returned_choices = []
        for choice_key in choices:
            returned_choices.append({
                "label": choice_key,
                "value": choices.get(choice_key)
            })


def do(payload, config, plugin_config, inputs):
    parameter_name = payload.get('parameterName')
    if parameter_name in ["bucket", "orgs"]:
        server_url, username, password, token, is_ssh_check_disabled = get_credential(config)
        if not is_config_valid(server_url, username, password, token):
            return build_select_choices("Missing credentials")
        session = InfluxDBSession(server_url, org=None, username=username, password=password, token=token, is_ssh_check_disabled=is_ssh_check_disabled)

    if parameter_name == "bucket":
        choices = []
        buckets = session.get_bucket_list()
        for bucket in buckets:
            choices.append({
                "label": bucket.get("name"), "value": bucket.get("id")
            })
        choices.append({"label": "Create new bucket", "value": "new_bucket"})
        return build_select_choices(choices)
    if parameter_name == "orgs":
        choices = []
        orgs = session.get_organization_list()
        for org in orgs:
            choices.append({
                "label": org.get("name"), "value": org.get("id")
            })
        return build_select_choices(choices)
    return build_select_choices


def is_config_valid(server_url, username, password, token):
    if not server_url:
        return False
    if not token and not password:
        return False
    return True
