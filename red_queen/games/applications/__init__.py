# ------------------------------------------------------------------------------
# Part of Red Queen Project.  This file is distributed under the MIT License.
# See accompanying file /LICENSE for details.
# ------------------------------------------------------------------------------

"""Benchmarks of application circuits."""
import pytest

from qiskit.compiler import transpile
from qiskit.result import marginal_distribution
from qiskit.providers.fake_provider import (
    FakeWashington,
    FakeBrooklyn,
    FakeRochester,
    FakeMontreal,
    FakeCairo,
    FakeToronto,
    FakeGuadalupe,
    FakeMelbourne,
)
from qiskit.quantum_info.analysis import hellinger_fidelity

backends = [
    FakeWashington(),
    FakeBrooklyn(),
    FakeRochester(),
    FakeMontreal(),
    FakeCairo(),
    FakeToronto(),
    FakeGuadalupe(),
    FakeMelbourne(),
]


def run_qiskit_circuit(
    benchmark, circuit, backend, optimization_level, shots, expected_counts, marginalize=None
):
    import qiskit
    benchmark.tool_version = qiskit.__version__

    def _evaluate_quality_metrics(tqc):
        from math
        quality_stats = {}
        quality_stats["depth"] = tqc.depth()
        quality_stats["size"] = tqc.size()
        quality_stats["num_2q"] = sum(1 for inst, qargs, cargs in tqc.data if len(qargs) == 2)
        quality_stats["num_1q"] = sum(1 for inst, qargs, cargs in tqc.data if len(qargs) == 1)
        quality_stats["xi"] = quality_stats["num_2q"] / (quality_stats["num_1q"] + quality_stats["num_2q"])

        if marginalize:
            counts = marginal_distribution(
                backend.run(tqc, shots=shots, seed_simulator=123456789).result().get_counts(),
                marginalize,
            )
        else:
            counts = backend.run(tqc, shots=shots, seed_simulator=123456789).result().get_counts()

        quality_stats["fidelity"] = hellinger_fidelity(counts, expected_counts)

        # from math import exp
        # stqc = transpile(tqc, backend, optimization_level=0, scheduling_method='alap')
        # quality_stats["eps"] = reduce(operator.mul, (
        #     1-backend.properties().gate_error(name, qargs) if name != 'delay'
        #     else (exp(-1 * instr.duration * backend.confiruation().dt / be.properties().t1(qars[0]))
        #           *exp(-1 * instr.duration * backend.confiruation().dt / be.properties().t2(qargs[0]))
        #           ) if (op_start_time != 0 and op_start_time + instr.duration < stqc.duration)
        #     else 1
        #     for ((instr, qargs, cargs), op_start_time) in zip(stqc.data, stqc.op_start_times)
        # ))
        return quality_stats

    info, tqc = benchmark(
        _evaluate_quality_metrics,
        transpile,
        circuit,
        backend,
        optimization_level=optimization_level,
        seed_transpiler=4242424242,
    )
