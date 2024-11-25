__all__ = ["HubSpaceAuth", "InvalidAuth", "InvalidResponse"]

import asyncio
import base64
import datetime
import hashlib
import logging
import os
import re
from collections import namedtuple
from typing import Final, Optional
from urllib.parse import parse_qs, urlparse

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from .const import HUBSPACE_DEFAULT_USERAGENT

logger = logging.getLogger(__name__)


HUBSPACE_OPENID_URL: Final[str] = (
    "https://accounts.mykoapp.com/auth/realms/kfi/protocol/openid-connect/auth"
)
HUBSPACE_DEFAULT_CLIENT_ID: Final[str] = "kfi_android"

HUBSPACE_DEFAULT_REDIRECT_URI: Final[str] = "kfi-app://loginredirect"
HUBSPACE_CODE_URL: Final[str] = (
    "https://accounts.mykoapp.com/auth/realms/kfi/login-actions/authenticate"
)
HUBSPACE_TOKEN_HEADERS: Final[dict[str, str]] = {
    "Content-Type": "application/x-www-form-urlencoded",
    "user-agent": HUBSPACE_DEFAULT_USERAGENT,
    "host": "accounts.mykoapp.com",
}
HUBSPACE_TOKEN_URL: Final[str] = (
    "https://accounts.mykoapp.com/auth/realms/kfi/protocol/openid-connect/token"
)
TOKEN_TIMEOUT: Final[int] = 118
STATUS_CODE: Final[str] = "Status Code: %s"


auth_challenge = namedtuple("AuthChallenge", ["challenge", "verifier"])
token_data = namedtuple("TokenData", ["token", "expiration"])
auth_sess_data = namedtuple("AuthSessionData", ["session_code", "execution", "tab_id"])


class InvalidAuth(Exception):
    pass


class InvalidResponse(Exception):
    pass


class HubSpaceAuth:
    """Authentication against the HubSpace API

    This class follows the HubSpace authentication workflow and utilizes
    refresh tokens.
    """

    def __init__(self, username, password):
        self._async_lock: asyncio.Lock = asyncio.Lock()
        self._username: str = username
        self._password: str = password
        self._refresh_token: Optional[str] = None
        self._token_data: Optional[token_data] = None

    @property
    async def is_expired(self) -> bool:
        """Determine if the token is expired"""
        if not self._token_data:
            return True
        return datetime.datetime.now().timestamp() >= self._token_data.expiration

    async def webapp_login(
        self, challenge: auth_challenge, client: ClientSession
    ) -> str:
        """Perform login to the webapp for a code

        Login to the webapp and generate a code used for generating tokens.

        :param challenge: Challenge data for connection and approving
        :param client: async client for making requests

        :return: Code used for generating a refresh token
        """
        code_params: dict[str, str] = {
            "response_type": "code",
            "client_id": HUBSPACE_DEFAULT_CLIENT_ID,
            "redirect_uri": HUBSPACE_DEFAULT_REDIRECT_URI,
            "code_challenge": challenge.challenge,
            "code_challenge_method": "S256",
            "scope": "openid offline_access",
        }
        logger.hs_trace(
            "URL: %s\n\tparams: %s",
            HUBSPACE_OPENID_URL,
            code_params,
        )
        async with client.get(
            HUBSPACE_OPENID_URL, params=code_params, allow_redirects=False
        ) as response:
            logger.hs_trace(STATUS_CODE, response.status)
            response.raise_for_status()
            contents = await response.text()
            login_data = await extract_login_data(contents)
            logger.hs_trace(
                (
                    "WebApp Login:"
                    "\n\tSession Code: %s"
                    "\n\tExecution: %s"
                    "\n\tTab ID:%s"
                ),
                login_data.session_code,
                login_data.execution,
                login_data.tab_id,
            )
            return await self.generate_code(
                login_data.session_code,
                login_data.execution,
                login_data.tab_id,
                client,
            )

    @staticmethod
    async def generate_challenge_data() -> auth_challenge:
        code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
        code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
        code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
        code_challenge = code_challenge.replace("=", "")
        chal = auth_challenge(code_challenge, code_verifier)
        logger.hs_trace("Challenge information: %s", chal)
        return chal

    async def generate_code(
        self, session_code: str, execution: str, tab_id: str, client: ClientSession
    ) -> str:
        """Finalize login to HubSpace page

        :param session_code: Session code during form interaction
        :param execution: Session code during form interaction
        :param tab_id: Session code during form interaction
        :param client: async client for making request

        :return: code for generating tokens
        """
        logger.hs_trace("Generating code")
        params = {
            "session_code": session_code,
            "execution": execution,
            "client_id": HUBSPACE_DEFAULT_CLIENT_ID,
            "tab_id": tab_id,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "user-agent": HUBSPACE_DEFAULT_USERAGENT,
        }
        auth_data = {
            "username": self._username,
            "password": self._password,
            "credentialId": "",
        }
        logger.hs_trace(
            "URL: %s\n\tparams: %s\n\tdata: %s\n\theaders: %s",
            HUBSPACE_CODE_URL,
            params,
            auth_data,
            headers,
        )
        async with client.post(
            HUBSPACE_CODE_URL,
            params=params,
            data=auth_data,
            headers=headers,
            allow_redirects=False,
        ) as response:
            logger.hs_trace(STATUS_CODE, response.status)
            if response.status != 302:
                raise InvalidResponse(
                    f"Unable to process the result from {response.url}: {response.status}"
                )
            try:
                parsed_url = urlparse(response.headers["location"])
                code = parse_qs(parsed_url.query)["code"][0]
            except KeyError:
                raise InvalidAuth(
                    "Unable to authenticate with the supplied username / password"
                )
            logger.hs_trace("Location: %s", response.headers.get("location"))
            logger.hs_trace("Code: %s", code)
            return code

    @staticmethod
    async def generate_refresh_token(
        code: str, challenge: auth_challenge, client: ClientSession
    ) -> str:
        """Generate the refresh token from the given code and challenge

        :param code: Code used for generating refresh token
        :param challenge: Challenge data for connection and approving
        :param client: async client for making request

        :return: Refresh token to generate a new token
        """
        logger.hs_trace("Generating refresh token")
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": HUBSPACE_DEFAULT_REDIRECT_URI,
            "code_verifier": challenge.verifier,
            "client_id": HUBSPACE_DEFAULT_CLIENT_ID,
        }
        logger.hs_trace(
            "URL: %s\n\tdata: %s\n\theaders: %s",
            HUBSPACE_TOKEN_URL,
            data,
            HUBSPACE_TOKEN_HEADERS,
        )
        async with client.post(
            HUBSPACE_TOKEN_URL, headers=HUBSPACE_TOKEN_HEADERS, data=data
        ) as response:
            logger.hs_trace(STATUS_CODE, response.status)
            response.raise_for_status()
            resp_json = await response.json()
            try:
                refresh_token = resp_json["refresh_token"]
            except KeyError:
                raise InvalidResponse("Unable to extract refresh token")
            logger.hs_trace("JSON response: %s", resp_json)
            return refresh_token

    async def perform_initial_login(self, client: ClientSession) -> str:
        """Login to generate a refresh token

        :param client: async client for making request

        :return: Refresh token for the auth
        """
        logger.debug("Refresh token not present. Generating a new refresh token")
        challenge = await HubSpaceAuth.generate_challenge_data()
        code: str = await self.webapp_login(challenge, client)
        logger.debug("Successfully generated an auth code")
        refresh_token = await self.generate_refresh_token(code, challenge, client)
        logger.debug("Successfully generated a refresh token")
        return refresh_token

    async def token(self, client: ClientSession) -> str:
        async with self._async_lock:
            if not self._refresh_token:
                self._refresh_token = await self.perform_initial_login(client)
            if await self.is_expired:
                logger.debug("Token has not been generated or is expired")
                self._token_data = await generate_token(client, self._refresh_token)
                logger.debug("Token has been successfully generated")
        return self._token_data.token


