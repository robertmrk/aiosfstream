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
        ReplayError
"""
from functools import wraps
import asyncio
import contextlib
from typing import Generator, Callable, TypeVar, Any, cast

import aiocometd.exceptions as cometd_exc


FuncType = Callable[..., Any]
Func = TypeVar('Func', bound=FuncType)


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


class ReplayError(AiosfstreamException):
    """Message replay related error"""

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


@contextlib.contextmanager
def translate_errors_context() -> Generator[None, None, None]:
    """Context manager for translating the raised aiocometd \
    errors to their aiosfstream counterparts

    As every properly behaving library, aiosfstream uses its own exception
    hierarchy, just as aiocometd does. The problem is that for the users of
    the library, it can be very confusing to deal with more then a single
    exception hierarchy, so aiocometd exceptions should be tranlated to
    aiosfstream exceptions. (unfortunately we can't make aiosfstream exceptions
    the virtual base class of aiocometd exceptions, since exception handling
    only looks at the __mro__ to find the base class, we have no choice but to
    redefine the same exceptions)
    """
    try:
        yield
    except AiosfstreamException:
        raise
    except cometd_exc.AiocometdException as cometd_error:
        error_cls = EXCEPTION_PAIRS[type(cometd_error)]
        raise error_cls(*cometd_error.args) from cometd_error


def translate_errors(func: Func) -> Func:
    """Function decorator for translating the raised aiocometd \
    errors to their aiosfstream counterparts

    :param func: Function or coroutine function
    :return: The wrapped function
    """
    if not asyncio.iscoroutinefunction(func):
        # for non coroutine functions use the context manager as a decorator
        # pylint: disable=not-callable
        return cast(Func, translate_errors_context()(func))
        # pylint: enable=not-callable

    # pylint: disable=missing-docstring
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        with translate_errors_context():
            return await func(*args, **kwargs)

    # pylint: enable=missing-docstring
    return cast(Func, async_wrapper)
