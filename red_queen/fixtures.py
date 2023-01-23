# ------------------------------------------------------------------------------
# Part of Qiskit.  This file is distributed under the Apache 2.0 License.
# See accompanying file /LICENSE for details.
# ------------------------------------------------------------------------------

"""Benchmark fixtures."""


import sys
import gc
import statistics

from functools import cached_property
from math import ceil
from timeit import default_timer


class BenchmarkInfo:
    """Benchmark information."""

    def _tool_name(self, fullname):
        index = fullname.find("[")
        name = fullname[:index]
        name = name.split("_")[1]
        return name

    def __init__(self, node):
        self._id = node._nodeid
        self.name = None
        self.tool = self._tool_name(node.name)
        self.algorithm = "default"
        self.hardware_description = None
        self._time_data = []
        self.quality_stats = defaultdict(list)

    def update(self, duration, quality_stat):
        self._time_data.append(duration)
        for k, v in quality_stat.items():
            self.quality_stats[k].append(v)

    def as_dict(self):
        result = {
            "id": self._id,
            "name": self.name,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "algorithm": self.algorithm,
            "stats": {
                "timings": self._time_data, #dict((field, getattr(self, field)) for field in self._fields()),
                "quality": self.quality_stats,
            },
        }
        return result

    @staticmethod
    def _fields():
        return ["min", "max", "mean", "rounds"]

    @cached_property
    def min(self):
        return min(self._time_data)

    @cached_property
    def max(self):
        return max(self._time_data)

    @cached_property
    def mean(self):
        return statistics.mean(self._time_data)

    @cached_property
    def rounds(self):
        return len(self._time_data)


class BenchmarkFixture:
    """Benchmark fixture."""

    def __init__(self, node):
        self.info = BenchmarkInfo(node)
        # TODO: make configurable
        self._disable_gc = True
        self._min_time = 5e-06
        self._max_time = 1.0

    @property
    def name(self):
        return self.info.name

    @name.setter
    def name(self, value):
        self.info.name = value

    @property
    def algorithm(self):
        return self.info.algorithm

    @algorithm.setter
    def algorithm(self, value):
        self.info.algorithm = value

    @property
    def tool_version(self):
        return self.info.tool_version

    @tool_version.setter
    def tool_version(self, value):
        self.info.tool_version = value

    def _make_runner(self, function_to_benchmark, args, kwargs):
        def runner(num_runs):
            gc_enabled = gc.isenabled()
            if self._disable_gc:
                gc.disable()
            tracer = sys.gettrace()
            sys.settrace(None)
            try:
                if num_runs:
                    r = range(num_runs)
                    start = default_timer()
                    results = [function_to_benchmark(*args, **kwargs)
                               for _ in r]
                    end = default_timer()
                    return end - start, results
                else:
                    start = default_timer()
                    result = function_to_benchmark(*args, **kwargs)
                    end = default_timer()
                    return end - start, result
            finally:
                sys.settrace(tracer)
                if gc_enabled:
                    gc.enable()

        return runner

    def _adjust_num_runs(self, runner):
        # Calculates the number of runs of function to take longer than self._min_time
        num_runs = 1
        while True:
            warmup_start = default_timer()
            while default_timer() - warmup_start < self._max_time:
                runner(num_runs)

            duration, _ = runner(num_runs)
            if duration >= self._min_time:
                break
            if duration >= (self._min_time / 2):
                num_runs = int(ceil(self._min_time * num_runs / duration))
                if num_runs == 1:
                    break
            else:
                num_runs *= 10
        return duration, num_runs

    def __call__(self, quality_gauge, function_to_benchmark, *args, **kwargs):
        runner = self._make_runner(function_to_benchmark, args, kwargs)
        duration, result = runner(None)

        # If single run takes longer than _max_time, but less than 5 min, run 5 times.
        # If single run takes longer than 5 min, run once,
        # Otherwise, call adjust_num_runs to find number of rounds required to get above _min_time
        if duration >= self._max_time:
            if duration < 300:
                for _ in range(5):
                    round_duration, result = runner(None)
                    self.info.update(round_duration, quality_gauge(result))
            else:
                self.info.update(duration, quality_gauge(result))
            return self.info, result

        duration, num_runs = self._adjust_num_runs(runner)
        rounds = int(ceil(self._max_time / duration))
        rounds = min(rounds, sys.maxsize)
        for _ in range(rounds):
            round_duration, results = runner(num_runs)
            for result in results:
                self.info.update(round_duration / num_runs, quality_gauge(result))

        return self.info, result
