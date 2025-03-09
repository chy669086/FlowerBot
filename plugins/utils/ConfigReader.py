import json
import structlog


config = None


def update_config():
    global config
    with open("plugins/data/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)


update_config()

logger = structlog.get_logger()


def get_logger():
    return logger


def read_main_path():
    return config["main_path"]


def read_contest_list():
    return config["clist_contest"]


def read_remind_times():
    return config["remind_times"]


def read_message_group_list():
    return config["message_group_list"]


def read_whitelist():
    return config["whitelist"]


if __name__ == "__main__":
    print(read_contest_list())
    print(config)
