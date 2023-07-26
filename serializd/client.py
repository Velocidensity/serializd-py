import json
import logging
from typing import Type

import httpx

from serializd.consts import APP_ID, AUTH_COOKIE_NAME, BASE_URL, COOKIE_DOMAIN, FRONT_PAGE_URL
from serializd.exceptions import InvalidTokenError, LoginError, ParseError, RequestError, SerializdError


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
            RequestError: HTTP request not successful
            ParseError: JSON parse failure error
            InvalidTokenError: if check is enabled and provided access token is invalid
        """
        if check and not self.check_token(access_token):
            self.logger.error('Provided token is invalid!')
            raise InvalidTokenError

        self.session.cookies.set(
            name=AUTH_COOKIE_NAME,
            value=access_token,
            domain=COOKIE_DOMAIN
        )

    def login(self, email: str, password: str) -> str:
        """
        Logs in into Serializd using provided credentials

        Args:
            email: User account email
            password: User account password

        Returns:
            Access token.

        Raises:
            RequestError: HTTP request not successful
            ParseError: JSON parse failure error
            InvalidEmailError: if provided email is invalid
            InvalidPasswordError: if provided password is invalid
            LoginError: if an unexpected login error happens
        """

        resp = self.session.post(
            '/login',
            json={
                'email': email,
                'password': password
            }
        )
        if not resp.is_success:
            self.logger.error('Failed to log in using provided credentials!')
        resp_json = self._parse_response(resp, exception=LoginError)

        self.load_token(resp_json['token'], check=False)
        return resp_json['token']

    def check_token(self, access_token: str) -> bool:
        """Checks whether given access token is still valid

        Args:
            access_token: User access token

        Returns:
            Token validity status.

        Raises:
            RequestError: HTTP request not successful
            ParseError: JSON parse failure error
        """
        self.logger.info('Checking token validity')
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

    def _parse_response(self, resp: httpx.Response, exception: Type[SerializdError] = RequestError) -> dict:
        """Reads, parses and checks a HTTP response

        Checks output for JSON message errors, and returns parsed response.

        Args:
            resp: HTTP response

        Returns:
            JSON response.

        Raises:
            RequestError: HTTP request not successful
            ParseError: JSON parse failure error
            ResponseError: error originating from the "message" field in response
        """
        try:
            resp_json = resp.json()
        except json.decoder.JSONDecodeError:
            self.logger.debug('Failed to parse response as JSON')
            self.logger.debug(resp.text)
            raise ParseError

        if message := resp_json.get('message'):
            self.logger.error('Error message: "%s"', message)
            raise exception(message)

        if not resp.is_success:
            raise RequestError

        return resp_json
