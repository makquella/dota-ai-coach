"""«Перевірити виправлення на записі»: every role case of scripts/replay_check.py
replays a sanitized match through the whole live path and must show the same
advice at the same moments as its accepted result in tests/replay_golden/.

A deliberate change of live behavior updates them with
`python scripts/replay_check.py --update` and the diff is reviewed in the PR;
`--text` prints each card's wording to see what changed."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import replay_check  # noqa: E402


@pytest.mark.parametrize("name", sorted(replay_check.CASES))
def test_role_case_matches_its_accepted_result(name):
    expected = replay_check.load_golden(name)
    assert expected is not None, (
        f"no accepted result: python scripts/replay_check.py --case {name} --update"
    )
    changes = replay_check.diff(expected, replay_check.run(name))
    assert not changes, (
        f"{name} changed:\n"
        + "\n".join(changes)
        + f"\nreproduce: python scripts/replay_check.py --case {name} --text"
    )


def test_every_role_has_a_case_and_every_case_shows_advice():
    roles = {case.role for case in replay_check.CASES.values()}
    assert roles == {"carry", "mid", "offlane", "support"}
    for name in replay_check.CASES:
        cards = replay_check.load_golden(name) or []
        assert any(not line.endswith(" hint") for line in cards), name
        assert any(line.endswith(" hint") for line in cards), name


def test_the_diff_names_added_and_removed_cards():
    expected = ["01:00 SAFE_FARMING coaching", "05:01 DEATH_REVIEW status"]
    actual = ["01:00 SAFE_FARMING coaching", "05:01 REPEATED_DEATH_PATTERN coaching"]
    assert replay_check.diff(expected, actual) == [
        "-05:01 DEATH_REVIEW status",
        "+05:01 REPEATED_DEATH_PATTERN coaching",
    ]
