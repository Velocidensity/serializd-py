from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel


class Network(BaseModel):
    id: int
    name: str
    logo_path: str | None
    origin_country: str


class Genre(BaseModel):
    id: int
    name: str


class Season(BaseModel):
    id: int
    airDate: str | None
    episodeCount: int
    name: str
    overview: str
    posterPath: str | None
    seasonNumber: int


class NextEpisodeToAir(BaseModel):
    id: int
    name: str
    runtime: int
    show_id: int
    air_date: str | None
    overview: str
    still_path: str | None
    vote_count: int
    episode_type: str
    vote_average: float
    season_number: int
    episode_number: int
    production_code: str


class EpisodeToPreview(BaseModel):
    episodeId: int
    airDate: str
    episodeNumber: int
    name: str
    overview: str
    stillPath: str | None
    seasonNumber: int


class ShowResponse(BaseModel):
    id: int
    name: str
    tagline: str
    summary: str
    status: str
    bannerImage: str | None
    premiereDate: str
    lastAirDate: str
    networks: List[Network]
    genres: List[Genre]
    seasons: List[Season]
    numSeasons: int
    numEpisodes: int
    nextEpisodeToAir: NextEpisodeToAir | None
    episodeToPreview: EpisodeToPreview | None
    episodeRunTime: List[int]
    nextEpisodeForUser: Any
