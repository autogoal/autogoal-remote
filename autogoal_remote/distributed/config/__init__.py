from inspect import getsourcefile
from os.path import abspath, dirname, join
from typing import Dict, List

import yaml
from yamlable import YamlAble, yaml_info

config_dir = dirname(abspath(getsourcefile(lambda: 0)))


@yaml_info(yaml_tag_ns="autogoal.remote.connectionAlias")
class Alias(YamlAble):
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip
        self.port = port


@yaml_info(yaml_tag_ns="autogoal.remote.connectionConfig")
class ConnectionConfig(YamlAble):
    def __init__(self, connections: Dict[str, Alias] = None):
        self.connections = connections or dict()


def _load_config() -> ConnectionConfig:
    path = join(config_dir, "connections.yml")
    result = None
    try:
        with open(path, "r") as fd:
            result = yaml.safe_load(fd)
            if result is None:
                raise IOError()
    except IOError as e:
        config = ConnectionConfig()
        with open(path, "w") as fd:
            yaml.dump(config, fd)
            result = config

    return result


def _save_config(config: ConnectionConfig):
    path = join(config_dir, "connections.yml")
    with open(path, "w") as fd:
        yaml.dump(config, fd)


def store_connection(ip: str, port: int, alias: str):
    config = _load_config() or ConnectionConfig()
    calias = Alias(alias, ip, port)
    config.connections[alias] = calias
    _save_config(config)


def clear_connetions():
    config = _load_config()
    config.connections = dict()
    _save_config(config)


def get_stored_aliases():
    config = _load_config()
    return list(config.connections.values())


def resolve_alias(alias_name: str):
    config = _load_config()
    return config.connections.get(alias_name)
