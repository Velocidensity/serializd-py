from __future__ import annotations

from pydantic import BaseModel


class LogSeasonsRequest(BaseModel):
    season_ids: list[int]
    show_id: int


class UnlogSeasonsRequest(LogSeasonsRequest):
    pass


class LogEpisodesRequest(BaseModel):
    episode_numbers: list[int]
    season_id: int
    show_id: int
    should_get_next_episode: bool = False


class UnlogEpisodesRequest(BaseModel):
    episode_numbers: list[int]
    season_id: int
    show_id: int
