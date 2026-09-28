"""Benchmarks for Roborock V1 and Q10 map parsing and rendering.

Can be run via pytest:
    uv run pytest tests/map/test_benchmarks.py
    uv run pytest tests/map/test_benchmarks.py --codspeed

Or directly as a standalone profiling CLI:
    uv run python -m tests.map.test_benchmarks
    uv run python -m tests.map.test_benchmarks --iterations 20 --profile
"""

import argparse
import cProfile
import io
import pstats
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    Q10MapPacket,
    Q10MapPacketKind,
    Q10Room,
    parse_map_packet,
)
from roborock.map.map_parser import MapParser, MapParserConfig

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture
else:
    try:
        from pytest_codspeed import BenchmarkFixture
    except ImportError:
        BenchmarkFixture = Any

        @pytest.fixture
        def benchmark() -> Callable[..., Any]:
            def _runner(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

            return _runner


_TESTDATA_DIR = Path(__file__).resolve().parent / "testdata"
_V1_S5_MAP = _TESTDATA_DIR / "v1" / "s5_fw2008_with_segments.bin"
_V1_S6_MAP = _TESTDATA_DIR / "v1" / "s6_fw2652_with_active_segment_and_no_mop_zone.bin"
_Q10_MAP = _TESTDATA_DIR / "b01_q10_map.bin"


def _build_synthetic_q10_grid(width: int = 200, height: int = 200) -> Q10MapPacket:
    """Generate a realistic 200x200 4-room Q10 occupancy grid for load benchmarking."""
    grid = bytearray([243] * (width * height))
    for y in range(20, height - 20):
        for x in range(20, width - 20):
            if x == 20 or x == width - 21 or y == 20 or y == height - 21 or x == width // 2 or y == height // 2:
                grid[y * width + x] = 245
            else:
                rx = 0 if x < width // 2 else 1
                ry = 0 if y < height // 2 else 1
                room_id = 1 + ry * 2 + rx
                grid[y * width + x] = room_id * 4

    rooms = [
        Q10Room(
            id=room_id,
            raw_name=f"Room {room_id}",
            pixel_value=room_id * 4,
            pixel_count=grid.count(room_id * 4),
        )
        for room_id in range(1, 5)
    ]
    return Q10MapPacket(
        kind=Q10MapPacketKind.CURRENT,
        map_id=1,
        width=width,
        height=height,
        grid=bytes(grid),
        rooms=rooms,
    )


def test_benchmark_v1_s5_map_parse(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S5 map with 2 rooms."""
    raw_data = _V1_S5_MAP.read_bytes()
    parser = MapParser(MapParserConfig())
    result = benchmark(parser.parse, raw_data)
    assert result is not None
    assert result.image_content is not None


def test_benchmark_v1_s6_map_parse(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S6 map with 6 rooms and active segment."""
    raw_data = _V1_S6_MAP.read_bytes()
    parser = MapParser(MapParserConfig())
    result = benchmark(parser.parse, raw_data)
    assert result is not None
    assert result.image_content is not None


def test_benchmark_q10_map_packet_unpack(benchmark: BenchmarkFixture) -> None:
    """Benchmark Q10 wire packet decompression and metadata decoding."""
    raw_data = _Q10_MAP.read_bytes()
    packet = benchmark(parse_map_packet, raw_data)
    assert packet.width > 0
    assert packet.height > 0


def test_benchmark_q10_map_parse_and_render(benchmark: BenchmarkFixture) -> None:
    """Benchmark end-to-end Q10 small map packet decoding and PNG rendering."""
    raw_data = _Q10_MAP.read_bytes()
    parser = B01Q10MapParser()
    result = benchmark(parser.parse, raw_data)
    assert result.image_content is not None


def test_benchmark_q10_map_full_scale_render(benchmark: BenchmarkFixture) -> None:
    """Benchmark Q10 composite rendering on a realistic 200x200 4-room floorplan."""
    packet = _build_synthetic_q10_grid(200, 200)
    parser = B01Q10MapParser()
    result = benchmark(parser.parse_packet, packet)
    assert result.image_content is not None


# ---------------------------------------------------------------------------
# Standalone CLI Benchmark & Profiler
# ---------------------------------------------------------------------------


def _run_benchmarks(iterations: int, warmup: int, profile: bool) -> None:
    v1_s5_data = _V1_S5_MAP.read_bytes()
    v1_s6_data = _V1_S6_MAP.read_bytes()
    q10_data = _Q10_MAP.read_bytes()
    q10_packet_200 = _build_synthetic_q10_grid(200, 200)

    v1_parser = MapParser(MapParserConfig())
    q10_parser = B01Q10MapParser()

    benchmarks: list[tuple[str, Callable[[], Any]]] = [
        ("V1 S5 Map (Parse & Render)", lambda: v1_parser.parse(v1_s5_data)),
        ("V1 S6 Map (Parse & Render)", lambda: v1_parser.parse(v1_s6_data)),
        ("Q10 Wire Packet (Unpack only)", lambda: parse_map_packet(q10_data)),
        ("Q10 Map (Parse & Render)", lambda: q10_parser.parse(q10_data)),
        ("Q10 200x200 Map (Composite Render)", lambda: q10_parser.parse_packet(q10_packet_200)),
    ]

    print(f"\nRunning {len(benchmarks)} benchmarks ({warmup} warmup, {iterations} timed iterations)...\n")
    results = []

    for name, fn in benchmarks:
        for _ in range(warmup):
            fn()

        timings: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            timings.append((time.perf_counter() - start) * 1000.0)

        timings.sort()
        min_ms = timings[0]
        mean_ms = sum(timings) / len(timings)
        med_ms = timings[len(timings) // 2]
        p95_ms = timings[int(len(timings) * 0.95)]
        ops_per_sec = 1000.0 / mean_ms if mean_ms > 0 else float("inf")

        results.append((name, min_ms, med_ms, mean_ms, p95_ms, ops_per_sec))

        if profile:
            pr = cProfile.Profile()
            pr.enable()
            for _ in range(iterations):
                fn()
            pr.disable()
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
            ps.print_stats(10)
            print(f"--- cProfile Top Hotspots: {name} ---")
            print(s.getvalue())

    header = (
        f"{'Benchmark':<36} | {'Min (ms)':>9} | {'Med (ms)':>9} | {'Mean (ms)':>9} | {'P95 (ms)':>9} | {'Ops/sec':>10}"
    )
    print(header)
    print("-" * len(header))
    for name, min_ms, med_ms, mean_ms, p95_ms, ops in results:
        print(f"{name:<36} | {min_ms:9.3f} | {med_ms:9.3f} | {mean_ms:9.3f} | {p95_ms:9.3f} | {ops:10.1f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Roborock map parser benchmarks")
    parser.add_argument("--iterations", type=int, default=20, help="Number of benchmark iterations (default: 20)")
    parser.add_argument("--warmup", type=int, default=3, help="Number of warmup iterations (default: 3)")
    parser.add_argument("--profile", action="store_true", help="Print cProfile hotspot breakdown for each benchmark")
    args = parser.parse_args()

    _run_benchmarks(iterations=args.iterations, warmup=args.warmup, profile=args.profile)


if __name__ == "__main__":
    main()
