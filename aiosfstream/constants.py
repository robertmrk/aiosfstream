"""Constants and enumerations"""
from enum import Enum, unique


@unique
class ReplayOption(Enum):
    NEW_EVENTS = -1
    ALL_EVENTS = -2
