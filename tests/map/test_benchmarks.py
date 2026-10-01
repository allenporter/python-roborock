"""Benchmarks for Roborock V1 and Q10 map parsing and rendering.

Includes permutations for:
- Different scaling values (scale 1, 2, 4)
- Drawable overlay variations (none, default, all)
- Real V1 S5 and S6 map payloads
- Q10 wire unpack and multi-room composite rendering
- Pixel output validation (dimensions, format, bounding box)

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
import math
import pstats
import statistics
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from PIL import Image
from vacuum_map_parser_base.config.drawable import Drawable

from roborock.map.b01_q10_map_parser import (
    B01Q10MapParser,
    B01Q10MapParserConfig,
    Q10HeaderCalibration,
    Q10MapPacket,
    Q10MapPacketKind,
    Q10Point,
    Q10Room,
    Q10TracePacket,
    parse_map_packet,
)
from roborock.map.b01_q10_overlays import Q10Zone
from roborock.map.b01_q10_render import Q10MapOverlays, render_q10_map
from roborock.map.map_parser import MapParser, MapParserConfig, ParsedMapData

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture
else:
    try:
        from pytest_benchmark.fixture import BenchmarkFixture
    except ImportError:
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


def _validate_image(
    result: ParsedMapData | None,
    expected_size: tuple[int, int] | None = None,
) -> None:
    """Validate rendered PNG image integrity and pixel bounds outside the timed benchmark."""
    assert result is not None
    assert result.image_content is not None
    assert len(result.image_content) > 0
    image = Image.open(io.BytesIO(result.image_content))
    assert image.format == "PNG"
    assert image.mode == "RGBA"
    assert image.getbbox() is not None  # Image has non-empty drawn content
    if expected_size is not None:
        assert image.size == expected_size


# ---------------------------------------------------------------------------
# V1 Map Benchmarks
# ---------------------------------------------------------------------------


def test_benchmark_v1_s5_map_parse(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S5 map with 2 rooms (default scale 4)."""
    raw_data = _V1_S5_MAP.read_bytes()
    parser = MapParser(MapParserConfig())
    result = benchmark(parser.parse, raw_data)
    _validate_image(result, (1024, 964))


