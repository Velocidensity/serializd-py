import json
import logging
from typing import Type

import httpx

from serializd.consts import APP_ID, AUTH_COOKIE_NAME, BASE_URL, COOKIE_DOMAIN, FRONT_PAGE_URL
from serializd.exceptions import InvalidTokenError, LoginError, SerializdError


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

    def check_token(self, access_token: str) -> bool:
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
        resp = self.session.post(
            '/validateauthtoken',
            json={'token': access_token}
        )
        resp_json = self._parse_response(resp)
        return resp_json['isValid']

    @property
    def access_token(self) -> str | None:
        """Serializd user access token"""
        return self.session.cookies.get(AUTH_COOKIE_NAME)

    def login(self, email: str, password: str) -> str:
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

        resp = self.session.post(
            '/login',
            json={
                'email': email,
                'password': password
            }
        )
        if not resp.is_success:
            self.logger.error('Failed to log in to Serializd using provided credentials!')
        resp_json = self._parse_response(resp, exception=LoginError)

        self.load_token(resp_json['token'], check=False)
        return resp_json['token']

    def get_show(self, show_id: int) -> dict:
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

        return self._parse_response(resp)

    def get_season(self, show_id: int, season_number: int) -> dict:
        """
        Fetches and returns season information

        Args:
            show_id: TMDB show ID
            season_number: Season number

        Returns:
            Season information as a dict.

        Raises:
            SerializdError: Serializd returned an error
        """
        resp = self.session.get(f'/show/{show_id}/season/{season_number}')
        if not resp.is_success:
            self.logger.error(
                'Failed to fetch season information for show ID %d, season %02d!',
                show_id, season_number
            )

        return self._parse_response(resp)

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
            season_ids=[season['seasonId'] for season in show_info['seasons']]
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
            season_ids=[season['seasonId'] for season in show_info['seasons']]
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
        resp = self.session.post(
            '/watched_v2',
            json={
                'season_ids': season_ids,
                'show_id': show_id
            }
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
        resp = self.session.post(
            '/watched/remove_v2',
            json={
                'season_ids': season_ids,
                'show_id': show_id
            }
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
        resp = self.session.post(
            '/episode_log/add',
            json={
                'episode_numbers': episode_numbers,
                'season_id': season_id,
                'show_id': show_id,
                'should_get_next_episode': False
            }
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
        resp = self.session.post(
            '/episode_log/remove',
            json={
                'episode_numbers': episode_numbers,
                'season_id': season_id,
                'show_id': show_id,
            }
        )
        if not resp.is_success:
            self.logger.error(
                'Failed to unlog epsiodes of season ID %d (show ID %d) as watched!',
                episode_numbers, season_id, show_id
            )
            self._parse_response(resp)
            return False

        return True

    def _parse_response(self, resp: httpx.Response, exception: Type[SerializdError] = SerializdError) -> dict:
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
