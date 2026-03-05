"""Tests for the CPU-based idle/working heuristic."""

import pytest
from companion.heuristic import ClaudeStatus, HeuristicConfig, IdleHeuristic


class FakeClock:
    """Controllable clock for deterministic testing."""

    def __init__(self, start: float = 0.0):
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float):
        self._now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def config():
    return HeuristicConfig(
        cpu_threshold_percent=3.0,
        idle_grace_seconds=5.0,
        poll_interval_seconds=2.0,
    )


@pytest.fixture
def heuristic(config, clock):
    return IdleHeuristic(config=config, time_fn=clock)


class TestProcessNotFound:
    def test_returns_closed_when_no_process(self, heuristic):
        assert heuristic.update(None) == ClaudeStatus.CLOSED

    def test_transitions_from_working_to_closed(self, heuristic, clock):
        heuristic.update(10.0)  # working
        assert heuristic.update(None) == ClaudeStatus.CLOSED

    def test_transitions_from_idle_to_closed(self, heuristic, clock):
        # Get to idle state first
        heuristic.update(0.0)
        clock.advance(6.0)
        assert heuristic.update(0.0) == ClaudeStatus.IDLE
        assert heuristic.update(None) == ClaudeStatus.CLOSED

    def test_repeated_none_stays_closed(self, heuristic):
        heuristic.update(None)
        heuristic.update(None)
        heuristic.update(None)
        assert heuristic.state.current_status == ClaudeStatus.CLOSED


class TestWorkingDetection:
    def test_high_cpu_means_working(self, heuristic):
        assert heuristic.update(10.0) == ClaudeStatus.WORKING

    def test_cpu_at_threshold_means_working(self, heuristic):
        assert heuristic.update(3.0) == ClaudeStatus.WORKING

    def test_sustained_high_cpu_stays_working(self, heuristic, clock):
        for _ in range(10):
            assert heuristic.update(50.0) == ClaudeStatus.WORKING
            clock.advance(2.0)

    def test_very_high_cpu_means_working(self, heuristic):
        assert heuristic.update(200.0) == ClaudeStatus.WORKING  # Multi-core


class TestIdleDetection:
    def test_low_cpu_during_grace_period_maintains_previous(self, heuristic, clock):
        # Initial state is CLOSED, low CPU during grace keeps CLOSED
        assert heuristic.update(0.0) == ClaudeStatus.CLOSED
        clock.advance(2.0)
        assert heuristic.update(0.0) == ClaudeStatus.CLOSED

    def test_low_cpu_after_grace_becomes_idle(self, heuristic, clock):
        heuristic.update(0.0)
        clock.advance(5.0)
        assert heuristic.update(0.0) == ClaudeStatus.IDLE

    def test_working_then_idle_after_grace(self, heuristic, clock):
        heuristic.update(10.0)  # working
        clock.advance(2.0)
        # CPU drops
        heuristic.update(1.0)  # below threshold, start grace
        assert heuristic.state.current_status == ClaudeStatus.WORKING  # still working during grace
        clock.advance(3.0)
        assert heuristic.update(1.0) == ClaudeStatus.WORKING  # only 3s into grace
        clock.advance(3.0)
        assert heuristic.update(1.0) == ClaudeStatus.IDLE  # 6s > 5s grace

    def test_cpu_just_below_threshold_eventually_idles(self, heuristic, clock):
        heuristic.update(2.9)  # just below 3.0
        clock.advance(6.0)
        assert heuristic.update(2.9) == ClaudeStatus.IDLE


