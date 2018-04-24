from http import HTTPStatus
import reprlib

from asynctest import TestCase, mock
from aiohttp.client_exceptions import ClientError

from aiosfstream.auth import AuthenticatorBase, PasswordAuthenticator, \
    TOKEN_URL, RefreshTokenAuthenticator
from aiosfstream.exceptions import AuthenticationError


class Authenticator(AuthenticatorBase):
    async def _authenticate(self):
        return {}


class TestAuthenticatorBase(TestCase):
    def setUp(self):
        self.authenticator = Authenticator()

    def test_instance_url(self):
        self.authenticator._auth_response = {
            "instance_url": "url"
        }

        result = self.authenticator.instance_url

        self.assertEqual(result, "url")

    def test_instance_url_none(self):
        self.authenticator._auth_response = None

        result = self.authenticator.instance_url

        self.assertEqual(result, None)

    async def test_outgoing_sets_header(self):
        self.authenticator._auth_header = "token"
        payload = []
        headers = {}

        await self.authenticator.outgoing(payload, headers)

        self.assertEqual(headers["Authorization"],
                         self.authenticator._auth_header)

    async def test_authenticate(self):
        response = {
            "token_type": "type",
            "access_token": "token"
        }
        status = HTTPStatus.OK
        self.authenticator._authenticate = mock.CoroutineMock(
            return_value=(status, response)
        )

        await self.authenticator.authenticate()

        self.assertEqual(self.authenticator._auth_response, response)
        self.assertEqual(
            self.authenticator._auth_header,
            response["token_type"] + " " + response["access_token"]
        )

    async def test_authenticate_non_ok_status_code(self):
        response = {
            "token_type": "type",
            "access_token": "token"
        }
        status = HTTPStatus.BAD_REQUEST
        self.authenticator._authenticate = mock.CoroutineMock(
            return_value=(status, response)
        )

        with self.assertRaisesRegex(AuthenticationError,
                                    "Authentication failed"):
            await self.authenticator.authenticate()

        self.assertIsNone(self.authenticator._auth_response)
        self.assertIsNone(self.authenticator._auth_header)

    async def test_authenticate_on_network_error(self):
        self.authenticator._authenticate = mock.CoroutineMock(
            side_effect=ClientError()
        )

        with self.assertRaisesRegex(AuthenticationError,
                                    "Network request failed"):
            await self.authenticator.authenticate()

        self.assertIsNone(self.authenticator._auth_response)
        self.assertIsNone(self.authenticator._auth_header)

    async def test_incoming(self):
        payload = []
        headers = {}

        await self.authenticator.incoming(payload, headers)

        self.assertFalse(payload)
        self.assertFalse(headers)


class TestPasswordAuthenticator(TestCase):
    def setUp(self):
        self.authenticator = PasswordAuthenticator(consumer_key="id",
                                                   consumer_secret="secret",
                                                   username="username",
                                                   password="password")

    @mock.patch("aiosfstream.auth.ClientSession")
    async def test_authenticate(self, session_cls):
        status = object()
        response_data = object()
        response_obj = mock.MagicMock()
        response_obj.json = mock.CoroutineMock(return_value=response_data)
        response_obj.status = status
        session = mock.MagicMock()
        session.__aenter__ = mock.CoroutineMock(return_value=session)
        session.__aexit__ = mock.CoroutineMock()
        session.post = mock.CoroutineMock(return_value=response_obj)
        session_cls.return_value = session
        expected_data = {
            "grant_type": "password",
            "client_id": self.authenticator.client_id,
            "client_secret": self.authenticator.client_secret,
            "username": self.authenticator.username,
            "password": self.authenticator.password
        }

        result = await self.authenticator._authenticate()

        self.assertEqual(result, (status, response_data))
        session.post.assert_called_with(TOKEN_URL, data=expected_data)
        session.__aenter__.assert_called()
        session.__aexit__.assert_called()

    def test_repr(self):
        result = repr(self.authenticator)

        cls_name = type(self.authenticator).__name__
        auth = self.authenticator
        self.assertEqual(
            result,
            f"{cls_name}(consumer_key={reprlib.repr(auth.client_id)},"
            f"consumer_secret={reprlib.repr(auth.client_secret)}, "
            f"username={reprlib.repr(auth.username)}, "
            f"password={reprlib.repr(auth.password)})"
        )


class TestRefreshTokenAuthenticator(TestCase):
    def setUp(self):
        self.authenticator = RefreshTokenAuthenticator(
            consumer_key="id",
            consumer_secret="secret",
            refresh_token="refresh_token"
        )

    @mock.patch("aiosfstream.auth.ClientSession")
    async def test_authenticate(self, session_cls):
        status = object()
        response_data = object()
        response_obj = mock.MagicMock()
        response_obj.json = mock.CoroutineMock(return_value=response_data)
        response_obj.status = status
        session = mock.MagicMock()
        session.__aenter__ = mock.CoroutineMock(return_value=session)
        session.__aexit__ = mock.CoroutineMock()
        session.post = mock.CoroutineMock(return_value=response_obj)
        session_cls.return_value = session
        expected_data = {
            "grant_type": "refresh_token",
            "client_id": self.authenticator.client_id,
            "client_secret": self.authenticator.client_secret,
            "refresh_token": self.authenticator.refresh_token
        }

        result = await self.authenticator._authenticate()

        self.assertEqual(result, (status, response_data))
        session.post.assert_called_with(TOKEN_URL, data=expected_data)
        session.__aenter__.assert_called()
        session.__aexit__.assert_called()

    def test_repr(self):
        result = repr(self.authenticator)

        cls_name = type(self.authenticator).__name__
        auth = self.authenticator
        self.assertEqual(
            result,
            f"{cls_name}(consumer_key={reprlib.repr(auth.client_id)},"
            f"consumer_secret={reprlib.repr(auth.client_secret)}, "
            f"refresh_token={reprlib.repr(auth.refresh_token)})"
        )
