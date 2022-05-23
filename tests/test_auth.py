import reprlib
import time
from http import HTTPStatus
import jwt
from aiohttp.client_exceptions import ClientError
from asynctest import TestCase, mock

from aiosfstream.auth import AuthenticatorBase, PasswordAuthenticator, \
    TOKEN_URL, SANDBOX_TOKEN_URL, RefreshTokenAuthenticator, JWTAuthenticator
from aiosfstream.exceptions import AuthenticationError


class Authenticator(AuthenticatorBase):
    async def _authenticate(self):
        return {}


class TestAuthenticatorBase(TestCase):
    def setUp(self):
        self.authenticator = Authenticator()

    def test_init(self):
        json_dumps = object()
        json_loads = object()

        auth = Authenticator(json_dumps=json_dumps, json_loads=json_loads)

        self.assertIs(auth.json_dumps, json_dumps)
        self.assertIs(auth.json_loads, json_loads)

    async def test_outgoing_sets_header(self):
        self.authenticator.token_type = "Bearer"
        self.authenticator.access_token = "token"
        payload = []
        headers = {}

        await self.authenticator.outgoing(payload, headers)

        self.assertEqual(headers["Authorization"],
                         self.authenticator.token_type + " " +
                         self.authenticator.access_token)

    async def test_outgoing_error_when_called_without_authentication(self):
        payload = []
        headers = {}

        with self.assertRaisesRegex(AuthenticationError,
                                    "Unknown token_type and access_token "
                                    "values. Method called without "
                                    "authenticating first."):
            await self.authenticator.outgoing(payload, headers)

    async def test_authenticate(self):
        response = {
            "id": "id_url",
            "issued_at": "1278448832702",
            "instance_url": "https://yourInstance.salesforce.com/",
            "signature": "signature_value",
            "access_token": "token",
            "token_type": "Bearer"
        }
        status = HTTPStatus.OK
        self.authenticator._authenticate = mock.CoroutineMock(
            return_value=(status, response)
        )

        await self.authenticator.authenticate()

        self.assertEqual(self.authenticator.id,
                         response["id"])
        self.assertEqual(self.authenticator.issued_at,
                         response["issued_at"])
        self.assertEqual(self.authenticator.instance_url,
                         response["instance_url"])
        self.assertEqual(self.authenticator.signature,
                         response["signature"])
        self.assertEqual(self.authenticator.access_token,
                         response["access_token"])
        self.assertEqual(self.authenticator.token_type,
                         response["token_type"])

    async def test_authenticate_non_ok_status_code(self):
        response = {
            "id": "id_url",
            "issued_at": "1278448832702",
            "instance_url": "https://yourInstance.salesforce.com/",
            "signature": "signature_value",
            "access_token": "token",
            "token_type": "Bearer"
        }
        status = HTTPStatus.BAD_REQUEST
        self.authenticator._authenticate = mock.CoroutineMock(
            return_value=(status, response)
        )

        with self.assertRaisesRegex(AuthenticationError,
                                    "Authentication failed"):
            await self.authenticator.authenticate()

        self.assertIsNone(self.authenticator.id)
        self.assertIsNone(self.authenticator.issued_at)
        self.assertIsNone(self.authenticator.instance_url)
        self.assertIsNone(self.authenticator.signature)
        self.assertIsNone(self.authenticator.access_token)
        self.assertIsNone(self.authenticator.token_type)

    async def test_authenticate_on_network_error(self):
        self.authenticator._authenticate = mock.CoroutineMock(
            side_effect=ClientError()
        )

        with self.assertRaisesRegex(AuthenticationError,
                                    "Network request failed"):
            await self.authenticator.authenticate()

        self.assertIsNone(self.authenticator.id)
        self.assertIsNone(self.authenticator.issued_at)
        self.assertIsNone(self.authenticator.instance_url)
        self.assertIsNone(self.authenticator.signature)
        self.assertIsNone(self.authenticator.access_token)
        self.assertIsNone(self.authenticator.token_type)

    async def test_incoming(self):
        payload = []
        headers = {}

        await self.authenticator.incoming(payload, headers)

        self.assertFalse(payload)
        self.assertFalse(headers)

    def test_token_url_non_sandbox(self):
        auth = Authenticator()

        self.assertEqual(auth._token_url, TOKEN_URL)

    def test_token_url_sandbox(self):
        auth = Authenticator(sandbox=True)

        self.assertEqual(auth._token_url, SANDBOX_TOKEN_URL)


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
        session_cls.assert_called_with(
            json_serialize=self.authenticator.json_dumps
        )
        session.post.assert_called_with(self.authenticator._token_url,
                                        data=expected_data)
        response_obj.json.assert_called_with(
            loads=self.authenticator.json_loads
        )
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
        session_cls.assert_called_with(
            json_serialize=self.authenticator.json_dumps
        )
        session.post.assert_called_with(self.authenticator._token_url,
                                        data=expected_data)
        response_obj.json.assert_called_with(
            loads=self.authenticator.json_loads
        )
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


