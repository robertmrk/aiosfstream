from asynctest import TestCase, mock

from aiosfstream.client import Client, get_cometd_url, COMETD_PATH, \
    API_VERSION
from aiosfstream.auth import AuthenticatorBase


class TestGetCometdUrl(TestCase):
    def test_get(self):
        instance_url = "instance"

        result = get_cometd_url(instance_url)

        self.assertEqual(result,
                         instance_url + "/" + COMETD_PATH + "/" + API_VERSION)


class TestClient(TestCase):
    def setUp(self):
        self.authenticator = mock.create_autospec(AuthenticatorBase)
        self.client = Client(self.authenticator)

    def test_init(self):
        client = Client(self.authenticator)

        self.assertEqual(client.url, "")
        self.assertEqual(client.auth, self.authenticator)

    @mock.patch("aiosfstream.client.CometdClient.open")
    @mock.patch("aiosfstream.client.get_cometd_url")
    async def test_open(self, get_cometd_url, super_open):
        get_cometd_url.return_value = "url"

        await self.client.open()

        self.authenticator.authenticate.assert_called()
        self.assertEqual(self.client.url, get_cometd_url.return_value)
        super_open.assert_called()
