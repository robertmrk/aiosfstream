Changelog
=========

0.1.0 (2018-04-26)
------------------

- Supported authentication types:
   - using a username and password
   - using a refresh token
- Subscribe to and receive messages on:
    - `PushTopics <PushTopic_>`_
    - `Generic Streaming Channels <GenericStreaming_>`_
- Support for `durable messages and replay of events <replay_>`_
- Automatic recovery from replay errors

.. _aiohttp: https://github.com/aio-libs/aiohttp/
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _api: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm
.. _PushTopic: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/working_with_pushtopics.htm
.. _GenericStreaming: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/generic_streaming_intro.htm#generic_streaming_intro
.. _replay: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/using_streaming_api_durability.htm
