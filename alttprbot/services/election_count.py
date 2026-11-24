"""Counting an election's ballots, one function per voting method.

Pure functions: ballots in, a count out, no database. The count is plain JSON-able
data that ``elections.close`` stores on the election and the results page draws:

    {
        "method": "stv",
        "seats": 3,
        "ballots": 42,            # ballots counted (blank ones left out)
        "quota": 10.5,            # votes a candidate needs to win (STV only, else None)
        "rounds": [               # one entry per round; approval and plurality have one
            {"candidates": [{"id": 1, "votes": 15.0, "status": "elected"}, ...],
             "exhausted": 0.0},   # votes whose ballots ran out of candidates
        ],
        "winners": [1, 4, 2],     # candidate ids, in the order they won
        "tie_broken": False,      # approval/plurality: a tie at the cut-off went to ballot
                                  # order. STV: a seeded draw ordered tied candidates.
    }

A ballot is a list of candidate ids. For STV it's the voter's ranking, favourite
first; for approval every candidate the voter ticked; for plurality the one they
picked.
"""

import random
from collections import Counter
from typing import Sequence

import pyrankvote
import pyrankvote.helpers as pyrankvote_helpers
from pyrankvote.helpers import CandidateStatus

STV = "stv"
APPROVAL = "approval"
PLURALITY = "plurality"
METHODS = (STV, APPROVAL, PLURALITY)

_STATUS = {
    CandidateStatus.Elected: "elected",
    CandidateStatus.Hopeful: "hopeful",
    CandidateStatus.Rejected: "eliminated",
}


class _TieBreaker:
    """Stands in for pyrankvote's ``random`` module: seeded, and remembers being used."""

    def __init__(self, seed: int):
        self._random = random.Random(seed)
        self.used = False

    def choice(self, seq):
        self.used = True
        return self._random.choice(seq)


def count(method: str, candidate_ids: Sequence[int], ballots: Sequence[Sequence[int]], seats: int = 1,
          seed: int = 0) -> dict:
    """Count ``ballots`` for ``candidate_ids`` (in ballot order) by ``method``.

    ``seed`` makes STV's last-resort random tie-break repeatable, so recounting the
    same election always gives the same answer; pass the election id.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown voting method {method!r}")
    seats = max(1, min(seats, len(candidate_ids)))
    known = set(candidate_ids)
    # Unknown candidates and repeats are dropped; a ballot left empty isn't counted.
    cleaned = [list(dict.fromkeys(c for c in ballot if c in known)) for ballot in ballots]
    cleaned = [b for b in cleaned if b]
    if method == STV:
        return _stv(list(candidate_ids), cleaned, seats, seed)
    if method == PLURALITY:
        cleaned = [b[:1] for b in cleaned]
    return _tally(method, list(candidate_ids), cleaned, seats)


def _tally(method: str, candidate_ids: list[int], ballots: list[list[int]], seats: int) -> dict:
    """Approval and plurality: one round, most votes win, ties go to ballot order."""
    totals = Counter(c for ballot in ballots for c in set(ballot))
    position = {cid: i for i, cid in enumerate(candidate_ids)}
    ranked = sorted(candidate_ids, key=lambda c: (-totals[c], position[c]))
    winners = ranked[:seats]
    # A tie decided it when the last winner and the first loser have the same total.
    tie_broken = len(ranked) > seats and totals[ranked[seats - 1]] == totals[ranked[seats]]
    return {
        "method": method,
        "seats": seats,
        "ballots": len(ballots),
        "quota": None,
        "rounds": [{
            "candidates": [
                {"id": c, "votes": float(totals[c]), "status": "elected" if c in winners else "hopeful"}
                for c in ranked
            ],
            "exhausted": 0.0,
        }],
        "winners": winners,
        "tie_broken": bool(tie_broken),
    }


def _stv(candidate_ids: list[int], ballots: list[list[int]], seats: int, seed: int) -> dict:
    """Single transferable vote with the Droop quota (pyrankvote). With one seat it's
    instant runoff."""
    candidates = {cid: pyrankvote.Candidate(str(cid)) for cid in candidate_ids}
    if not ballots:
        return {"method": STV, "seats": seats, "ballots": 0, "quota": None, "rounds": [], "winners": [],
                "tie_broken": False}

    rng = _TieBreaker(seed)
    # pyrankvote breaks a tie by later preferences, then at random through its
    # module's ``random``. Swap in a seeded one so a recount always matches, and
    # notice when it was needed.
    real = pyrankvote_helpers.random
    pyrankvote_helpers.random = rng
    try:
        result = pyrankvote.single_transferable_vote(
            candidates=list(candidates.values()),
            ballots=[pyrankvote.Ballot(ranked_candidates=[candidates[c] for c in b]) for b in ballots],
            number_of_seats=seats,
        )
    finally:
        pyrankvote_helpers.random = real
    tie_broken = rng.used

    rounds = []
    winners: list[int] = []
    for round_ in result.rounds:
        rows = []
        for cr in round_.candidate_results:
            cid = int(cr.candidate.name)
            status = _STATUS[cr.status]
            rows.append({"id": cid, "votes": round(float(cr.number_of_votes), 4), "status": status})
            if status == "elected" and cid not in winners:
                winners.append(cid)
        rounds.append({"candidates": rows, "exhausted": round(float(round_.number_of_blank_votes), 4)})

    return {
        "method": STV,
        "seats": seats,
        "ballots": len(ballots),
        "quota": round(len(ballots) / (seats + 1), 4),
        "rounds": rounds,
        "winners": winners,
        "tie_broken": tie_broken,
    }
