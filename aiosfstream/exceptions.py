"""Exception types

Exception hierarchy::

    AiosfstreamException
        AuthenticationError
        ClientError
            ClientInvalidOperation
        TransportError
            TransportInvalidOperation
            TransportTimeoutError
            TransportConnectionClosed
        ServerError
"""
from functools import wraps
import asyncio

import aiocometd.exceptions as cometd_exc


# pylint: disable=too-many-ancestors

class AiosfstreamException(cometd_exc.AiocometdException):
    """Base exception type.

    All exceptions of the package inherit from this class.
    """


class AuthenticationError(AiosfstreamException):
    """Authentication failure"""


class TransportError(AiosfstreamException, cometd_exc.TransportError):
    """Error during the transportation of messages"""


class TransportInvalidOperation(TransportError,
                                cometd_exc.TransportInvalidOperation):
    """The requested operation can't be executed on the current state of the
    transport"""


class TransportTimeoutError(TransportError,
                            cometd_exc.TransportTimeoutError):
    """Transport timeout"""


class TransportConnectionClosed(TransportError,
                                cometd_exc.TransportConnectionClosed):
    """The connection unexpectedly closed"""


class ServerError(AiosfstreamException,
                  cometd_exc.ServerError):
    """Streaming API server side error

    If the *response* contains an error field it gets parsed
    according to the \
    `specs <https://docs.cometd.org/current/reference/#_code_error_code>`_

    :param str message: Error description
    :param dict response: Server response message
    """


class ClientError(AiosfstreamException,
                  cometd_exc.ClientError):
    """Client side error"""


class ClientInvalidOperation(ClientError,
                             cometd_exc.ClientInvalidOperation):
    """The requested operation can't be executed on the current state of the
    client"""

# pylint: enable=too-many-ancestors


EXCEPTION_PAIRS = {
    cometd_exc.AiocometdException: AiosfstreamException,
    cometd_exc.TransportError: TransportError,
    cometd_exc.TransportInvalidOperation: TransportInvalidOperation,
    cometd_exc.TransportTimeoutError: TransportTimeoutError,
    cometd_exc.TransportConnectionClosed: TransportConnectionClosed,
    cometd_exc.ServerError: ServerError,
    cometd_exc.ClientError: ClientError,
    cometd_exc.ClientInvalidOperation: ClientInvalidOperation
}


def translate_errors(func):
    """Function decorator for translating the raised aiocometd \
    errors to their aiosfstream counterparts

    As every properly behaving library, aiosfstream uses its own exception
    hierarchy, just as aiocometd does. The problem is that for the users of
    the library, it can be very confusing to deal with more then a single
    exception hierarchy, so aiocometd exceptions should be tranlated to
    aiosfstream exceptions. (unfortunately we can't make aiosfstream exceptions
    the virtual base class of aiocometd exceptions, since exception handling
    only looks at the __mro__ to find the base class, we have no choice but to
    redefine the same exceptions)

    :param func: The wrapped function
    :return: The function wrapper
    """
    # pylint: disable=missing-docstring
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except cometd_exc.AiocometdException as cometd_error:
            error_cls = EXCEPTION_PAIRS[type(cometd_error)]
            raise error_cls(*cometd_error.args) from cometd_error
        except Exception:
            raise

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except cometd_exc.AiocometdException as cometd_error:
            error_cls = EXCEPTION_PAIRS[type(cometd_error)]
            raise error_cls(*cometd_error.args) from cometd_error
        except Exception:
            raise

    # pylint: enable=missing-docstring

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return wrapper
