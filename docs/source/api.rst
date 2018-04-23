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


Replay
------

.. autoclass:: aiosfstream.replay.ReplayOption
    :members:
    :undoc-members:

.. autoclass:: aiosfstream.replay.ReplayMarker
    :members:
    :show-inheritance:

.. autoclass:: aiosfstream.replay.ReplayMarkerStorage

    .. autocomethod:: get_replay_marker
    .. autocomethod:: set_replay_marker

.. autoclass:: aiosfstream.replay.MappingStorage

.. autoclass:: aiosfstream.replay.DefaultMappingStorage

.. autoclass:: aiosfstream.replay.ConstantReplayId

Exceptions
----------

.. automodule:: aiosfstream.exceptions
    :members:
    :undoc-members:
