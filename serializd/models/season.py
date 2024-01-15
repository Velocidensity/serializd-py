from __future__ import annotations

from typing import List

from pydantic import BaseModel


class Episode(BaseModel):
    episodeId: int
    airDate: str
    episodeNumber: int
    name: str
    overview: str
    stillPath: str
    seasonNumber: int


class SeasonResponse(BaseModel):
    seasonId: int
    seasonNumber: int
    name: str
    overview: str
    airDate: str
    posterPath: str
    episodes: List[Episode]
