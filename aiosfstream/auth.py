"""Authenticatior class implementations"""
from abc import abstractmethod

from aiocometd import AuthExtension
from aiohttp import ClientSession


AUTHORIZATION_URL = "https://login.salesforce.com/services/oauth2/authorize"
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
        self._auth_response = await self._authenticate()
        self._auth_header = (self._auth_response["token_type"] + " " +
                             self._auth_response["access_token"])

    @abstractmethod
    async def _authenticate(self):
        """Authenticate the user

        :return: The server's response
        :rtype: dict
        """


class PasswordAuthenticator(AuthenticatorBase):
    def __init__(self, client_id, client_secret, username, password):
        super().__init__()
        #: OAuth2 client id
        self.client_id = client_id
        #: OAuth2 client secret
        self.client_secret = client_secret
        #: Salesforce username
        self.username = username
        #: Salesforce password
        self.password = password

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
            return await response.json()
