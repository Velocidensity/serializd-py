from __future__ import annotations

from typing import List

from pydantic import BaseModel


class Episode(BaseModel):
    episodeId: int
    airDate: str | None
    episodeNumber: int
    name: str
    overview: str
    stillPath: str | None
    seasonNumber: int


class SeasonResponse(BaseModel):
    seasonId: int
    seasonNumber: int
    name: str
    overview: str
    airDate: str | None
    posterPath: str | None
    episodes: List[Episode]
