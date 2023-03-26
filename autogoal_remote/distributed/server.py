import uuid
import json
from typing import Any
import uvicorn
from autogoal_remote.distributed.proxy import (
    AttrCallRequest,
    InstantiateRequest,
    RemoteAlgorithmDTO,
    decode,
    dumps,
    encode,
    loads,
)

from fastapi import FastAPI, Request, WebSocket
from fastapi.exceptions import HTTPException

from autogoal_contrib import find_classes
from autogoal.utils import Gb, Hour, Kb, Mb, Min, RestrictedWorkerWithState, Sec
from autogoal.utils._dynamic import dynamic_call

from autogoal_remote.distributed.utils import receive_large_message, send_large_message
import pprint
import time

app = FastAPI()

# get references for every algorithm in contribs
algorithms = find_classes()

# simple set for pooling algorithm instances. If instances
# are not properly deleted can (and will) fill the memory
algorithm_pool = {}

# sets the RAM usage restriction for remote calls. This will only affect
# remote attribute calls and is ignored during the instance creation.
# Defaults to 4Gb.
remote_call_memory_limit = 4 * Gb

# sets the remote call timeout. This will only affect
# remote attribute calls and is ignored during the instance creation.
# Defaults to 20 Sec.
remote_call_timeout = 20 * Sec


#####################
#     HTTP API      #
#####################


@app.get("/")
async def root():
    return {"message": "Service Running"}


@app.get("/algorithms")
async def get_exposed_algorithms(request: Request):
    """
    Returns exposed algorithms
    """
    remote_algorithms = [RemoteAlgorithmDTO.from_algorithm_class(a) for a in algorithms]
    return {
        "message": f"Exposing {str(len(algorithms))} algorithms: {', '.join([a.__name__ for a in algorithms])}",
        "algorithms": remote_algorithms,
    }


@app.post("/algorithm/call")
async def instantiate(request: AttrCallRequest):
    id = uuid.UUID(request.instance_id, version=4)
    inst = algorithm_pool.get(id)
    if inst == None:
        raise HTTPException(400, f"Algorithm instance with id={id} not found")

    attr = getattr(inst, request.attr)
    is_callable = hasattr(attr, "__call__")

    func = (
        RestrictedWorkerWithState(
            dynamic_call, remote_call_timeout, remote_call_memory_limit
        )
        if is_callable
        else None
    )

    try:
        result = (
            func(inst, request.attr, *loads(request.args), **loads(request.kwargs))
            if is_callable
            else attr
        )
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"result": dumps(result)}


@app.post("/algorithm/has_attr")
async def has_attr(request: AttrCallRequest):
    id = uuid.UUID(request.instance_id, version=4)
    inst = algorithm_pool.get(id)
    if inst == None:
        raise HTTPException(400, f"Algorithm instance with id={id} not found")

    try:
        attr = getattr(inst, request.attr)
        result = True
    except:
        result = False

    return {"exists": result, "is_callable": result and hasattr(attr, "__call__")}


@app.post("/algorithm/instantiate")
async def instantiate(request: InstantiateRequest):
    dto = RemoteAlgorithmDTO.parse_obj(request.algorithm_dto)
    cls = dto.get_original_class()
    new_id = uuid.uuid4()
    algorithm_pool[new_id] = cls(*loads(request.args), **loads(request.kwargs))
    return {"message": "success", "id": new_id.bytes}


@app.delete("/algorithm/{raw_id}")
async def delete_algorithm(raw_id):
    id = uuid.UUID(raw_id, version=4)

    try:
        algorithm_pool.pop(id)
    except KeyError:
        # do nothing, key is already out of the pool. Dont ask that many questions...
        pass

    return {"message": f"deleted instance with id={id}"}


#####################
#  Websocket API    #
#####################


@app.websocket("/get-algorithms")
async def get_exposed_algorithms(websocket: WebSocket):
    """
    Returns exposed algorithms
    """
    await websocket.accept()
    remote_algorithms = [
        RemoteAlgorithmDTO.from_local_class(a).dict() for a in algorithms
    ]
    data = {
        "message": f"Exposing {str(len(algorithms))} algorithms: {', '.join([a.__name__ for a in algorithms])}",
        "algorithms": remote_algorithms,
    }
    await websocket.send_json(data)


fid = id


@app.websocket("/algorithm/call")
async def call(websocket: WebSocket):
    await websocket.accept()
    data = await receive_large_message(websocket)
    request = json.loads(data)
    id = uuid.UUID(request["instance_id"], version=4)
    inst = algorithm_pool.get(id)
    if inst == None:
        await websocket.send_json(
            {"error": f"Algorithm instance with id={id} not found"}
        )
        return

    attr = getattr(inst, request["attr"])
    is_callable = hasattr(attr, "__call__")
    run_as_restricted = is_callable and request["attr"] == "run"

    args = loads(request["args"])
    kwargs = loads(request["kwargs"])

    func = (
        RestrictedWorkerWithState(
            dynamic_call, remote_call_timeout, remote_call_memory_limit
        )
        if run_as_restricted
        else dynamic_call
    )

    try:
        result = attr
        if is_callable:
            result = func(
                inst,
                request["attr"],
                *args,
                **kwargs,
            )

        if run_as_restricted:
            result, ninstance = result
            if ninstance is not None:
                algorithm_pool[id] = ninstance

        result_data = json.dumps({"result": dumps(result)})
    except Exception as e:
        result_data = json.dumps({"error": str(e)})

    await send_large_message(websocket, result_data, 500)


@app.websocket("/algorithm/has_attr")
async def has_attr(websocket: WebSocket):
    await websocket.accept()
    request = await websocket.receive_json()
    id = uuid.UUID(request["instance_id"], version=4)
    inst = algorithm_pool.get(id)
    if inst == None:
        await websocket.send_json(
            {"error": f"Algorithm instance with id={id} not found"}
        )
        return

    try:
        attr = getattr(inst, request["attr"])
        result = True
    except:
        result = False

    await websocket.send_json(
        {"exists": result, "is_callable": result and hasattr(attr, "__call__")}
    )


@app.websocket("/algorithm/instantiate")
async def instantiate(websocket: WebSocket):
    await websocket.accept()
    request = await websocket.receive_json()
    dto = RemoteAlgorithmDTO.parse_obj(request["algorithm_dto"])
    cls = dto.get_local_class()
    new_id = uuid.uuid4()
    algorithm_pool[new_id] = cls(*loads(request["args"]), **loads(request["kwargs"]))
    await websocket.send_json({"message": "success", "id": str(new_id)})


@app.websocket("/algorithm/delete/{raw_id}")
async def delete_algorithm(websocket: WebSocket, raw_id):
    await websocket.accept()

    id = uuid.UUID(raw_id, version=4)

    try:
        algorithm_pool.pop(id)
    except KeyError:
        # do nothing, key is already out of the pool. Dont ask that many questions...
        pass

    await websocket.send_json({"message": f"deleted instance with id={id}"})


# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_text()
#         await websocket.send_text(f"Message text was: {data}")


def run(ip=None, port=None):
    """
    Starts HTTP API with specified model.
    """
    uvicorn.run(app, host=ip or "0.0.0.0", port=port or 8000)


if __name__ == "__main__":
    run()
