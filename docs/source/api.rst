API Reference
=============

.. py:currentmodule:: aiosfstream

Client
------

.. autoclass:: SalesforceStreamingClient

.. autoclass:: Client
    :members:
    :undoc-members:

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

.. autoclass:: ReplayMarkerStoragePolicy
    :members:
    :undoc-members:

Authenticators
--------------

.. autoclass:: aiosfstream.auth.AuthenticatorBase

.. autoclass:: PasswordAuthenticator
    :members:

.. autoclass:: RefreshTokenAuthenticator
    :members:


Replay
------

.. autoclass:: ReplayOption
    :members:
    :undoc-members:

.. autoclass:: ReplayMarker
    :members:
    :show-inheritance:

.. autoclass:: ReplayMarkerStorage

    .. autocomethod:: get_replay_marker
    .. autocomethod:: set_replay_marker
    .. autocomethod:: extract_replay_id
    .. autocomethod:: __call__

.. autoclass:: MappingStorage

.. autoclass:: DefaultMappingStorage

.. autoclass:: ConstantReplayId

Exceptions
----------

.. automodule:: aiosfstream.exceptions

.. py:currentmodule:: aiosfstream.exceptions

.. autoexception:: AiosfstreamException
    :members:

.. autoexception:: AuthenticationError
    :members:

.. autoexception:: ClientError
    :members:

.. autoexception:: ClientInvalidOperation
    :members:

.. autoexception:: TransportError
    :members:

.. autoexception:: TransportInvalidOperation
    :members:

.. autoexception:: TransportTimeoutError
    :members:

.. autoexception:: TransportConnectionClosed
    :members:

.. autoexception:: ServerError
    :members:

    .. autoattribute:: message
    .. autoattribute:: response
    .. autoattribute:: error
    .. autoattribute:: error_code
    .. autoattribute:: error_args
    .. autoattribute:: error_message

.. autoexception:: ReplayError
    :members:
