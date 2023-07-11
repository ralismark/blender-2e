#!/usr/bin/env python3

import logging
import contextlib
import random

class LogBlock():
    """
    Logging message with helping stuff
    """
    def __init__(self, fmt, *args, **kwargs):
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return str(self.fmt).format(*self.args, **self.kwargs)

    @contextlib.contextmanager
    def log(self, log, level=logging.INFO):
        """
        Submit self to log
        """
        try:
            yield self
        finally:
            log.log(level, self)

    def set(self, *args, **kwargs):
        """
        Set arguments for format
        """
        self.args += args
        self.kwargs.update(kwargs)

    def append(self, fmt, *args, **kwargs):
        """
        Append a line onto the event
        """
        self.fmt += f"\n         ... {fmt}"
        self.set(*args, **kwargs)

class Reservoir():
    """
    An implementation of reservoir sampling
    """

    def __init__(self, size):
        self.size = size
        self.sample = []
        self.counter = 0

    def add(self, item):
        """
        Sample an item from the reservoir
        """
        self.counter += 1
        if self.counter <= self.size:
            assert len(self.sample) < self.size
            self.sample.append(item)
        else:
            assert len(self.sample) == self.size
            j = random.randrange(0, self.counter)
            if j < self.size:
                self.sample[j] = item
