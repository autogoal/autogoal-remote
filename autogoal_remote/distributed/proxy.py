import autogoal_remote.distributed.client as client
from autogoal_remote.distributed.remote_algorithm import (
    AlgorithmBase,
    RemoteAlgorithmDTO,
    decode,
    dumps,
    encode,
    loads,
)
import json
import uuid
from typing import Dict

from pydantic import BaseModel
from requests.api import delete, post

from autogoal.kb import AlgorithmBase
import asyncio
from functools import partial


def build_proxy_class(dto: RemoteAlgorithmDTO, ip: str = None, port: int = None):
    ip = ip or "0.0.0.0"
    port = port or 8000
    id = f"{ip}:{port}-{dto.name}"
    cls = type(id, (RemoteAlgorithmBase,), {})
    cls.input_types = lambda: loads(dto.input_types)
    cls.init_input_types = lambda: loads(dto.init_input_types, use_dill=True)
    cls.get_inner_signature = lambda: loads(dto.inner_signature, use_dill=True)
    cls.output_type = lambda: loads(dto.output_type)
    cls.dto = dto
    cls.contrib = dto.contrib
    cls.ip = ip
    cls.port = port
    return cls


class RemoteAlgorithmBase(AlgorithmBase):
    contrib = "remote"
    dto: RemoteAlgorithmDTO = None
    ip: str = None
    port: int = None

    def __new__(cls: type, *args, **kwargs):
        uri = f"{client.build_route(cls.ip, cls.port)}/algorithm/instantiate"
        response = asyncio.run(
            client.instantiate(uri, cls.dto.dict(), dumps(args), dumps(kwargs))
        )
        instance = super().__new__(cls)
        instance.id = uuid.UUID(response["id"], version=4)
        return instance

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return self.__del__()

    def __del__(self):
        try:
            delete(
                f"http://{self.ip or '0.0.0.0'}:{self.port or 8000}/algorithm/{self.id}",
            )
        except:
            pass

    def _proxy_call(self, attr_name, *args, **kwargs):
        uri = f"{client.build_route(self.ip, self.port)}/algorithm/call"
        response = asyncio.run(
            client.call_algorithm(
                uri, str(self.id), attr_name, dumps(args), dumps(kwargs)
            )
        )
        return loads(response["result"])

    def _has_attr(self, attr_name):
        uri = f"{client.build_route(self.ip, self.port)}/algorithm/has_attr"
        response = asyncio.run(client.has_attr(uri, str(self.id), attr_name))
        return RemoteAttrInfo.construct(**response, attr=attr_name)

    def __getattribute__(self, name):
        # Calls to proxy_call are not supposed to be proxied.
        # Check for attributes from the local instance
        if (
            name == "_proxy_call"
            or name == "_has_attr"
            or name == "id"
            or name == "ip"
            or name == "port"
            or name == "__class__"
        ):
            return object.__getattribute__(self, name)

        # get remote information for the attribute.
        # do nothing if the attribute does not exists in the remote instance and return None.
        remote_attr_info = self._has_attr(name)
        if remote_attr_info.exists:
            if remote_attr_info.is_callable:
                # if attribute is callable then return a partial function based on _proxy_call
                #  which will take up the args and kwargs specified by the caller
                return partial(self._proxy_call, name)

            # if object is not callable then return the exact attr from the remote object
            return self._proxy_call("__getattribute__", name)

    def __repr__(self) -> str:
        inner = self._proxy_call("__repr__")
        return f"{self.__class__.__name__}({inner})"

    def __str__(self) -> str:
        inner = self._proxy_call("__repr__")
        return f"{self.__class__.__name__}({inner})"

    def run(self, *args):
        pass


class AttrCallRequest(BaseModel):
    instance_id: str
    attr: str
    args: str
    kwargs: str

    @staticmethod
    def build(instance_id: str, attr: str, args, kwargs):
        return AttrCallRequest(
            instance_id=instance_id,
            attr=attr,
            args=dumps(args),
            kwargs=dumps(kwargs),
        )


class InstantiateRequest(BaseModel):
    args: str
    kwargs: str
    algorithm_dto: Dict

    @staticmethod
    def build(dto: RemoteAlgorithmDTO, args, kwargs):
        return InstantiateRequest(
            args=dumps(args),
            kwargs=dumps(kwargs),
            algorithm_dto=dto,
        )


class RemoteAttrInfo(BaseModel):
    attr: str
    exists: bool
    is_callable: bool
