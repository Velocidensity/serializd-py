import json
import logging
from typing import Any, Type

import httpx

from serializd.consts import APP_ID, BASE_URL, FRONT_PAGE_URL
from serializd.exceptions import EmptySeasonError, InvalidTokenError, LoginError, SerializdError
from serializd.models.actions import (
    DiaryEntryRequest,
    LogEpisodesRequest,
    LogSeasonsRequest,
    UnlogEpisodesRequest,
)
from serializd.models.auth import (
    LoginRequest,
    LoginResponse,
    ValidateAuthTokenRequest,
    ValidateAuthTokenResponse
)
from serializd.models.season import SeasonResponse
from serializd.models.show import ShowResponse


class SerializdClient:
    """Serializd.com API client class"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = httpx.Client(base_url=BASE_URL)
        self.session.headers.update({
            'Origin': FRONT_PAGE_URL,
            'Referer': FRONT_PAGE_URL,
            'X-Requested-With': APP_ID,
        })
        self._access_token: str | None = None

    def load_token(self, access_token: str, check: bool = True):
        """
        Loads saved Serializd user access token

        Args:
            access_token: User access token
            check: Enable checking token validity (default: true)

        Raises:
            InvalidTokenError: If check is enabled and provided access token is invalid
        """
        if check and not self.check_token(access_token):
            self.logger.error('Provided Serializd token is invalid!')
            raise InvalidTokenError

        self._access_token = access_token
        self.session.headers.update({
            'Authorization': f'Bearer {self._access_token}',
        })

    def check_token(self, access_token: str) -> ValidateAuthTokenResponse:
        """
        Checks whether given access token is still valid

        Args:
            access_token: User access token

        Returns:
            Token validity status.

        Raises:
            SerializdError: Serializd returned an error
        """
        self.logger.info('Checking Serializd token validity')
        params = ValidateAuthTokenRequest(token=access_token)
        resp = self.session.post(
            '/validateauthtoken',
            data=params.model_dump_json()
        )
        return ValidateAuthTokenResponse(**self._parse_response(resp))

    @property
    def access_token(self) -> str | None:
        """Serializd user access token"""
        return self._access_token

    def login(self, email: str, password: str) -> LoginResponse:
        """
        Logs in into Serializd using provided credentials

        Args:
            email: User account email
            password: User account password

        Returns:
            Access token.

        Raises:
            LoginError: Failed to log in
        """

        params = LoginRequest(email=email, password=password)
        resp = self.session.post(
            '/login',
            data=params.model_dump_json(),
        )
        if not resp.is_success:
            self.logger.error('Failed to log in to Serializd using provided credentials!')

        parsed = LoginResponse(**self._parse_response(resp, exception=LoginError))
        self.load_token(parsed.token, check=False)

        return parsed

    def get_show(self, show_id: int) -> ShowResponse:
        """
        Fetches and returns show information

        Args:
            show_id: TMDB show ID

        Returns:
            Show information as a dict.

        Raises:
            SerializdError: Serializd returned an error
        """
        resp = self.session.get(f'/show/{show_id}')
        if not resp.is_success:
            self.logger.error('Failed to fetch show information for show ID %d!', show_id)

        return ShowResponse(**self._parse_response(resp))

    def get_season(self, show_id: int, season_number: int) -> SeasonResponse:
        """
        Fetches and returns season information

        Args:
            show_id: TMDB show ID
            season_number: Season number

        Returns:
            Season information as a dict.

        Raises:
            SerializdError: Serializd returned an error
            EmptySeasonError: Serializd returned empty season information
        """
        resp = self.session.get(f'/show/{show_id}/season/{season_number}')
        if not resp.is_success:
            self.logger.error(
                'Failed to fetch season information for show ID %s, season %s!',
                show_id, season_number
            )

        parsed = self._parse_response(resp)
        if parsed['seasonId'] is None:
            message = (
                f'Serializd return empty season information for ID {show_id}, '
                f'season {season_number:02d} (likely: no episodes)'
            )
            self.logger.error(message)
            raise EmptySeasonError(message)

        return SeasonResponse(**parsed)

    def get_user_show_progress(self, username: str, show_id: int) -> dict:
        """
        Fetches watched episode progress for a show for a specific user.

        Args:
            username: Serializd username
            show_id: TMDB show ID

        Returns:
            Dict with watched episodes data

        Raises:
            SerializdError: Serializd returned an error
        """
        resp = self.session.get(f'/user/{username}/show/{show_id}/progress')
        if not resp.is_success:
            # Progress endpoint might not exist, return empty dict
            return {}
        
        try:
            return resp.json()
        except Exception:
            return {}

    def is_episode_watched(self, username: str, show_id: int, season_number: int, episode_number: int) -> bool:
        """
        Checks if an episode is already marked as watched for a user.

        Args:
            username: Serializd username
            show_id: TMDB show ID
            season_number: Season number
            episode_number: Episode number

        Returns:
            True if episode is watched, False otherwise
        """
        try:
            progress = self.get_user_show_progress(username, show_id)
            if not progress:
                return False
            
            # Check the watched episodes structure
            watched_seasons = progress.get('watchedSeasons', [])
            for season in watched_seasons:
                if season.get('seasonNumber') == season_number:
                    watched_episodes = season.get('watchedEpisodes', [])
                    return episode_number in watched_episodes
            return False
        except Exception:
            return False

    def log_show(self, show_id: int) -> bool:
        """
        Adds a given show (all seasons) to the user's watched list

        Args:
            show_id: TMDB show ID

        Returns:
            Success status.

        Raises:
            SerializdError: Serializd returned an error
        """
        show_info = self.get_show(show_id)
        return self.log_seasons(
            show_id=show_id,
            season_ids=[season.id for season in show_info.seasons]
        )

    def unlog_show(self, show_id: int) -> bool:
        """
        Removes a given show (all seasons) from the user's watched list

        Args:
            show_id: TMDB show ID

        Returns:
            Success status.

        Raises:
            SerializdError: Serializd returned an error
        """
        show_info = self.get_show(show_id)
        return self.unlog_seasons(
            show_id=show_id,
            season_ids=[season.id for season in show_info.seasons]
        )

    def log_seasons(self, show_id: int, season_ids: list[int]) -> bool:
        """
        Adds given seasons (by ID) to the user's watched list

        Args:
            show_id: TMDB show ID
            season_ids: List of TMDB season ID

        Returns:
            Success status.

        Raises:
            SerializdError: Serializd returned an error
        """
        params = LogSeasonsRequest(season_ids=season_ids, show_id=show_id)
        resp = self.session.post(
            '/watched_v2',
            data=params.model_dump_json()
        )
        if not resp.is_success:
            self.logger.error(
                'Failed to log seasons %s of show ID %d as watched!',
                season_ids, show_id
            )
            self._parse_response(resp)
            return False

        return True

    def unlog_seasons(self, show_id: int, season_ids: list[int]) -> bool:
        """
        Removes given seasons (by ID) from the user's watched list

        Args:
            show_id: TMDB show ID
            season_ids: List of TMDB season ID

        Returns:
            Success status.

        Raises:
            SerializdError: Serializd returned an error
        """
        params = LogSeasonsRequest(season_ids=season_ids, show_id=show_id)
        resp = self.session.post(
            '/watched/remove_v2',
            data=params.model_dump_json()
        )
        if not resp.is_success:
            self.logger.error(
                'Failed to unlog seasons %s of show ID %d as watched!',
                season_ids, show_id
            )
            self._parse_response(resp)
            return False

        return True

    def log_episodes(self, show_id: int, season_id: int, episode_numbers: list[int]) -> bool:
        """
        Adds given episodes (by numbers) to the user's watched list

        Note: This does not mark the season as watched,
              even if all episodes are provided

        Args:
            show_id: TMDB show ID
            season_id: TMDB season ID
            episode_numbers: List of episodes numbers

        Returns:
            Success status.

        Raises:
            SerializdError: Serializd returned an error
        """
        params = LogEpisodesRequest(
            episode_numbers=episode_numbers,
            season_id=season_id,
            show_id=show_id
        )
        resp = self.session.post(
            '/episode_log/add',
            data=params.model_dump_json()
        )
        if not resp.is_success:
            self.logger.error(
                'Failed to log episodes %s of season ID %d (show ID %d) as watched!',
                episode_numbers, season_id, show_id
            )
            self._parse_response(resp)
            return False

        return True

    def unlog_episodes(self, show_id: int, season_id: int, episode_numbers: list[int]) -> bool:
        """
        Removes given episodes (by numbers) from the user's watched list

        Note: This does not unmark the season as watched,
              even if all episodes are provided

        Args:
            show_id: TMDB show ID
            season_id: TMDB season ID
            episode_numbers: List of episodes numbers

        Returns:
            Success status.

        Raises:
            SerializdError: Serializd returned an error
        """
        params = UnlogEpisodesRequest(
            episode_numbers=episode_numbers,
            season_id=season_id,
            show_id=show_id
        )
        resp = self.session.post(
            '/episode_log/remove',
            data=params.model_dump_json()
        )
        if not resp.is_success:
            self.logger.error(
                'Failed to unlog episodes %s of season ID %d (show ID %d) as watched!',
                episode_numbers, season_id, show_id
            )
            self._parse_response(resp)
            return False

        return True

    def log_episode_to_diary(
        self,
        show_id: int,
        season_id: int,
        episode_number: int,
        watched_at: str,
        is_rewatch: bool = False,
        rating: int = 0,
        review_text: str = "",
        mark_as_watched: bool = True
    ) -> bool:
        """
        Adds an episode to the user's diary with a specific watch date.

        Uses the /show/reviews/add endpoint which supports backdating entries.
        This is the preferred method for migrating watch history with dates.

        Note: This logs one episode at a time. For bulk logging without dates,
              use log_episodes() instead.

        Args:
            show_id: TMDB show ID
            season_id: Serializd season ID
            episode_number: Episode number within the season
            watched_at: ISO 8601 datetime string (e.g., '2024-01-15T12:00:00Z')
            is_rewatch: Whether this is a rewatch of a previously seen episode
            rating: Optional rating (0-10, 0 means no rating)
            review_text: Optional review text
            mark_as_watched: Also mark the episode as watched (default: True)

        Returns:
            Success status.

        Raises:
            SerializdError: Serializd returned an error
        """
        # First, mark the episode as watched using episode_log/add
        # This ensures the episode shows up in the watched list, not just the diary
        if mark_as_watched:
            try:
                watched_success = self.log_episodes(
                    show_id=show_id,
                    season_id=season_id,
                    episode_numbers=[episode_number]
                )
                if not watched_success:
                    self.logger.warning(
                        'Failed to mark episode %d as watched, continuing with diary entry',
                        episode_number
                    )
            except Exception as e:
                self.logger.warning(
                    'Error marking episode %d as watched (%s), continuing with diary entry',
                    episode_number, str(e)
                )

        # Then add to diary with the specific date
        params = DiaryEntryRequest(
            show_id=show_id,
            season_id=season_id,
            episode_number=episode_number,
            backdate=watched_at,
            is_rewatch=is_rewatch,
            rating=rating,
            review_text=review_text
        )
        resp = self.session.post(
            '/show/reviews/add',
            data=params.model_dump_json()
        )
        if not resp.is_success:
            self.logger.error(
                'Failed to add episode %d of season ID %d (show ID %d) to diary!',
                episode_number, season_id, show_id
            )
            self._parse_response(resp)
            return False

        return True

    def get_user_diary(self, username: str, page: int = 1) -> dict[str, Any]:
        """
        Fetches diary entries for a user.

        Args:
            username: Serializd username
            page: Page number (default: 1)

        Returns:
            Dict with 'reviews' list and pagination info.

        Raises:
            SerializdError: Serializd returned an error
        """
        resp = self.session.get(f'/user/{username}/diary', params={'page': page})
        if not resp.is_success:
            self.logger.error('Failed to fetch diary for user %s!', username)

        return self._parse_response(resp)

    def get_all_diary_entries(self, username: str) -> list[dict[str, Any]]:
        """
        Fetches all diary entries for a user (all pages).

        Args:
            username: Serializd username

        Returns:
            List of all diary entry dicts.

        Raises:
            SerializdError: Serializd returned an error
        """
        all_entries = []
        page = 1

        while True:
            self.logger.info('Fetching diary page %d for user %s', page, username)
            data = self.get_user_diary(username, page=page)
            reviews = data.get('reviews', [])

            if not reviews:
                break

            all_entries.extend(reviews)
            total_pages = data.get('totalPages', 1)

            if page >= total_pages:
                break

            page += 1

        return all_entries

    def delete_diary_entry(self, review_id: int) -> bool:
        """
        Deletes a diary entry (review) by ID.

        Args:
            review_id: The ID of the diary entry/review to delete

        Returns:
            True if deletion was successful, False otherwise.

        Raises:
            SerializdError: Serializd returned an error
        """
        resp = self.session.post(
            '/show/reviews/delete',
            json={'review_id': review_id}
        )
        if not resp.is_success:
            self.logger.error('Failed to delete diary entry %d!', review_id)
            return False
        
        return True

    def _parse_response(
        self,
        resp: httpx.Response,
        exception: Type[SerializdError] = SerializdError
    ) -> dict[str, Any]:
        """
        Reads, parses and checks a HTTP response

        Checks output for JSON message errors, and returns parsed response.

        Args:
            resp: HTTP response

        Returns:
            JSON response.

        Raises:
            json.decoder.JSONDecodeError: Failed to parse response as JSON
            SerializdError: Serializd returned an error
        """
        try:
            resp_json = resp.json()
        except json.decoder.JSONDecodeError as exc:
            self.logger.debug('Failed to parse response as JSON')
            self.logger.debug(resp.text)
            raise exc from exc

        if not resp.is_success:
            if message := resp_json.get('message'):
                self.logger.error('Error message: "%s"', message)
                raise exception(message)
            raise exception(f'Request returned status code {resp.status_code}')

        return resp_json
