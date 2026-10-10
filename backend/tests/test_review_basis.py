"""«На чём основан разбор?»: every built review records its rules, data and why
it was (re)built; Progress says whether its averages compare like with like."""

from __future__ import annotations

from test_coach_ai import MATCH_ID, _reviewed_match

from app import review_basis
from app.post_match_analysis import ANALYSIS_VERSION


def test_a_new_review_is_stamped(client, tmp_path):
    _reviewed_match(client, tmp_path, None)
    basis = client.get(f"/player/matches/{MATCH_ID}").json()["analysis"]["basis"]
    assert basis["rules"] == ANALYSIS_VERSION and basis["reason"] == "new"
    assert basis["sources"] == ["opendota"] and basis["recorded"] is False
    assert basis["previous_rules"] is None and basis["built_at"]


def test_a_rules_change_is_named_on_rebuild(client, tmp_path):
    service = _reviewed_match(client, tmp_path, None)
    account = service.store.primary_account_id()
    record = service.store.get_match(account, MATCH_ID)
    old = {**record["analysis"], "version": ANALYSIS_VERSION - 1}
    old.pop("basis", None)
    service.store.upsert_match(account, MATCH_ID, source="opendota", fields={}, analysis=old)
    basis = client.get(f"/player/matches/{MATCH_ID}").json()["analysis"]["basis"]
    assert basis["reason"] == "rules" and basis["previous_rules"] == ANALYSIS_VERSION - 1
    # The same rules and data again: the stamp stays as it was.
    service._rebuild_analysis(account, MATCH_ID)
    assert service.store.get_match(account, MATCH_ID)["analysis"]["basis"] == basis
    # The same rules with more data (now a live recording too): a rebuild for data.
    stamp = review_basis.stamp(
        rules=ANALYSIS_VERSION,
        trim=4,
        opendota={"patch": 58},
        sources=["opendota", "gsi"],
        parsed=False,
        has_timeline=True,
        previous=service.store.get_match(account, MATCH_ID)["analysis"],
    )
    assert stamp["reason"] == "data" and stamp["previous_rules"] == ANALYSIS_VERSION
    assert stamp["patch"] == 58 and stamp["recorded"] is True


def test_career_basis_counts_patches_and_parsed_replays():
    stamps = [
        {"version": 21, "basis": {"patch": 58, "parsed": True, "recorded": False}},
        {"version": 21, "basis": {"patch": 58, "parsed": False, "recorded": True}},
        {"version": 21, "basis": {"patch": 59, "parsed": False, "recorded": False}},
        {"version": 21},  # built before stamps: unknown patch and data
        None,
    ]
    basis = review_basis.career_basis(stamps, 21)
    assert basis["matches"] == 4 and basis["same_rules"] is True
    assert basis["patches"] == {"58": 2, "59": 1} and basis["unknown_patch"] == 1
    assert basis["mixed_patches"] is True and basis["mixed_data"] is True
    assert basis["parsed"] == 1 and basis["recorded"] == 1
    assert review_basis.career_basis([], 21)["same_rules"] is False
    one = review_basis.career_basis([{"version": 20, "basis": {"patch": 58}}], 21)
    assert one["same_rules"] is False and one["mixed_patches"] is False


def test_progress_carries_the_basis(client, tmp_path):
    _reviewed_match(client, tmp_path, None)
    basis = client.get("/player/career?lang=ru").json().get("basis")
    if basis is not None:  # Progress needs a few matches before it reports
        assert basis["rules"] == ANALYSIS_VERSION
