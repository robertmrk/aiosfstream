aiosfstream
===========

.. image:: https://badge.fury.io/py/aiosfstream.svg
    :target: https://badge.fury.io/py/aiosfstream
    :alt: PyPI package

.. image:: https://readthedocs.org/projects/aiosfstream/badge/?version=latest
    :target: http://aiosfstream.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://travis-ci.org/robertmrk/aiosfstream.svg?branch=develop
    :target: https://travis-ci.org/robertmrk/aiosfstream
    :alt: Build status

.. image:: https://coveralls.io/repos/github/robertmrk/aiosfstream/badge.svg
    :target: https://coveralls.io/github/robertmrk/aiosfstream
    :alt: Coverage

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT license

aiosfstream is a `Salesforce Streaming API <api_>`_ client for asyncio_. It can
be used to receive push notifications about changes on Salesforce objects or
notifications of general events sent through the `Streaming API <api_>`_.

For detailed guidance on how to work with `PushTopics <PushTopic_>`_ or how
to create `Generic Streaming Channels <GenericStreaming_>`_ please consult the
`Streaming API documentation <api_>`_.

Features
--------

- Supported authentication types:
   - using a username and password
   - using a refresh token
- Subscribe to and receive messages on:
    - `PushTopics <PushTopic_>`_
    - `Generic Streaming Channels <GenericStreaming_>`_
- Support for `durable messages and replay of events <replay_>`_
- Automatic recovery from replay errors

Usage
-----

.. code-block:: python

    import asyncio

    from aiosfstream import SalesforceStreamingClient


    async def stream_events():
        # connect to Streaming API
        async with SalesforceStreamingClient(
                consumer_key="<consumer key>",
                consumer_secret="<consumer secret>",
                username="<username>",
                password="<password>") as client:

            # subscribe to topics
            await client.subscribe("/topic/one")
            await client.subscribe("/topic/two")

            # listen for incoming messages
            async for message in client:
                topic = message["channel"]
                data = message["data"]
                print(f"{topic}: {data}")

    if __name__ == "__main__":
        loop = asyncio.get_event_loop()
        loop.run_until_complete(stream_events())

Documentation
-------------

http://aiosfstream.readthedocs.io/

.. _aiohttp: https://github.com/aio-libs/aiohttp/
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _api: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm
.. _PushTopic: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/working_with_pushtopics.htm
.. _GenericStreaming: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/generic_streaming_intro.htm#generic_streaming_intro
.. _replay: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/using_streaming_api_durability.htm
