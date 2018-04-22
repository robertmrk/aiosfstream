API Reference
=============

.. py:currentmodule:: aiosfstream

Client
------

.. autoclass:: Client

    .. autocomethod:: open
    .. autocomethod:: close
    .. autocomethod:: publish
    .. autocomethod:: subscribe
    .. autocomethod:: unsubscribe
    .. autocomethod:: receive
    .. autoattribute:: closed
    .. autoattribute:: subscriptions
    .. autoattribute:: connection_type
    .. autoattribute:: pending_count
    .. autoattribute:: has_pending_messages

Authenticators
--------------

.. autoclass:: aiosfstream.auth.AuthenticatorBase

.. autoclass:: PasswordAuthenticator
    :members:

.. autoclass:: RefreshTokenAuthenticator
    :members:

Exceptions
----------

.. automodule:: aiosfstream.exceptions
    :members:
    :undoc-members:
