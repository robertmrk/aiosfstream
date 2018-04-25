Advanced Usage
==============

.. py:currentmodule:: aiosfstream

.. _replay_config:

Replay configuration
--------------------

Network failures
----------------

When a :py:obj:`Client` object is opened, it will try to maintain a continuous
connection in the background with the server. If any network failures happen
while waiting to :py:meth:`~Client.receive` messages, the client will reconnect
to the server transparently, it will resubscribe to the subscribed channels,
and continue to wait for incoming messages.

To avoid waiting for a server which went offline permanently, or in case of a
permanent network failure, a ``connection_timeout`` can be passed to the
:py:obj:`Client`, to limit how many seconds the client object should wait
before raising a :py:obj:`~exceptions.TransportTimeoutError` if it can't
reconnect to the server.

.. code-block:: python

    client = SalesforceStreamingClient(
        consumer_key="<consumer key>",
        consumer_secret="<consumer secret>",
        username="<username>",
        password="<password>",
        connection_timeout=60
    )
    await client.open()

    try:
        message = await client.receive()
    except TransportTimeoutError:
        print("Connection is lost with the server. "
              "Couldn't reconnect in 60 seconds.")

The defaul value is ``10`` seconds. If you pass ``None`` as the
``connection_timeout`` value, then the client will keep on trying indefinitely.

Prefetching
-----------

When a :py:obj:`Client` is opened it will start and maintain a connection in
the background with the server. It will start to fetch messages from the
server as soon as it's connected, even before :py:meth:`~Client.receive` is
called.

Prefetching messages has the advantage, that incoming messages will
wait in a buffer for users to consume them when :py:meth:`~Client.receive`
is called, without any delay.

To avoid consuming all the available memory by the incoming messages, which are
not consumed yet, the number of prefetched messages can be limited with the
``max_pending_count`` parameter of the :py:obj:`Client`. The default value is
``100``.

.. code-block:: python

    client = SalesforceStreamingClient(
        consumer_key="<consumer key>",
        consumer_secret="<consumer secret>",
        username="<username>",
        password="<password>",
        max_pending_count=42
    )

The current number of messages waiting to be consumed can be obtained from the
:py:obj:`Client.pending_count` attribute.

.. include:: global.rst
