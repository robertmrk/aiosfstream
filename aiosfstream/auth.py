"""Authenticatior class implementations"""
from abc import abstractmethod
from http import HTTPStatus
import reprlib
import json

from aiocometd import AuthExtension
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError

from .exceptions import AuthenticationError


TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"


# pylint: disable=too-many-instance-attributes

class AuthenticatorBase(AuthExtension):
    """Abstract base class to serve as a base for implementing concrete
    authenticators"""
    def __init__(self, json_dumps=json.dumps, json_loads=json.loads):
        """
        :param json_dumps: Function for JSON serialization, the default is \
        :func:`json.dumps`
        :type json_dumps: :func:`callable`
        :param json_loads: Function for JSON deserialization, the default is \
        :func:`json.loads`
        :type json_loads: :func:`callable`
        """
        #: Salesforce session ID that can be used with the web services API
        self.access_token = None
        #: Value is Bearer for all responses that include an access token
        self.token_type = None
        #: A URL indicating the instance of the user’s org
        self.instance_url = None
        #: Identity URL that can be used to both identify the user and query \
        #: for more information about the user
        self.id = None  # pylint: disable=invalid-name
        #: Base64-encoded HMAC-SHA256 signature signed with the consumer’s \
        #: private key containing the concatenated ID and issued_at. Use to \
        #: verify that the identity URL hasn’t changed since the server sent it
        self.signature = None
        #: Timestamp when the signature was created
        self.issued_at = None
        #: Function for JSON serialization
        self.json_dumps = json_dumps
        #: Function for JSON deserialization
        self.json_loads = json_loads

    async def outgoing(self, payload, headers):
        headers["Authorization"] = self.token_type + " " + self.access_token

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
            self.access_token = None
            self.token_type = None
            self.instance_url = None
            self.id = None
            self.signature = None
            self.issued_at = None
            raise AuthenticationError("Authentication failed", response_data)

        self.__dict__.update(response_data)

    @abstractmethod
    async def _authenticate(self):
        """Authenticate the user

        :return: The status code and response data from the server's response
        :rtype: tuple(int, dict)
        :raise aiohttp.client_exceptions.ClientError: If a network failure \
        occurs
        """

# pylint: enable=too-many-instance-attributes
# pylint: disable=too-many-arguments


class PasswordAuthenticator(AuthenticatorBase):
    """Authenticator for using the OAuth 2.0 Username-Password Flow"""
    def __init__(self, consumer_key, consumer_secret, username, password,
                 json_dumps=json.dumps, json_loads=json.loads):
        """
        :param str consumer_key: Consumer key from the Salesforce connected \
        app definition
        :param str consumer_secret: Consumer secret from the Salesforce \
        connected app definition
        :param str username: Salesforce username
        :param str password: Salesforce password
        :param json_dumps: Function for JSON serialization, the default is \
        :func:`json.dumps`
        :type json_dumps: :func:`callable`
        :param json_loads: Function for JSON deserialization, the default is \
        :func:`json.loads`
        :type json_loads: :func:`callable`
        """
        super().__init__(json_dumps=json_dumps, json_loads=json_loads)
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
        async with ClientSession(json_serialize=self.json_dumps) as session:
            data = {
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password
            }
            response = await session.post(TOKEN_URL, data=data)
            response_data = await response.json(loads=self.json_loads)
            return response.status, response_data


class RefreshTokenAuthenticator(AuthenticatorBase):
    """Authenticator for using the OAuth 2.0 Refresh Token Flow"""
    def __init__(self, consumer_key, consumer_secret, refresh_token,
                 json_dumps=json.dumps, json_loads=json.loads):
        """
        :param str consumer_key: Consumer key from the Salesforce connected \
        app definition
        :param str consumer_secret: Consumer secret from the Salesforce \
        connected app definition
        :param str refresh_token: A refresh token obtained from Salesforce \
        by using one of its authentication methods (for example with the \
        OAuth 2.0 Web Server Authentication Flow)
        :param json_dumps: Function for JSON serialization, the default is \
        :func:`json.dumps`
        :type json_dumps: :func:`callable`
        :param json_loads: Function for JSON deserialization, the default is \
        :func:`json.loads`
        :type json_loads: :func:`callable`
        """
        super().__init__(json_dumps=json_dumps, json_loads=json_loads)
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
        async with ClientSession(json_serialize=self.json_dumps) as session:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token
            }
            response = await session.post(TOKEN_URL, data=data)
            response_data = await response.json(loads=self.json_loads)
            return response.status, response_data

# pylint: enable=too-many-arguments
