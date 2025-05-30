import json
import logging
from typing import Any, Type

import httpx

from serializd.consts import APP_ID, AUTH_COOKIE_NAME, BASE_URL, COOKIE_DOMAIN, FRONT_PAGE_URL
from serializd.exceptions import EmptySeasonError, InvalidTokenError, LoginError, SerializdError
from serializd.models.actions import LogEpisodesRequest, LogSeasonsRequest, UnlogEpisodesRequest
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

        self.session.cookies.set(
            name=AUTH_COOKIE_NAME,
            value=access_token,
            domain=COOKIE_DOMAIN
        )

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
        return self.session.cookies.get(AUTH_COOKIE_NAME)

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
                'Failed to fetch season information for show ID %d, season %02d!',
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
                'Failed to log epsiodes of season ID %d (show ID %d) as watched!',
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
                'Failed to unlog epsiodes of season ID %d (show ID %d) as watched!',
                episode_numbers, season_id, show_id
            )
            self._parse_response(resp)
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
