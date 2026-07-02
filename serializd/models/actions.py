from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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


class DiaryEntryRequest(BaseModel):
    """Request model for adding an episode to diary with custom date.
    
    Uses the /show/reviews/add endpoint which supports backdating entries.
    """
    show_id: int
    season_id: int
    episode_number: int
    backdate: str = Field(
        ...,
        description="ISO 8601 formatted datetime string (e.g., '2025-06-15T12:00:00Z')"
    )
    review_text: str = ""
    rating: int = Field(default=0, ge=0, le=10)
    contains_spoiler: bool = False
    is_log: bool = True
    is_rewatch: bool = False
    tags: list[str] = Field(default_factory=list)
    allows_comments: bool = True
    like: bool = False
    
    @classmethod
    def from_watch_data(
        cls,
        show_id: int,
        season_id: int,
        episode_number: int,
        watched_at: datetime | str,
        is_rewatch: bool = False
    ) -> DiaryEntryRequest:
        """Create a diary entry from watch history data.
        
        Args:
            show_id: Serializd show ID
            season_id: Serializd season ID  
            episode_number: Episode number in the season
            watched_at: When the episode was watched (datetime or ISO string)
            is_rewatch: Whether this is a rewatch
            
        Returns:
            DiaryEntryRequest configured for logging a watched episode
        """
        if isinstance(watched_at, datetime):
            backdate = watched_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            backdate = watched_at
            
        return cls(
            show_id=show_id,
            season_id=season_id,
            episode_number=episode_number,
            backdate=backdate,
            is_rewatch=is_rewatch
        )
