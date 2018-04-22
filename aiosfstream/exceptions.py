"""Exception types

Exception hierarchy::

    AiosfstreamException
        AuthenticationError
"""


class AiosfstreamException(Exception):
    """Base exception type.

    All exceptions of the package inherit from this class.
    """


class AuthenticationError(AiosfstreamException):
    """Authentication failure"""
