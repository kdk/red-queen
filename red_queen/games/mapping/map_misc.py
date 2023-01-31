# ------------------------------------------------------------------------------
# Part of Red Queen Project.  This file is distributed under the MIT License.
# See accompanying file /LICENSE for details.
# ------------------------------------------------------------------------------

"""Misc mapping benchmarks."""

import pytest
from qiskit.providers.fake_provider import FakeProvider

from mapping import run_qiskit_mapper, run_tweedledum_mapper, run_tket_mapper
from .benchmarks import misc_qasm


backends = []
provider = FakeProvider()
for name in (
    'fake_sherbrooke',  # Eagle r3
    'fake_washington',  # Eagle r1
    'fake_ithaca',      # Hummingbird r3
    'fake_brooklyn',    # Hummingbird r2
    'fake_montreal',    # Falcon r4
    # 'fake_toronto',    # Falcon r4
    'fake_lima',        # Falcon r4T
    'fake_guadalupe',   # Falcon r4P
    'fake_geneva',      # Falcon r8
    'fake_mumbai',      # Falcon r5.10 # KDK bug, this is listed in the backend as r5.1
    'fake_manila',      # Falcon r5.11L
    'fake_jakarta',     # Falcon r5.11H
    'fake_cairo',       # Falcon r5.11
):
    try:
        be = provider.get_backend(name)
        backends.append(be)
    except:
        pass

@pytest.mark.qiskit
@pytest.mark.parametrize("layout_routing_method", [("sabre", "sabre"), ("dense", "stochastic")])
@pytest.mark.parametrize("backend", backends)
@pytest.mark.parametrize("qasm", misc_qasm)
def bench_qiskit(benchmark, layout_routing_method, backend, qasm) -> None:
    layout_method, routing_method = layout_routing_method
    benchmark.name = qasm.name
    processor_type = backend.configuration().processor_type
    benchmark.algorithm = f"{layout_method}/{routing_method}"
    benchmark.hardware_description = (
        f"{backend.name()} "
        f"({backend.configuration().num_qubits}Q {processor_type['family']} {processor_type['revision']}{processor_type.get('segment', '')})"
    )
    run_qiskit_mapper(
        benchmark,
        layout_method,
        routing_method,
        backend.configuration().coupling_map,
        qasm,
    )

@pytest.mark.tweedledum
@pytest.mark.parametrize("routing_method", ["jit", "sabre"])
@pytest.mark.parametrize("backend", backends)
@pytest.mark.parametrize("qasm", misc_qasm)
def bench_tweedledum(benchmark, routing_method, backend, qasm) -> None:
    benchmark.name = qasm.name
    processor_type = backend.configuration().processor_type
    benchmark.algorithm = f"{routing_method}"
    benchmark.hardware_description = (
        f"{backend.name()} "
        f"({backend.configuration().num_qubits}Q {processor_type['family']} {processor_type['revision']}{processor_type.get('segment', '')})"
    )
    run_tweedledum_mapper(benchmark, routing_method, backend.configuration().coupling_map, qasm)

@pytest.mark.tket
@pytest.mark.parametrize("layout_method", ["graph", "line"])
@pytest.mark.parametrize("backend", backends)
@pytest.mark.parametrize("qasm", misc_qasm)
def bench_tket(benchmark, layout_method, backend, qasm) -> None:
    benchmark.name = qasm.name
    processor_type = backend.configuration().processor_type
    # benchmark.algorithm = f"{layout_method} Placement + Routing "
    benchmark.algorithm = f"{layout_method}"
    benchmark.hardware_description = (
        f"{backend.name()} "
        f"({backend.configuration().num_qubits}Q {processor_type['family']} {processor_type['revision']}{processor_type.get('segment', '')})"
    )
    coupling_map = backend.configuration().coupling_map
    run_tket_mapper(benchmark, layout_method, coupling_map, qasm)
