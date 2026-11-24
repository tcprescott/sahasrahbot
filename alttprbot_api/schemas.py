"""Request and response bodies of the web app's JSON API (``/api/v1``).

These are the API's contract with the React app in ``web/``: ``web/src/api/schema.d.ts``
is generated from the OpenAPI schema they produce (``scripts/export_openapi.py``).
Discord ids are strings, because they don't fit in a JavaScript number.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    error: str


class SessionUser(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str] = None


class SessionInfo(BaseModel):
    user: Optional[SessionUser] = None


class BrowserSentry(BaseModel):
    """What the React app hands the Sentry browser SDK."""
    dsn: str
    environment: str
    release: Optional[str] = None
    sample_rate: float = Field(description="Share of browser errors sent, 0 to 1.")
    traces_sample_rate: float = Field(description="Share of page loads and navigations traced, 0 to 1.")
    replay: bool = Field(description="Record a session replay to send with an error.")


class Telemetry(BaseModel):
    sentry: Optional[BrowserSentry] = Field(description="Null when Sentry is off; the app then loads no SDK.")


class Profile(BaseModel):
    user: SessionUser
    racetime_linked: bool
    racetime_id: Optional[str] = None
    preset_namespace: Optional[str] = None
    moderated_triforce_pools: list[str]


class Randomizers(BaseModel):
    randomizers: list[str]


class NamespaceSummary(BaseModel):
    name: str
    preset_count: int


class NamespaceList(BaseModel):
    namespaces: list[NamespaceSummary]


class MyNamespace(BaseModel):
    namespace: str


class PresetSummary(BaseModel):
    namespace: str
    randomizer: str
    name: str
    modified: Optional[datetime] = None
    generated_count: int


class Namespace(BaseModel):
    name: str
    can_edit: bool
    presets: list[PresetSummary]


class Preset(PresetSummary):
    content: str
    can_edit: bool


class PresetContent(BaseModel):
    content: str = Field(max_length=200_000)


class Candidate(BaseModel):
    id: int
    name: str


ElectionMethod = Literal['stv', 'approval', 'plurality']
ElectionStatus = Literal['draft', 'open', 'closed']


class Election(BaseModel):
    """An open election, as a voter sees it."""
    id: int
    title: str
    description: Optional[str] = None
    private: bool
    method: ElectionMethod = 'stv'
    seats: int
    closes_at: Optional[datetime] = None
    guild_name: Optional[str] = None
    candidates: list[Candidate]
    ballot: Optional[list[int]] = Field(default=None, description="The viewer's ballot: candidate ids, most preferred first (approval: every one ticked); null until they vote")
    voted_at: Optional[datetime] = None


class BallotIn(BaseModel):
    ranking: list[int] = Field(description="Candidate ids, most preferred first. Candidates left out are unranked.")


class ElectionBallotIn(BaseModel):
    choices: list[int] = Field(description="Candidate ids: the ranking, most preferred first (stv); every candidate approved of (approval); or the one picked (plurality).")


class ServerOption(BaseModel):
    id: str
    name: str


class ServerList(BaseModel):
    servers: list[ServerOption] = Field(description="Servers the viewer can run elections in; empty for everyone else")


class ServerOptions(BaseModel):
    channels: list[ServerOption]
    roles: list[ServerOption]


class ElectionSummary(BaseModel):
    id: int
    title: str
    guild_id: Optional[str] = None
    guild_name: Optional[str] = None
    method: ElectionMethod
    seats: int
    status: ElectionStatus
    closes_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    ballots: int


class ElectionList(BaseModel):
    elections: list[ElectionSummary]


class ElectionDetail(ElectionSummary):
    """An election as its admins edit it."""
    description: Optional[str] = None
    channel_id: Optional[str] = None
    message_id: Optional[str] = None
    voter_role_id: Optional[str] = None
    show_vote_count: bool
    candidates: list[Candidate]
    locked: bool = Field(description="Ballots are in (or it closed): candidates, method and winners can't change")


class ElectionIn(BaseModel):
    guild_id: str
    channel_id: str
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    candidates: list[str] = Field(description="Candidate names in ballot order")
    method: ElectionMethod = 'stv'
    seats: int = Field(default=1, ge=1, description="Winners; only ranked (stv) elections can have more than one")
    voter_role_id: Optional[str] = None
    closes_at: Optional[datetime] = Field(default=None, description="When it closes by itself, with a time zone; null to close by hand")
    show_vote_count: bool = True


class TallyRow(BaseModel):
    id: int
    votes: float
    status: Literal['elected', 'hopeful', 'eliminated']


class TallyRound(BaseModel):
    candidates: list[TallyRow]
    exhausted: float = 0.0


class Tally(BaseModel):
    method: ElectionMethod
    seats: int
    ballots: int
    quota: Optional[float] = None
    rounds: list[TallyRound]
    winners: list[int]
    tie_broken: bool


class ElectionResults(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    method: ElectionMethod
    seats: int
    closed_at: Optional[datetime] = None
    guild_name: Optional[str] = None
    candidates: list[Candidate]
    tally: Tally


TextStatus = Literal['pending', 'approved', 'rejected']


class TriforceText(BaseModel):
    id: int
    lines: list[str]
    status: TextStatus
    submitted: Optional[datetime] = None
    author: Optional[str] = None


class TriforcePool(BaseModel):
    pool: str
    max_line_length: int
    is_moderator: bool
    mine: list[TriforceText]


class TriforceTextIn(BaseModel):
    lines: list[str] = Field(min_length=3, max_length=3)


class TriforceModerationList(BaseModel):
    pool: str
    status: Literal['pending', 'approved', 'rejected', 'all']
    texts: list[TriforceText]


class ModerationQuery(BaseModel):
    status: Literal['pending', 'approved', 'rejected', 'all'] = 'pending'


class ModerationIn(BaseModel):
    approved: bool


class FormOption(BaseModel):
    value: str
    label: str


class FormField(BaseModel):
    key: str
    label: str
    options: list[FormOption]


class SubmissionForm(BaseModel):
    event: str
    fields: list[FormField]


class SubmissionIn(BaseModel):
    episode_id: int
    settings: dict[str, str]


class SubmissionDone(BaseModel):
    event: str
    episode_id: int
    versus: str
