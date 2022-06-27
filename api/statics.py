from enum import Enum


class Direction(Enum):
    desc = 0
    asc = 1


class Sorting(Enum):
    id = 0
    reads = 1
    likes = 2
    popularity = 3
