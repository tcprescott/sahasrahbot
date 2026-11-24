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


class Election(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    private: bool
    seats: int
    candidates: list[Candidate]
    ballot: Optional[list[int]] = Field(default=None, description="Candidate ids the viewer ranked, most preferred first; null until they vote")


class BallotIn(BaseModel):
    ranking: list[int] = Field(description="Candidate ids, most preferred first. Candidates left out are unranked.")


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
