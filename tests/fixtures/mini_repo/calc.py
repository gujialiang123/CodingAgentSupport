"""A tiny calculator used as an offline fixture repository."""


def add(a, b):
    return a + b


def subtract(a, b):
    # BUG: should be a - b
    return a + b
