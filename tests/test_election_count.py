"""Counting ballots: alttprbot/services/election_count.py."""

from collections import defaultdict

import pytest

import testdata
from alttprbot.services import election_count
from alttprbot.services.election_count import APPROVAL, PLURALITY, STV, count


def test_unknown_method_is_refused():
    with pytest.raises(ValueError):
        count("borda", [1, 2], [[1]])


@pytest.mark.parametrize("method", [APPROVAL, PLURALITY])
def test_single_round_methods_pick_the_most_votes(method):
    ballots = [[2], [2], [1], [3]] if method == PLURALITY else [[1, 2], [2], [2, 3], [3]]
    result = count(method, [1, 2, 3], ballots)
    assert result["method"] == method
    assert result["winners"] == [2]
    assert result["tie_broken"] is False
    assert result["quota"] is None
    assert len(result["rounds"]) == 1
    rows = result["rounds"][0]["candidates"]
    assert rows[0] == {"id": 2, "votes": 3.0 if method == APPROVAL else 2.0, "status": "elected"}
    assert [r["status"] for r in rows[1:]] == ["hopeful", "hopeful"]


def test_plurality_counts_only_the_first_choice():
    result = count(PLURALITY, [1, 2], [[1, 2], [1], [2, 1]])
    assert result["winners"] == [1]
    assert {r["id"]: r["votes"] for r in result["rounds"][0]["candidates"]} == {1: 2.0, 2: 1.0}


def test_approval_counts_a_repeated_tick_once():
    result = count(APPROVAL, [1, 2], [[1, 1, 1], [2]])
    assert {r["id"]: r["votes"] for r in result["rounds"][0]["candidates"]} == {1: 1.0, 2: 1.0}


def test_a_tie_at_the_cut_off_goes_to_ballot_order_and_is_flagged():
    result = count(APPROVAL, [3, 1, 2], [[1], [2], [3]], seats=2)
    assert result["winners"] == [3, 1]
    assert result["tie_broken"] is True


def test_multi_seat_approval_without_a_tie():
    result = count(APPROVAL, [1, 2, 3], [[1, 2], [1, 2], [1]], seats=2)
    assert result["winners"] == [1, 2]
    assert result["tie_broken"] is False


def test_unknown_candidates_and_empty_ballots_are_dropped():
    result = count(PLURALITY, [1, 2], [[99], [], [2]])
    assert result["ballots"] == 1
    assert result["winners"] == [2]


def test_seats_are_clamped_to_the_candidates():
    assert count(APPROVAL, [1, 2], [[1]], seats=5)["seats"] == 2
    assert count(APPROVAL, [1, 2], [[1]], seats=0)["seats"] == 1


def test_stv_with_no_ballots_has_no_winners():
    result = count(STV, [1, 2], [])
    assert result == {"method": STV, "seats": 1, "ballots": 0, "quota": None, "rounds": [], "winners": [],
                      "tie_broken": False}


def test_stv_majority_wins_in_one_round():
    result = count(STV, [1, 2], [[1], [1], [2]])
    assert result["winners"] == [1]
    assert result["quota"] == 1.5
    assert result["rounds"][-1]["candidates"][0] == {"id": 1, "votes": 2.0, "status": "elected"}
    assert result["tie_broken"] is False


def test_stv_transfers_votes_and_records_every_round():
    ballots = [[1, 2], [1, 3], [1, 2], [2, 1], [3, 2], [3], [4, 3], [2, 3], [1, 4]]
    result = count(STV, [1, 2, 3, 4], ballots, seats=2, seed=5)
    assert result["ballots"] == 9
    assert result["quota"] == 3.0
    assert result["winners"] == [1, 3]
    assert len(result["rounds"]) == 3
    statuses = [{r["id"]: r["status"] for r in rnd["candidates"]} for rnd in result["rounds"]]
    assert statuses[0][1] == "elected"
    assert statuses[1][4] == "eliminated"
    assert all("exhausted" in rnd for rnd in result["rounds"])


def test_stv_tie_break_is_repeatable_and_flagged():
    first = count(STV, [1, 2], [[1], [2]], seed=7)
    assert first["tie_broken"] is True
    assert count(STV, [1, 2], [[1], [2]], seed=7)["winners"] == first["winners"]


def test_stv_puts_pyrankvote_random_back():
    import pyrankvote.helpers as helpers
    before = helpers.random
    count(STV, [1, 2], [[1], [2]], seed=1)
    assert helpers.random is before


def test_recounting_production_shaped_elections_matches_their_winners():
    """Every finished fixture election (copied from production, anonymized) gets the
    same winners from the new count as it did when it closed."""
    candidates = defaultdict(list)
    for c in testdata.rows("ranked_choice", "RankedChoiceCandidate"):
        candidates[c["election_id"]].append(c)
    ballots = defaultdict(lambda: defaultdict(list))
    for v in sorted(testdata.rows("ranked_choice", "RankedChoiceVotes"), key=lambda v: v["rank"]):
        ballots[v["election_id"]][v["user_id"]].append(v["candidate_id"])

    checked = 0
    for election in testdata.rows("ranked_choice", "RankedChoiceElection"):
        if election["active"] or not election["results"]:
            continue
        cands = sorted(candidates[election["id"]], key=lambda c: c["id"])
        result = count(STV, [c["id"] for c in cands], list(ballots[election["id"]].values()),
                       seats=election["seats"], seed=election["id"])
        assert set(result["winners"]) == {c["id"] for c in cands if c["winner"]}, election["title"]
        checked += 1
    assert checked >= 3


def test_methods_constant_lists_all_three():
    assert election_count.METHODS == (STV, APPROVAL, PLURALITY)
