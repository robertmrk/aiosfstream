"""Authenticatior class implementations"""
from abc import abstractmethod
from http import HTTPStatus
import reprlib

from aiocometd import AuthExtension
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError

from .exceptions import AuthenticationError


TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"


class AuthenticatorBase(AuthExtension):
    """Abstract base class to serve as a base for implementing concrete
    authenticators"""
    def __init__(self):
        self._auth_response = None
        self._auth_header = None

    @property
    def instance_url(self):
        """Salesforce instance URL

        ``None`` if not authenticated yet
        """
        if self._auth_response:
            return self._auth_response["instance_url"]
        return None

    async def outgoing(self, payload, headers):
        headers["Authorization"] = self._auth_header

    async def incoming(self, payload, headers=None):
        pass

    async def authenticate(self):
        """Called on initialization and after a failed authentication attempt

        :raise AuthenticationError: If the server rejects the authentication \
        request or if a network failure occurs
        """
        try:
            status_code, response_data = await self._authenticate()
        except ClientError as error:
            raise AuthenticationError("Network request failed") from error

        if status_code != HTTPStatus.OK:
            self._auth_response = None
            self._auth_header = None
            raise AuthenticationError("Authentication failed", response_data)

        self._auth_response = response_data
        self._auth_header = (self._auth_response["token_type"] + " " +
                             self._auth_response["access_token"])

    @abstractmethod
    async def _authenticate(self):
        """Authenticate the user

        :return: The status code and response data from the server's response
        :rtype: tuple(int, dict)
        :raise aiohttp.client_exceptions.ClientError: If a network failure \
        occurs
        """


class PasswordAuthenticator(AuthenticatorBase):
    """Authenticator for using the OAuth 2.0 Username-Password Flow"""
    def __init__(self, consumer_key, consumer_secret, username, password):
        """
        :param str consumer_key: Consumer key from the Salesforce connected \
        app definition
        :param str consumer_secret: Consumer secret from the Salesforce \
        connected app definition
        :param str username: Salesforce username
        :param str password: Salesforce password
        """
        super().__init__()
        #: OAuth2 client id
        self.client_id = consumer_key
        #: OAuth2 client secret
        self.client_secret = consumer_secret
        #: Salesforce username
        self.username = username
        #: Salesforce password
        self.password = password

    def __repr__(self):
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(consumer_key={reprlib.repr(self.client_id)}," \
               f"consumer_secret={reprlib.repr(self.client_secret)}, " \
               f"username={reprlib.repr(self.username)}, " \
               f"password={reprlib.repr(self.password)})"

    async def _authenticate(self):
        async with ClientSession() as session:
            data = {
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password
            }
            response = await session.post(TOKEN_URL, data=data)
            response_data = await response.json()
            return response.status, response_data


class RefreshTokenAuthenticator(AuthenticatorBase):
    """Authenticator for using the OAuth 2.0 Refresh Token Flow"""
    def __init__(self, consumer_key, consumer_secret, refresh_token):
        """
        :param str consumer_key: Consumer key from the Salesforce connected \
        app definition
        :param str consumer_secret: Consumer secret from the Salesforce \
        connected app definition
        :param str refresh_token: A refresh token obtained from Salesforce \
        by using one of its authentication methods (for example with the \
        OAuth 2.0 Web Server Authentication Flow)
        """
        super().__init__()
        #: OAuth2 client id
        self.client_id = consumer_key
        #: OAuth2 client secret
        self.client_secret = consumer_secret
        #: Salesforce refresh token
        self.refresh_token = refresh_token

    def __repr__(self):
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(consumer_key={reprlib.repr(self.client_id)}," \
               f"consumer_secret={reprlib.repr(self.client_secret)}, " \
               f"refresh_token={reprlib.repr(self.refresh_token)})"

    async def _authenticate(self):
        async with ClientSession() as session:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token
            }
            response = await session.post(TOKEN_URL, data=data)
            response_data = await response.json()
            return response.status, response_data