async def extract_login_data(page: str) -> auth_sess_data:
    """Extract the required login data from the auth page

    :param page: the response from performing a GET against HUBSPACE_OPENID_URL
    """
    auth_page = BeautifulSoup(page, features="html.parser")
    login_form = auth_page.find("form", id="kc-form-login")
    if login_form is None:
        raise InvalidResponse("Unable to parse login page")
    try:
        login_url: str = login_form.attrs["action"]
    except KeyError:
        raise InvalidResponse("Unable to extract login url")
    parsed_url = urlparse(login_url)
    login_data = parse_qs(parsed_url.query)
    try:
        return auth_sess_data(
            login_data["session_code"][0],
            login_data["execution"][0],
            login_data["tab_id"][0],
        )
    except (KeyError, IndexError) as err:
        raise InvalidResponse("Unable to parse login url") from err


async def generate_token(client: ClientSession, refresh_token: str) -> token_data:
    """Generate a token from the refresh token

    :param client: async client for making request
    :param refresh_token: Refresh token for generating request tokens
    """
    logger.hs_trace("Generating token")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "openid email offline_access profile",
        "client_id": HUBSPACE_DEFAULT_CLIENT_ID,
    }
    logger.hs_trace(
        ("URL: %s" "\n\tdata: %s" "\n\theaders: %s"),
        HUBSPACE_TOKEN_URL,
        data,
        HUBSPACE_TOKEN_HEADERS,
    )
    async with client.post(
        HUBSPACE_TOKEN_URL, headers=HUBSPACE_TOKEN_HEADERS, data=data
    ) as response:
        logger.hs_trace("Status code: %s", response.status)
        response.raise_for_status()
        resp_json = await response.json()
        try:
            auth_token = resp_json["id_token"]
        except KeyError:
            raise InvalidResponse("Unable to extract the token")
        logger.hs_trace("JSON response: %s", resp_json)
        return token_data(
            auth_token, datetime.datetime.now().timestamp() + TOKEN_TIMEOUT
        )