class TestJWTAuthenticator(TestCase):
    def setUp(self):
        self.authenticator = JWTAuthenticator(
            consumer_key="id",
            username="username",
            private_key="""-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCT/YuMSf0WinGx
MS7TO3ssO3iLYwAlJa97yUSKXDbYX2QwFDng4a9OkAvUxf4pxvppy85+97/LY5W7
kQ0zxnn4VD12UvA5iL3X1GgUUfqyG56CbYVJP2livmR5cERrtxxg1dA3hhbFP8l1
JllsgNAi0KWfxi9Do0HPSDRmE4/4Dr9MsPmvcUTw7cVs+VVz8RDHWbMB7ptJb+30
Qwmp81XTecysVpxEs/ZcSo5ej4vNqjGwERSEoWDu3CY2SoRAaUvDP1xBgvOo7w2q
pSrBxo36t0iQxSg0q1JcyDncD0jHH8qYEm6ZbjdAGbaXqz1DAXECJcjh5yeiWTPn
uI0I6lltAgMBAAECggEAZmhys87Tc1C0YiCdvZCQqMgyn4oPpKUSbT+WzYQIc+x2
4QpuDt89t8jYVxH30qMd0C43pAb/UtiD2fsDPsvexWhN695y2+1zKbKTn1Qnfi68
npb5P/nAjJMh5iM5Ray914i+AF4qza5ZU1cJVJtC7ISjyA+Vz2Fe/fiCQgzReJ52
gc5KuOhF/0FBZtOvhqVubJYxngpZCGfpUi28MyN+f6fYm4vtvkDZLJETb+LcyR4M
inlFu2hwl+ZVXIXM8EybPyBphSzUszCUPnw20rVJRu2HWF0kE7jC3+BS5rBcaWoJ
qboGbrpbHl1AGnav3c+o3/JUr+TqoE+qwclwpimFBQKBgQDDNclovApsokScEsqX
RI/UD1WwgWKIztoRkPBCsJpLQPGv8eJJI25HWePQN6NzN8inKY0SO7+UN5u32Yg6
AWUWvAs2IVH17Y88YkbET2kQEX1kYVga6dCSnN2h98yED26+NtJq6kGVjswUZVU8
yG4cweZtR5JL+avTltBiIrL1MwKBgQDCE2ORym5uo18rsFQKyiJGJrmMGwTX8WvZ
BexWfVfhaMNwLgHcvrWp91d2TfL5LAStOLDoL0amlTggRDsqmy1N5S8fEPzfc+oY
4EZkDzT9dJZnRVHUdfLA1HOFnQ+L4Xd296ors7seuN71NLU9dRjWYlXsIe88gacW
ZOCW93o23wKBgBB7EQcLoSGszXgTyhDdU/tGVCizs7rzI8wJ3Y7z1AL4d68wD7e3
Cw9xEl+44s7Obd1XD7bzXmhIDZiHAA5Nodg6hgPK6l2F8eraLTlTrv4RS/HWmhaj
mN1X6wpKnnSjzOi4PimSn3jd9nLeX0TjcxBwemDNgxdw+8XAXNV8MnmrAoGABK0I
6htRe9Lt2RSfgb8LAluufsSr4jQL4Ce3YQIWGvU2OD6zhskFgXnXHp+UKhK4bh/+
iymQbzULLCPYtRcWCVlrQDldjlixnDXTHFgNc8naUdSmuxK4bZLw0ZhOJpWhFjmz
XOgwqvXTUV8ausdWeNvXrB/JLtEE4JI/owOFa0sCgYAY5jeBany8hIBQqAlnb6Ab
ZH+xkHDKhBWU6UWBHfJuZNVsGSLDYuZELyJ+tejy6gDffEjxAAps3ZxTe9Pae4WL
5oMTFlZd2r2yfjSplVPPhJwq07FXQJ89UlgGLuNrqSUsntImjSmqrC1Hy9owJvyU
GP6HlmVV5x1WaBt0HxRLXg==
-----END PRIVATE KEY-----
""")

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
        claim = {
            'iss': self.authenticator.client_id,
            'exp': int(time.time()) + 300,
            'aud': 'https://login.salesforce.com',
            'sub': self.authenticator.username,
        }
        assertion = jwt.encode(claim, self.authenticator.private_key, algorithm='RS256', headers={
            'alg': 'RS256'})
        expected_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }

        result = await self.authenticator._authenticate()

        self.assertEqual(result, (status, response_data))
        session_cls.assert_called_with(
            json_serialize=self.authenticator.json_dumps
        )
        session.post.assert_called_with(self.authenticator._token_url,
                                        data=expected_data)
        response_obj.json.assert_called_with(
            loads=self.authenticator.json_loads
        )
        session.__aenter__.assert_called()
        session.__aexit__.assert_called()

    def test_repr(self):
        result = repr(self.authenticator)

        cls_name = type(self.authenticator).__name__
        auth = self.authenticator
        self.assertEqual(
            result,
            f"{cls_name}(consumer_key={reprlib.repr(auth.client_id)},"
            f"username={reprlib.repr(auth.username)}, "
            f"private_key={reprlib.repr(auth.private_key)})"
        )
