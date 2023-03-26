import json
from autogoal_remote.distributed.config import resolve_alias
from autogoal_remote.distributed.utils import send_large_message, receive_large_message
import websockets

def get_address(ip: str = None, port: int = None, alias: str = None):
    if alias is not None:
        c_alias = resolve_alias(alias)
        if c_alias is not None:
            ip = c_alias.ip
            port = c_alias.port
    return ip, port

def build_route(ip: str = None, port: int = None):
    return f"ws://{ip or '0.0.0.0'}:{port or 8000}"


async def get_algorithms(uri: str):
    async with websockets.connect(uri) as websocket:
        response = await websocket.recv()
        return json.loads(response)


async def call_algorithm(uri: str, instance_id, attr, args, kwargs):
    async with websockets.connect(uri) as websocket:
        request = {
            "instance_id": instance_id,
            "attr": attr,
            "args": args,
            "kwargs": kwargs,
        }
        data = json.dumps(request)
        await send_large_message(websocket, data, 500)
        response = await receive_large_message(websocket)
        response = json.loads(response)
        
        # simple error handling
        error = response.get("error")
        if error is not None:
            raise Exception(f"Proxy Error (server-side). {error}")

        return response

async def has_attr(uri: str, instance_id: str, attr: str):
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"instance_id": instance_id, "attr": attr}))
        response = await websocket.recv()
        return json.loads(response)


async def instantiate(uri: str, algorithm_dto: dict, args: list, kwargs: dict):
    async with websockets.connect(uri) as websocket:
        await websocket.send(
            json.dumps({"algorithm_dto": algorithm_dto, "args": args, "kwargs": kwargs})
        )
        response = await websocket.recv()
        return json.loads(response)
