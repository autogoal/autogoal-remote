from autogoal_remote.distributed.remote_algorithm import *
from autogoal_remote.distributed.client import *
from autogoal_remote.distributed.server import *
from autogoal_remote.distributed.config import *
from autogoal_remote.distributed.proxy import *
from autogoal_remote.distributed.utils import *


def get_algorithms(ip: str = None, port: int = None, alias: str = None):
    from autogoal_remote.distributed.client import (
        get_algorithms,
        build_route,
        get_address,
    )
    import asyncio

    ip, port = get_address(ip, port, alias)
    uri = f"{build_route(ip, port)}/get-algorithms"

    async def load():
        raw_algorithms = (await get_algorithms(uri))["algorithms"]
        return [
            build_proxy_class(RemoteAlgorithmDTO(**ralg), ip, port)
            for ralg in raw_algorithms
        ]

    try:
        result = asyncio.run(load())
    except:
        result = []
    return result


if __name__ == "__main__":
    algs = get_algorithms(alias="remote-sklearn")
    print(algs)
