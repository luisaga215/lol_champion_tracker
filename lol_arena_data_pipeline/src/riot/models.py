"""Pydantic models mirroring the Riot match-v5 API payloads.

Only the fields required by the Arena pipeline are declared; unknown fields are
ignored so the models remain robust to future API additions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_ITEMS = (0, 0, 0, 0, 0, 0, 0)


class Participant(BaseModel):
    """A single participant in an Arena match."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    puuid: str
    champion_id: int = Field(alias="championId")
    champion_name: str = Field(alias="championName")
    placement: int = 1
    subteam_placement: int | None = Field(default=None, alias="subteamPlacement")
    team_id: int | None = Field(default=None, alias="teamId")
    subteam_id: int | None = Field(default=None, alias="subteamId")
    item0: int = 0
    item1: int = 0
    item2: int = 0
    item3: int = 0
    item4: int = 0
    item5: int = 0
    item6: int = 0
    player_augment1: int = Field(default=0, alias="playerAugment1")
    player_augment2: int = Field(default=0, alias="playerAugment2")
    player_augment3: int = Field(default=0, alias="playerAugment3")
    player_augment4: int = Field(default=0, alias="playerAugment4")

    @property
    def items(self) -> list[int]:
        """Final equipped items (including the Arena item slot)."""
        return [self.item0, self.item1, self.item2, self.item3, self.item4, self.item5, self.item6]

    @property
    def augments(self) -> list[int]:
        """Equipped augment ids (``0`` indicates an empty slot)."""
        return [
            self.player_augment1,
            self.player_augment2,
            self.player_augment3,
            self.player_augment4,
        ]


class MatchMetadata(BaseModel):
    """Metadata section of a match payload."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    match_id: str = Field(alias="matchId")
    participants: list[str] = Field(default_factory=list)


class MatchInfo(BaseModel):
    """Info section of a match payload."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    game_version: str = Field(alias="gameVersion")
    game_duration: int | None = Field(default=None, alias="gameDuration")
    queue_id: int = Field(alias="queueId")
    participants: list[Participant] = Field(default_factory=list)


class Match(BaseModel):
    """A parsed Arena match."""

    model_config = ConfigDict(extra="ignore")

    metadata: MatchMetadata
    info: MatchInfo

    @property
    def match_id(self) -> str:
        return self.metadata.match_id

    @property
    def game_version(self) -> str:
        return self.info.game_version

    def participant_by_id(self, participant_id: int) -> Participant | None:
        """Map a timeline ``participantId`` (1-indexed) to a participant."""
        index = participant_id - 1
        if 0 <= index < len(self.info.participants):
            return self.info.participants[index]
        return None


class TimelineEvent(BaseModel):
    """A single timeline event.

    Only common fields are typed; Arena round metadata (e.g. ``roundNumber``) is
    preserved via ``extra="allow"`` and read through :attr:`model_extra`.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: str
    timestamp: int
    participant_id: int | None = Field(default=None, alias="participantId")
    item_id: int | None = Field(default=None, alias="itemId")
    skill_slot: int | None = Field(default=None, alias="skillSlot")


class TimelineFrame(BaseModel):
    """A single timeline frame."""

    model_config = ConfigDict(extra="ignore")

    timestamp: int = 0
    events: list[TimelineEvent] = Field(default_factory=list)


class TimelineInfo(BaseModel):
    """Info section of a timeline payload."""

    model_config = ConfigDict(extra="ignore")

    frames: list[TimelineFrame] = Field(default_factory=list)


class Timeline(BaseModel):
    """A parsed match timeline."""

    model_config = ConfigDict(extra="ignore")

    metadata: dict[str, Any] = Field(default_factory=dict)
    info: TimelineInfo = Field(default_factory=TimelineInfo)

    def iter_events(self) -> list[TimelineEvent]:
        """Flatten all events across frames in chronological order."""
        events: list[TimelineEvent] = []
        for frame in self.info.frames:
            events.extend(frame.events)
        events.sort(key=lambda event: event.timestamp)
        return events
