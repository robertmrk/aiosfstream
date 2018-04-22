from asynctest import TestCase, mock

from aiosfstream.auth import AuthenticatorBase


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