class TestGracePeriod:
    def test_spike_during_grace_resets_timer(self, heuristic, clock):
        heuristic.update(10.0)  # working
        clock.advance(2.0)
        heuristic.update(1.0)  # start grace
        clock.advance(3.0)
        heuristic.update(1.0)  # still in grace (3s < 5s)
        assert heuristic.state.current_status == ClaudeStatus.WORKING

        # CPU spikes — should reset grace timer
        heuristic.update(10.0)
        assert heuristic.state.current_status == ClaudeStatus.WORKING
        assert heuristic.state.idle_since is None  # timer reset

        # Drop again — grace period starts fresh
        clock.advance(1.0)
        heuristic.update(1.0)
        clock.advance(4.0)
        assert heuristic.update(1.0) == ClaudeStatus.WORKING  # only 4s < 5s grace
        clock.advance(2.0)
        assert heuristic.update(1.0) == ClaudeStatus.IDLE  # 6s > 5s grace

    def test_brief_spike_then_drop_prevents_premature_idle(self, heuristic, clock):
        # Simulate: working -> brief dip -> working -> sustained dip -> idle
        heuristic.update(20.0)
        clock.advance(2.0)
        heuristic.update(1.0)  # dip
        clock.advance(1.0)
        heuristic.update(15.0)  # back to working
        clock.advance(2.0)
        heuristic.update(0.5)  # sustained dip begins
        clock.advance(4.0)
        assert heuristic.update(0.5) == ClaudeStatus.WORKING  # 4s < 5s
        clock.advance(2.0)
        assert heuristic.update(0.5) == ClaudeStatus.IDLE  # 6s > 5s

    def test_zero_grace_period_transitions_immediately(self):
        clock = FakeClock()
        config = HeuristicConfig(cpu_threshold_percent=3.0, idle_grace_seconds=0.0)
        h = IdleHeuristic(config=config, time_fn=clock)
        h.update(10.0)  # working
        assert h.update(0.0) == ClaudeStatus.IDLE  # immediate

    def test_exact_grace_boundary(self, heuristic, clock):
        heuristic.update(10.0)  # working
        clock.advance(2.0)
        heuristic.update(0.0)  # start grace at t=2
        clock.advance(5.0)  # exactly at grace boundary (t=7, 5s elapsed)
        assert heuristic.update(0.0) == ClaudeStatus.IDLE


class TestTransitions:
    def test_closed_to_working(self, heuristic):
        assert heuristic.state.current_status == ClaudeStatus.CLOSED
        assert heuristic.update(10.0) == ClaudeStatus.WORKING

    def test_idle_to_working(self, heuristic, clock):
        heuristic.update(0.0)
        clock.advance(6.0)
        assert heuristic.update(0.0) == ClaudeStatus.IDLE
        assert heuristic.update(10.0) == ClaudeStatus.WORKING

    def test_working_to_closed(self, heuristic):
        heuristic.update(10.0)
        assert heuristic.update(None) == ClaudeStatus.CLOSED

    def test_full_lifecycle(self, heuristic, clock):
        # Closed -> Working -> Idle -> Working -> Closed
        assert heuristic.state.current_status == ClaudeStatus.CLOSED

        assert heuristic.update(20.0) == ClaudeStatus.WORKING
        clock.advance(10.0)
        assert heuristic.update(15.0) == ClaudeStatus.WORKING

        clock.advance(2.0)
        heuristic.update(0.5)  # grace starts
        clock.advance(6.0)
        assert heuristic.update(0.5) == ClaudeStatus.IDLE

        assert heuristic.update(30.0) == ClaudeStatus.WORKING
        assert heuristic.update(None) == ClaudeStatus.CLOSED


class TestSampleTracking:
    def test_samples_are_recorded(self, heuristic, clock):
        for cpu in [10.0, 20.0, 0.5, 1.0]:
            heuristic.update(cpu)
            clock.advance(2.0)
        assert heuristic.state.recent_cpu_samples == [10.0, 20.0, 0.5, 1.0]

    def test_samples_capped_at_max(self, heuristic, clock):
        for i in range(50):
            heuristic.update(float(i))
            clock.advance(1.0)
        assert len(heuristic.state.recent_cpu_samples) == 30
        assert heuristic.state.recent_cpu_samples[0] == 20.0  # oldest kept

    def test_none_does_not_add_sample(self, heuristic):
        heuristic.update(None)
        assert heuristic.state.recent_cpu_samples == []