def test_benchmark_v1_s6_map_scale_4_default(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S6 map at default scale 4 (1644x1344 px)."""
    raw_data = _V1_S6_MAP.read_bytes()
    parser = MapParser(MapParserConfig(map_scale=4))
    result = benchmark(parser.parse, raw_data)
    _validate_image(result, (1644, 1344))


def test_benchmark_v1_s6_map_scale_2(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S6 map at scale 2 (822x672 px)."""
    raw_data = _V1_S6_MAP.read_bytes()
    parser = MapParser(MapParserConfig(map_scale=2))
    result = benchmark(parser.parse, raw_data)
    _validate_image(result, (822, 672))


def test_benchmark_v1_s6_map_scale_1(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S6 map at scale 1 (411x336 px)."""
    raw_data = _V1_S6_MAP.read_bytes()
    parser = MapParser(MapParserConfig(map_scale=1))
    result = benchmark(parser.parse, raw_data)
    _validate_image(result, (411, 336))


def test_benchmark_v1_s6_map_no_drawables(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S6 map with all drawables disabled."""
    raw_data = _V1_S6_MAP.read_bytes()
    parser = MapParser(MapParserConfig(map_scale=4, drawables=[]))
    result = benchmark(parser.parse, raw_data)
    _validate_image(result, (1644, 1344))


def test_benchmark_v1_s6_map_all_drawables(benchmark: BenchmarkFixture) -> None:
    """Benchmark parsing a real Roborock V1 S6 map with all available drawables enabled."""
    raw_data = _V1_S6_MAP.read_bytes()
    parser = MapParser(MapParserConfig(map_scale=4, drawables=list(Drawable)))
    result = benchmark(parser.parse, raw_data)
    _validate_image(result, (1644, 1344))


# ---------------------------------------------------------------------------
# Q10 Map Benchmarks
# ---------------------------------------------------------------------------


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
    _validate_image(result, (32, 24))


def test_benchmark_q10_map_full_scale_render_scale_1(benchmark: BenchmarkFixture) -> None:
    """Benchmark Q10 base rendering on a realistic 200x200 4-room floorplan at scale 1."""
    packet = _build_synthetic_q10_grid(200, 200)
    parser = B01Q10MapParser(B01Q10MapParserConfig(map_scale=1))
    result = benchmark(parser.parse_packet, packet)
    _validate_image(result, (200, 200))


def test_benchmark_q10_map_full_scale_render_scale_4(benchmark: BenchmarkFixture) -> None:
    """Benchmark Q10 base rendering on a realistic 200x200 4-room floorplan at scale 4."""
    packet = _build_synthetic_q10_grid(200, 200)
    parser = B01Q10MapParser(B01Q10MapParserConfig(map_scale=4))
    result = benchmark(parser.parse_packet, packet)
    _validate_image(result, (800, 800))


def _composite_inputs() -> tuple[Q10MapPacket, Q10TracePacket, Q10MapOverlays]:
    """Build calibrated map, trace and restriction inputs outside timed sections."""
    packet = replace(
        _build_synthetic_q10_grid(),
        header_calibration=Q10HeaderCalibration(0, 2000, 5, 400, 400, 90),
    )
    trace = Q10TracePacket(
        points=[Q10Point(x * 20, (200 - y) * 20) for x, y in [(30, 30), (80, 30), (80, 80), (30, 80), (30, 40)]]
    )
    overlays = Q10MapOverlays(zones=[Q10Zone(type=0, vertices=[(400, 1400), (600, 1400), (600, 1200), (400, 1200)])])
    return packet, trace, overlays


@pytest.mark.parametrize("scale", [1, 4])
def test_benchmark_q10_composite_render(benchmark: BenchmarkFixture, scale: int) -> None:
    """Exercise trace, charger and restriction composition before PNG encoding."""
    packet, trace, overlays = _composite_inputs()
    config = B01Q10MapParserConfig(map_scale=scale)
    content = benchmark(render_q10_map, packet, trace, overlays, config=config)
    with Image.open(io.BytesIO(content)) as image:
        assert image.format == "PNG"
        assert image.size == (200 * scale, 200 * scale)
        with Image.open(io.BytesIO(render_q10_map(packet, None, Q10MapOverlays(), config=config))) as base:
            assert image.tobytes() != base.tobytes()


# ---------------------------------------------------------------------------
# Standalone CLI Benchmark & Profiler
# ---------------------------------------------------------------------------


def _run_benchmarks(iterations: int, warmup: int, profile: bool) -> None:
    if iterations < 1 or warmup < 0:
        raise ValueError("iterations must be positive and warmup must be non-negative")
    packet, trace, overlays = _composite_inputs()
    v1_s5_data = _V1_S5_MAP.read_bytes()
    v1_s6_data = _V1_S6_MAP.read_bytes()
    q10_data = _Q10_MAP.read_bytes()
    q10_packet_200 = _build_synthetic_q10_grid(200, 200)

    p_v1_s5 = MapParser(MapParserConfig())
    p_v1_s6_scale4 = MapParser(MapParserConfig(map_scale=4))
    p_v1_s6_scale2 = MapParser(MapParserConfig(map_scale=2))
    p_v1_s6_scale1 = MapParser(MapParserConfig(map_scale=1))
    p_v1_s6_no_draw = MapParser(MapParserConfig(map_scale=4, drawables=[]))
    p_v1_s6_all_draw = MapParser(MapParserConfig(map_scale=4, drawables=list(Drawable)))

    config_scale1 = B01Q10MapParserConfig(map_scale=1)
    config_scale4 = B01Q10MapParserConfig(map_scale=4)
    p_q10_small = B01Q10MapParser()
    p_q10_scale1 = B01Q10MapParser(B01Q10MapParserConfig(map_scale=1))
    p_q10_scale4 = B01Q10MapParser(B01Q10MapParserConfig(map_scale=4))

    benchmarks: list[tuple[str, Callable[[], Any]]] = [
        ("V1 S5 Map (Scale 4, Default)", lambda: p_v1_s5.parse(v1_s5_data)),
        ("V1 S6 Map (Scale 4, Default)", lambda: p_v1_s6_scale4.parse(v1_s6_data)),
        ("V1 S6 Map (Scale 2)", lambda: p_v1_s6_scale2.parse(v1_s6_data)),
        ("V1 S6 Map (Scale 1)", lambda: p_v1_s6_scale1.parse(v1_s6_data)),
        ("V1 S6 Map (No Drawables)", lambda: p_v1_s6_no_draw.parse(v1_s6_data)),
        ("V1 S6 Map (All Drawables)", lambda: p_v1_s6_all_draw.parse(v1_s6_data)),
        ("Q10 Wire Packet (Unpack only)", lambda: parse_map_packet(q10_data)),
        ("Q10 Small Map (Scale 1)", lambda: p_q10_small.parse(q10_data)),
        ("Q10 200x200 Map (Scale 1)", lambda: p_q10_scale1.parse_packet(q10_packet_200)),
        ("Q10 200x200 Map (Scale 4)", lambda: p_q10_scale4.parse_packet(q10_packet_200)),
        (
            "Q10 Composite (Scale 1)",
            lambda: render_q10_map(packet, trace, overlays, config=config_scale1),
        ),
        (
            "Q10 Composite (Scale 4)",
            lambda: render_q10_map(packet, trace, overlays, config=config_scale4),
        ),
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
        med_ms = statistics.median(timings)
        p95_ms = timings[math.ceil(len(timings) * 0.95) - 1]  # Nearest-rank percentile (one-based).
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

    if args.iterations < 1 or args.warmup < 0:
        parser.error("--iterations must be positive and --warmup must be non-negative")

    _run_benchmarks(iterations=args.iterations, warmup=args.warmup, profile=args.profile)


@pytest.mark.parametrize("iterations,warmup", [(0, 0), (-1, 0), (1, -1)])
def test_cli_rejects_invalid_counts(iterations: int, warmup: int) -> None:
    """Invalid counts fail before loading fixtures or running benchmarks."""
    with pytest.raises(ValueError, match="iterations must be positive"):
        _run_benchmarks(iterations, warmup, False)


def test_cli_reports_nearest_rank_p95_and_median(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Twenty samples report the nineteenth rank as P95 and average the middle pair."""
    monkeypatch.setattr(MapParser, "parse", lambda *args: None)
    monkeypatch.setattr(B01Q10MapParser, "parse", lambda *args: None)
    monkeypatch.setattr(B01Q10MapParser, "parse_packet", lambda *args: None)
    monkeypatch.setattr("tests.map.test_benchmarks.parse_map_packet", lambda *args: None)
    monkeypatch.setattr("tests.map.test_benchmarks.render_q10_map", lambda *args, **kwargs: b"")
    clock = iter(value for _ in range(12) for rank in range(1, 21) for value in (0.0, rank / 1000))
    monkeypatch.setattr(time, "perf_counter", lambda: next(clock))
    _run_benchmarks(iterations=20, warmup=0, profile=False)
    rows = [line.split("|") for line in capsys.readouterr().out.splitlines() if "|" in line][1:]
    assert len(rows) == 12
    for row in rows:
        assert float(row[2]) == 10.5
        assert float(row[4]) == 19.0


if __name__ == "__main__":
    main()
