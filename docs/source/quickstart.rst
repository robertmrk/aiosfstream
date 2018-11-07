Quickstart
==========

.. py:currentmodule:: aiosfstream

Authentication
--------------

To connect to the `Salesforce Streaming API <api_>`_ all clients must
authenticate themselves. The library supports the
`username-password <password_auth_>`_ based OAuth2 authentication flow as well
as the `refresh token <refresh_auth_>`_ based authentication.

Whichever technique you end up using, you must first create a
`Connected App <connected_app_>`_ on Salesforce to acquire a Consumer Key and
Consumer Secret value. Which are actually the client_id and client_secret
parameters in OAuth2 terminology.

Username-Password authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For username-password based authentication you can use the
:py:obj:`SalesforceStreamingClient` class, with the Salesforce user's
username and password:

.. code-block:: python

    client = SalesforceStreamingClient(
        consumer_key="<consumer key>",
        consumer_secret="<consumer secret>",
        username="<username>",
        password="<password>"
    )

:py:obj:`SalesforceStreamingClient` is actually just a convenience class,
based on :py:obj:`Client`. It enables you to create a client object
with the most common authentication technique, without having to create a
separate :py:obj:`PasswordAuthenticator` object. You can actually use the
:py:obj:`Client` class to create client that would be equivalent with the
example above:

.. code-block:: python

    auth = PasswordAuthenticator(
        consumer_key="<consumer key>",
        consumer_secret="<consumer secret>",
        username="<username>",
        password="<password>"
    )
    client = Client(auth)

Refresh token authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The refresh token base authentication technique can be used by creating
a :py:obj:`RefreshTokenAuthenticator` and passing it to the :py:obj:`Client`
class:

.. code-block:: python

    auth = RefreshTokenAuthenticator(
        consumer_key="<consumer key>",
        consumer_secret="<consumer secret>",
        refresh_token="<refresh_token>"
    )
    client = Client(auth)

You can get a refresh token using several different `authentication techniques
supported by Salesforce <sf_auth_>`_, the most commonly used one is probably
the `web server authentication flow <web_server_auth_>`_.

Authentication on sandbox orgs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're trying to connect to a sandbox org, then you have to assign
``True`` to the ``sandbox`` parameter when creating the
:py:obj:`SalesforceStreamingClient`, :py:obj:`PasswordAuthenticator` or
:py:obj:`RefreshTokenAuthenticator` object. Furthermore, the name of the
sandbox should be appended to the username. For example, if a username for a
production org is user1@acme.com, and the sandbox is named `test`, the modified
username to log in to the sandbox is user1@acme.com.test.

.. code-block:: python

    client = SalesforceStreamingClient(
        consumer_key="<consumer key>",
        consumer_secret="<consumer secret>",
        username="<username>.<sandbox_name>",
        password="<password>",
        sandbox=True
    )

Connecting
----------

After creating a :py:class:`Client` object the :py:meth:`~Client.open` method
should be called to establish a connection with the server. The connection is
closed and the session is terminated by calling the :py:meth:`~Client.close`
method.

.. code-block:: python

    client = SalesforceStreamingClient(
        consumer_key="<consumer key>",
        consumer_secret="<consumer secret>",
        username="<username>",
        password="<password>"
    )
    await client.open()
    # subscribe and receive messsages...
    await client.close()

:py:class:`Client` objects can be also used as asynchronous context managers.

.. code-block:: python

    async with SalesforceStreamingClient(
            consumer_key="<consumer key>",
            consumer_secret="<consumer secret>",
            username="<username>",
            password="<password>") as client:
        # subscribe and receive messsages...

Channels
--------

A channel is a string that looks like a URL path such as ``/topic/foo`` or
``/topic/bar``.

For detailed guidance on how to work with `PushTopics <PushTopic_>`_ or how
to create `Generic Streaming Channels <GenericStreaming_>`_ please consult the
`Streaming API documentation <api_>`_.

Subscriptions
-------------

To receive notification messages the client must subscribe to the channels
it's interested in.

.. code-block:: python

    await client.subscribe("/topic/foo")

If you no longer want to receive messages from one of the channels you're
subscribed to then you must unsubscribe from the channel.

.. code-block:: python

    await client.unsubscribe("/topic/foo")

The current set of subscriptions can be obtained from the
:obj:`Client.subscriptions` attribute.

Receiving messages
------------------

To receive messages broadcasted by Salesforce after
`subscribing <Subscriptions_>`_ to these `channels <Channels_>`_ the
:py:meth:`~Client.receive` method should be used.

.. code-block:: python

    message = await client.receive()

The :py:meth:`~Client.receive` method will wait until a message is received
or it will raise a :py:obj:`~exceptions.TransportTimeoutError` in case the
connection is lost with the server and the client can't re-establish the
connection or a :py:obj:`~exceptions.ServerError` if the connection gets
closed by the server.

The client can also be used as an asynchronous iterator in a for loop to wait
for incoming messages.

.. code-block:: python

    async for message in client:
        # process message

Replay of events
----------------

The great thing about streaming is that the client gets instantly notified
about events as they occur. The downside is that if the client becomes
temporarily disconnected, due to hardware, software or network failure, then
it might miss some of the messages emitted by the server. This is where
Salesforce's message durability comes in handy.

Salesforce stores events for 24 hours. Events outside the 24-hour retention
period are discarded. Salesforce extends the event messages with ``repalyId``
and ``createdDate`` fields (called as :py:obj:`ReplayMarker` by aiosfstream).
These fields can be used by the client to request the missed event messages
from the server when it reconnects.

The default behavior of the client is to receive only the new events sent after
subscribing. To take advantage of message durability, all you have to do is to
pass an object capable of storing the most recent :py:obj:`ReplayMarker`
objects, so the next time the client reconnects, it can continue to process
event messages from the point where it left off. The most convenient
choice is a :py:obj:`~shelve.Shelf` object, which can store
:py:obj:`ReplayMarkers <ReplayMarker>` on the disk, between application
restarts.

.. code-block:: python

        with shelve.open("replay.db") as replay:

            async with SalesforceStreamingClient(
                consumer_key="<consumer key>",
                consumer_secret="<consumer secret>",
                username="<username>",
                password="<password>",
                replay=replay) as client:

                await client.subscribe("/topic/foo")

                async for message in client:
                    # process message

Besides :py:obj:`~shelve.Shelf` objects you can pass a lot of different kind
of objects to the replay parameter, and you can configure different aspects of
replay behavior as well. For a full description of replay configuration
options check out the :ref:`replay_config` section.

.. include:: global.rst
