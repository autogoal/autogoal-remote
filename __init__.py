"""
AutoGOAL is a Python framework for the automatic optimization, generation and learning of software pipelines.

A software pipeline is defined, for the purpose of AutoGOAL, as any software component, whether a class hierarchy,
a set of functions, or any combination thereof, that work together to solve a specific problem.
With AutoGOAL you can define a pipeline in many different ways, such that certain parts of it are configurable or
tunable, and then use search algorithms to find the best way to tune or configure it for a given problem.

This Remote package enable the following functionalities:
    - share algorithms from different contribs to other AutoGOAL instances accessible through network.
    - include algorithms shared by other AuutoGOAL instances in the AutoML process.
    - export a trained AutoML pipeline to an isolated, minimal Docker Container, and enable operations on this pipeline as a service.
"""

from .distributed import *
from .production import *