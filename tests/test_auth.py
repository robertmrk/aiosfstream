from asynctest import TestCase, mock

from aiosfstream.auth import AuthenticatorBase, PasswordAuthenticator, \
    TOKEN_URL


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
        self.authenticator._authenticate = mock.CoroutineMock(
            return_value=response
        )

        await self.authenticator.authenticate()

        self.assertEqual(self.authenticator._auth_response, response)
        self.assertEqual(
            self.authenticator._auth_header,
            response["token_type"] + " " + response["access_token"]
        )

    async def test_incoming(self):
        payload = []
        headers = {}

        await self.authenticator.incoming(payload, headers)

        self.assertFalse(payload)
        self.assertFalse(headers)


class TestPasswordAuthenticator(TestCase):
    def setUp(self):
        self.authenticator = PasswordAuthenticator(client_id="id",
                                                   client_secret="secret",
                                                   username="username",
                                                   password="password")

    @mock.patch("aiosfstream.auth.ClientSession")
    async def test_authenticate(self, session_cls):
        response = object()
        response_obj = mock.MagicMock()
        response_obj.json = mock.CoroutineMock(return_value=response)
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

        self.assertEqual(result, response)
        session.post.assert_called_with(TOKEN_URL, data=expected_data)
        session.__aenter__.assert_called()
        session.__aexit__.assert_called()
