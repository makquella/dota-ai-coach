"""Large-history reads (scripts/bench_history.py): every list order of the match
table is served by an index, never by a temporary sort over the history, and
the profile reads only the columns it needs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import bench_history  # noqa: E402


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    store = bench_history.build(tmp_path_factory.mktemp("history"), 300)
    yield store
    store.close()


@pytest.mark.parametrize("name", sorted(bench_history.PLANS))
def test_list_orders_use_an_index_without_a_temporary_sort(store, name):
    sql, params = bench_history.PLANS[name]
    steps = bench_history.plan(store, sql, params)
    assert any("USING" in step and "INDEX" in step for step in steps), steps
    assert not any("TEMP B-TREE" in step for step in steps), steps


def test_profile_rows_carry_only_what_the_profile_reads(store):
    rows = store.profile_rows(bench_history.ACCOUNT, limit=5000)
    assert len(rows) == 300
    assert set(rows[0]) == {*store.PROFILE_COLUMNS, "has_analysis"}
    assert rows[0]["has_analysis"] is True and isinstance(rows[0]["sources"], list)
    starts = [row["start_time"] for row in rows]
    assert starts == sorted(starts, reverse=True)
    # The same rows, in the same order, as the full match table read.
    full = store.list_matches(bench_history.ACCOUNT, limit=5000)
    assert [row["match_id"] for row in rows] == [row["match_id"] for row in full]
