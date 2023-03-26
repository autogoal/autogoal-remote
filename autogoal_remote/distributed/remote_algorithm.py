import pickle
import re
from typing import Dict

import dill
from pydantic import BaseModel
from requests.api import delete, post

from autogoal.kb import AlgorithmBase
from autogoal.utils._dynamic import dynamic_import

contrib_pattern = r"autogoal_(?P<contrib>\w+)\."


def dumps(data: object, use_dill=False) -> str:
    data = dill.dumps(data) if use_dill else pickle.dumps(data)
    return decode(data)


def decode(data: bytes) -> str:
    return data.decode("latin1")


def loads(data: str, use_dill=False):
    raw_data = data.encode("latin1")
    return dill.loads(raw_data) if use_dill else pickle.loads(raw_data)


def encode(code: str):
    return code.encode("latin1")


class RemoteAlgorithmDTO(BaseModel):
    name: str
    module: str
    contrib: str
    input_args: str
    init_input_types: str
    inner_signature: str
    input_types: str
    output_type: str

    @staticmethod
    def from_local_class(algorithm_cls):
        name = algorithm_cls.__name__
        module = algorithm_cls.__module__
        contrib = re.search(contrib_pattern, module).group("contrib")
        input_args = dumps(algorithm_cls.input_args())
        init_input_types = dumps(algorithm_cls.init_input_types(), use_dill=True)
        inner_signature = dumps(algorithm_cls.get_inner_signature(), use_dill=True)
        input_types = dumps(algorithm_cls.input_types())
        output_type = dumps(algorithm_cls.output_type())

        return RemoteAlgorithmDTO(
            name=name,
            module=module,
            contrib=contrib,
            input_args=input_args,
            init_input_types=init_input_types,
            inner_signature=inner_signature,
            input_types=input_types,
            output_type=output_type,
        )

    def get_local_class(self):
        return dynamic_import(self.module, self.name)

    @staticmethod
    def get_local_class_from_dict(data: Dict):
        dto = RemoteAlgorithmDTO.parse_obj(data)
        return dto.get_local_class()
