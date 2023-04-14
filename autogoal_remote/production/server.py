from typing import Any
from fastapi import FastAPI, Response, Request
from pathlib import Path
from pydantic import BaseModel
from autogoal.utils._storage import inspect_storage
import uvicorn
from autogoal_remote.distributed.proxy import loads, dumps, encode, decode


class Body(BaseModel):
    values: Any


app = FastAPI()


@app.get("/input")
async def input(request: Request):
    """
    Returns the model input type
    """
    return {
        "semantic type name": str(request.app.model.best_pipeline_.input_types),
        "pickled data": dumps(request.app.model.best_pipeline_.input_types, use_dill=True),
        }


@app.get("/output")
async def output(request: Request):
    """
    Returns the model output type
    """
    return {
        "semantic type name": str(
            request.app.model.best_pipeline_.algorithms[-1].__class__.output_type()
        ),
        "pickled data": dumps(request.app.model.best_pipeline_.algorithms[-1].__class__.output_type(), use_dill=True),
    }


@app.get("/inspect")
async def inspect(request: Request):
    """
    Returns the model inspect command
    """
    return {"data": str(inspect_storage(Path(request.app.model.export_path)))}


@app.post("/")
async def eval(t: Body, request: Request):
    """
    Returns the model prediction over the provided values
    """
    model = request.app.model
    data = loads(t.values)
    result = model.predict(data)
    return {"data": dumps(result)}


def run(model, ip=None, port=None):
    """
    Starts HTTP API with specified model.
    """
    app.model = model
    uvicorn.run(app, host=ip or "0.0.0.0", port=port or 8000)
