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
        connection_timeout = 20
        max_pending_count = 1
        loop = object()
        client = Client(self.authenticator,
                        connection_timeout=connection_timeout,
                        max_pending_count=max_pending_count,
                        loop=loop)

        self.assertEqual(client.url, "")
        self.assertEqual(client.auth, self.authenticator)
        self.assertEqual(client.connection_timeout, connection_timeout)
        self.assertEqual(client._max_pending_count, max_pending_count)
        self.assertEqual(client._loop, loop)

    @mock.patch("aiosfstream.client.CometdClient.open")
    @mock.patch("aiosfstream.client.get_cometd_url")
    async def test_open(self, get_cometd_url, super_open):
        get_cometd_url.return_value = "url"

        await self.client.open()

        self.authenticator.authenticate.assert_called()
        self.assertEqual(self.client.url, get_cometd_url.return_value)
        super_open.assert_called()
