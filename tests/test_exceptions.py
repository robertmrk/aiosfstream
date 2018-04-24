from asynctest import TestCase

import aiocometd.exceptions as cometd_exc

import aiosfstream.exceptions as exc


class TestExceptionHierarchy(TestCase):
    def test_root_exception(self):
        issubclass(exc.AiosfstreamException,
                   cometd_exc.AiocometdException)

    def test_authentication_error(self):
        issubclass(exc.AiosfstreamException,
                   exc.AuthenticationError)

    def test_transport_invalid_operation(self):
        issubclass(exc.TransportInvalidOperation,
                   exc.AiosfstreamException)
        issubclass(exc.TransportInvalidOperation,
                   exc.TransportError)
        issubclass(exc.TransportInvalidOperation,
                   cometd_exc.TransportInvalidOperation)

    def test_transport_timeout(self):
        issubclass(exc.TransportTimeoutError,
                   exc.AiosfstreamException)
        issubclass(exc.TransportTimeoutError,
                   exc.TransportError)
        issubclass(exc.TransportTimeoutError,
                   cometd_exc.TransportTimeoutError)

    def test_connection_closed(self):
        issubclass(exc.TransportConnectionClosed,
                   exc.AiosfstreamException)
        issubclass(exc.TransportConnectionClosed,
                   exc.TransportError)
        issubclass(exc.TransportConnectionClosed,
                   cometd_exc.TransportConnectionClosed)

    def test_server_error(self):
        issubclass(exc.ServerError,
                   exc.AiosfstreamException)
        issubclass(exc.ServerError,
                   cometd_exc.ServerError)

    def test_client_error(self):
        issubclass(exc.ClientError,
                   exc.AiosfstreamException)
        issubclass(exc.ClientError,
                   cometd_exc.ClientError)

    def test_client_invalid_operation(self):
        issubclass(exc.ClientInvalidOperation,
                   exc.AiosfstreamException)
        issubclass(exc.ClientInvalidOperation,
                   exc.ClientError)
        issubclass(exc.ClientInvalidOperation,
                   cometd_exc.ClientInvalidOperation)


class TestTranslateError(TestCase):
    def test_returns_result_on_no_error(self):
        return_value = object()

        result = exc.translate_errors(lambda: return_value)()

        self.assertIs(result, return_value)

    async def test_async_returns_result_on_no_error(self):
        return_value = object()

        async def func():
            return return_value

        result = await exc.translate_errors(func)()

        self.assertIs(result, return_value)

    def test_reraises_non_cometd_error(self):
        def raise_error():
            raise ValueError()

        with self.assertRaises(ValueError):
            exc.translate_errors(raise_error)()

    async def test_async_reraises_non_cometd_error(self):
        async def raise_error():
            raise ValueError()

        with self.assertRaises(ValueError):
            await exc.translate_errors(raise_error)()

    def test_translates_cometd_error(self):
        response = {
            "error": "400:arg1,arg2:description"
        }
        error = cometd_exc.ServerError("Message", response)

        def raise_error():
            raise error

        with self.assertRaises(exc.ServerError) as cm:
            exc.translate_errors(raise_error)()

        self.assertEqual(cm.exception.args, error.args)

    async def test_async_translates_cometd_error(self):
        response = {
            "error": "400:arg1,arg2:description"
        }
        error = cometd_exc.ServerError("Message", response)

        async def raise_error():
            raise error

        with self.assertRaises(exc.ServerError) as cm:
            await exc.translate_errors(raise_error)()

        self.assertEqual(cm.exception.args, error.args)
