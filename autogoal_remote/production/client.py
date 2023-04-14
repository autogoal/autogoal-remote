import requests
from pydantic import BaseModel
from typing import Any
from autogoal_remote.distributed.proxy import loads, dumps, encode, decode
import json

class Body(BaseModel):
    values: Any

def get_input(ip: str = "localhost", port: int = 8000):
    base_url = f"http://{ip}:{port}"
    response = requests.get(f"{base_url}/input")
    return response.json()

def get_output(ip: str = "localhost", port: int = 8000):
    base_url = f"http://{ip}:{port}"
    response = requests.get(f"{base_url}/output")
    return response.json()

def get_inspect(ip: str = "localhost", port: int = 8000):
    base_url = f"http://{ip}:{port}"
    response = requests.get(f"{base_url}/inspect")
    return response.json()

def post_eval(data, ip: str = "localhost", port: int = 8000):
    base_url = f"http://{ip}:{port}"
    response = requests.post(f"{base_url}/", json=Body(values=dumps(data)).dict())
    content = json.loads(response.content)
    return loads(content["data"])