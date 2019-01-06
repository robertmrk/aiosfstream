"""Client class implementation"""
from collections import abc
from http import HTTPStatus
import logging
import json
import asyncio
from typing import Optional, Union, MutableMapping, AsyncIterator, Type, cast
from types import TracebackType
from enum import Enum, auto, unique

from aiocometd import Client as CometdClient
from aiocometd.exceptions import ServerError
from aiocometd.typing import JsonObject, JsonLoader, JsonDumper

from aiosfstream.auth import AuthenticatorBase, PasswordAuthenticator
from aiosfstream.replay import ReplayOption, ReplayMarkerStorage, \
    MappingStorage, ConstantReplayId, ReplayMarker
from aiosfstream.exceptions import translate_errors, translate_errors_context


COMETD_PATH = "cometd"
API_VERSION = "42.0"
LOGGER = logging.getLogger(__name__)
ReplayParameter = Union[ReplayOption,
                        ReplayMarkerStorage,
                        MutableMapping[str, ReplayMarker]]


@unique
class ReplayMarkerStoragePolicy(Enum):
    """Defines the available replay marker storage policies"""
    #: Store the replay marker of messages automatically, as soon as they're
    #: received.
    #: The downside of this approach is that the replay marker of a message
    #: will be stored (thus marking it as successfully consumed) even if the
    #: processing of the message fails in the client side code
    AUTOMATIC = auto()
    #: Store the replay marker of messages manually, after the message has been
    #: successfully processed in client side code
    MANUAL = auto()


class Client(CometdClient):
    """Salesforce Streaming API client"""
    @translate_errors
    def __init__(self, authenticator: AuthenticatorBase, *,
                 replay: ReplayParameter = ReplayOption.NEW_EVENTS,
                 replay_fallback: Optional[ReplayOption] = None,
                 replay_storage_policy: ReplayMarkerStoragePolicy
                 = ReplayMarkerStoragePolicy.AUTOMATIC,
                 connection_timeout: Union[int, float] = 10.0,
                 max_pending_count: int = 100,
                 json_dumps: JsonDumper = json.dumps,
                 json_loads: JsonLoader = json.loads,
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        :param authenticator: An authenticator object
        :param replay: A ReplayOption or an object capable of storing replay \
        ids if you want to take advantage of Salesforce's replay extension. \
        You can use one of the :obj:`ReplayOptions <ReplayOption>`, or \
        an object that supports the MutableMapping protocol like :obj:`dict`, \
        :obj:`~collections.defaultdict`, :obj:`~shelve.Shelf` etc. or a \
        custom :obj:`ReplayMarkerStorage` implementation.
        :param replay_fallback: Replay fallback policy, for when a subscribe \
        operation fails because a replay id was specified for a message \
        outside the retention window
        :param replay_storage_policy: Defines at which point the \
        replay marker of received messages will be stored
        :param connection_timeout: The maximum amount of time to wait for the \
        transport to re-establish a connection with the server when the \
        connection fails.
        :param max_pending_count: The maximum number of messages to \
        prefetch from the server. If the number of prefetched messages reach \
        this size then the connection will be suspended, until messages are \
        consumed. \
        If it is less than or equal to zero, the count is infinite.
        :param json_dumps: Function for JSON serialization, the default is \
        :func:`json.dumps`
        :param json_loads: Function for JSON deserialization, the default is \
        :func:`json.loads`
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        if not isinstance(authenticator, AuthenticatorBase):
            raise TypeError(f"authenticator should be an instance of "
                            f"{AuthenticatorBase.__name__}.")
        #: Replay fallback policy, for when a subscribe
        #: operation fails because a replay id was specified for a message
        #: outside the retention window
        self.replay_fallback = replay_fallback

        replay_storage = self.create_replay_storage(replay)
        if not isinstance(replay_storage, ReplayMarkerStorage):
            raise TypeError("{!r} is not a valid type for the replay "
                            "parameter.".format(type(replay).__name__))
        #: :obj:`ReplayMarkerStorage` instance capable of storing
        #: :py:obj:`ReplayMarker` objects
        self.replay_storage: ReplayMarkerStorage = replay_storage

        #: Defines at which point the :py:obj:`ReplayMarker` of received
        #: messages will be stored
        self.replay_storage_policy = replay_storage_policy

        LOGGER.debug("Client created with replay storage: %r, "
                     "replay fallback: %r",
                     self.replay_storage,
                     self.replay_fallback)

        # update the JSON serializer/deserializer of the authenticator with
        # the callables passed to the client
        authenticator.json_dumps = json_dumps
        authenticator.json_loads = json_loads

        # set authenticator as the auth extension
        super().__init__("",
                         auth=authenticator,
                         extensions=[self.replay_storage],
                         connection_timeout=connection_timeout,
                         max_pending_count=max_pending_count,
                         json_dumps=json_dumps,
                         json_loads=json_loads,
                         loop=loop)

    @translate_errors
    async def open(self) -> None:
        """Establish a connection with the Streaming API endpoint

        :raise ClientError: If none of the connection types offered by the \
        server are supported
        :raise ClientInvalidOperation:  If the client is already open, or in \
        other words if it isn't :obj:`closed`
        :raise TransportError: If a network or transport related error occurs
        :raise ServerError: If the handshake or the first connect request \
        gets rejected by the server.
        :raise AuthenticationError: If the server rejects the authentication \
        request or if a network failure occurs during the authentication
        """
        authenticator = cast(AuthenticatorBase, self.auth)
        # authenticate
        LOGGER.debug("Authenticating using %r.", authenticator)
        await authenticator.authenticate()
        LOGGER.info("Successful authentication. Instance URL: %r.",
                    authenticator.instance_url)
        # construct the URL of the CometD endpoint using the instance URL
        self.url = self.get_cometd_url(cast(str, authenticator.instance_url))
        # open the CometD client
        await super().open()

    @translate_errors
    async def close(self) -> None:
        await super().close()

    @translate_errors
    async def subscribe(self, channel: str) -> None:
        try:
            await super().subscribe(channel)
        except ServerError as error:
            if (self.replay_fallback and self.replay_storage and
                    error.error_code == HTTPStatus.BAD_REQUEST):
                LOGGER.warning("Subscription failed with message: %r, "
                               "retrying subscription with %r.",
                               error.error_message,
                               self.replay_fallback)
                self.replay_storage.replay_fallback = self.replay_fallback
                await super().subscribe(channel)
            else:
                raise

    @translate_errors
    async def unsubscribe(self, channel: str) -> None:
        await super().unsubscribe(channel)

    @translate_errors
    async def publish(self, channel: str, data: JsonObject) -> JsonObject:
        """Publish *data* to the given *channel*

        .. warning::

            The Streaming API is implemented on top of CometD. The publish
            operation is a CometD operation. While it's still a legal
            operation, Salesforce chose not to implement the
            publishing of Generic Streaming and Platform events with CometD.

            You should use the `REST API to generate Generic Streaming events \
            <https://developer.salesforce.com/docs/\
            atlas.en-us.api_streaming.meta/api_streaming/\
            generate_event_using_rest.htm>`_,
            or use the `REST or SOAP API to publish Platform events <https://\
            developer.salesforce.com/docs/atlas.en-us.platform_events.meta/\
            platform_events/platform_events_publish_api.htm>`_.

        :param channel: Name of the channel
        :param data: Data to send to the server
        :return: Publish response
        :raise ClientInvalidOperation: If the client is :obj:`closed`
        :raise TransportError: If a network or transport related error occurs
        :raise ServerError: If the publish request gets rejected by the server
        """
        return await super().publish(channel, data)

    @translate_errors
    async def receive(self) -> JsonObject:
        """Wait for incoming messages from the server

        :return: Incoming message
        :raise ClientInvalidOperation: If the client is closed, and has no \
        more pending incoming messages
        :raise ServerError: If the client receives a confirmation message \
         which is not ``successful``
        :raise TransportTimeoutError: If the transport can't re-establish \
        connection with the server in :obj:`connection_timeout` time.
        :raise ReplayError: On a message replay or replay marker storage \
        related error
        """
        response = await super().receive()

        if self.replay_storage_policy == ReplayMarkerStoragePolicy.AUTOMATIC:
            # only extract the replay id from the message once we're sure that
            # it's going to be consumed (as opposed to extracting it when
            # its received), otherwise unconsumed messages might get
            # skipped if client reconnects with replay
            await self.replay_storage.extract_replay_id(response)
        return response

    @translate_errors
    async def __aiter__(self) -> AsyncIterator[JsonObject]:
        """Asynchronous iterator

        :raise ServerError: If the client receives a confirmation message \
         which is not ``successful``
        :raise TransportTimeoutError: If the transport can't re-establish \
        connection with the server in :obj:`connection_timeout` time.
        :raise ReplayError: On a message replay or replay marker storage \
        related error
        """
        with translate_errors_context():
            # pylint: disable=not-an-iterable
            async for message in super().__aiter__():
                # pylint: enable=not-an-iterable
                yield message

    @translate_errors
    async def __aenter__(self) -> "Client":
        return cast("Client", await super().__aenter__())

    @translate_errors
    async def __aexit__(self, exc_type: Type[BaseException],
                        exc_val: BaseException,
                        exc_tb: TracebackType) -> None:
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def create_replay_storage(replay_param: ReplayParameter) \
            -> Optional[ReplayMarkerStorage]:
        """Create a :obj:`ReplayMarkerStorage` object based from *replay_param*

        :param replay_param: One of the supported *replay_param* type objects
        :return: A new :obj:`ReplayMarkerStorage` object or *replay_param* if \
        it's already an instance of :obj:`ReplayMarkerStorage` object, or \
        None if *replay_param* is None
        """
        if isinstance(replay_param, ReplayMarkerStorage):
            return replay_param
        if isinstance(replay_param, abc.MutableMapping):
            return MappingStorage(replay_param)
        if isinstance(replay_param, ReplayOption):
            return ConstantReplayId(replay_param)
        return None

    @staticmethod
    def get_cometd_url(instance_url: str) -> str:
        """Get the CometD URL associated with the *instance_url*

        :param instance_url: Salesforce instance URL
        :return: CometD URL associated with the *instance_url*
        """
        return "/".join((instance_url, COMETD_PATH, API_VERSION))


class SalesforceStreamingClient(Client):
    """Salesforce Streaming API client with username/password authentication

    This is a convenience class which is suitable for the most common use case.
    To use a different authentication method, use the general :obj:`Client`
    class with a different
    :obj:`Authenticator <aiosfstream.auth.AuthenticatorBase>`
    """
    def __init__(self, *,  # pylint: disable=too-many-locals
                 consumer_key: str, consumer_secret: str,
                 username: str, password: str,
                 replay: ReplayParameter = ReplayOption.NEW_EVENTS,
                 replay_fallback: Optional[ReplayOption] = None,
                 replay_storage_policy: ReplayMarkerStoragePolicy
                 = ReplayMarkerStoragePolicy.AUTOMATIC,
                 connection_timeout: Union[int, float] = 10.0,
                 max_pending_count: int = 100, sandbox: bool = False,
                 json_dumps: JsonDumper = json.dumps,
                 json_loads: JsonLoader = json.loads,
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        :param consumer_key: Consumer key from the Salesforce connected \
        app definition
        :param consumer_secret: Consumer secret from the Salesforce \
        connected app definition
        :param username: Salesforce username
        :param password: Salesforce password
        :param replay: A ReplayOption or an object capable of storing replay \
        ids if you want to take advantage of Salesforce's replay extension. \
        You can use one of the :obj:`ReplayOptions <.ReplayOption>`, or \
        an object that supports the MutableMapping protocol like :obj:`dict`, \
        :obj:`~collections.defaultdict`, :obj:`~shelve.Shelf` etc. or a \
        custom :obj:`ReplayMarkerStorage` implementation.
        :param replay_fallback: Replay fallback policy, for when a subscribe \
        operation fails because a replay id was specified for a message \
        outside the retention window
        :param replay_storage_policy: Defines at which point the \
        replay marker of received messages will be stored
        :param connection_timeout: The maximum amount of time to wait for the \
        transport to re-establish a connection with the server when the \
        connection fails.
        :param max_pending_count: The maximum number of messages to \
        prefetch from the server. If the number of prefetched messages reach \
        this size then the connection will be suspended, until messages are \
        consumed. \
        If it is less than or equal to zero, the count is infinite.
        :param sandbox: Marks whether the connection has to be made with \
        a sandbox org or with a production org
        :param json_dumps: Function for JSON serialization, the default is \
        :func:`json.dumps`
        :param json_loads: Function for JSON deserialization, the default is \
        :func:`json.loads`
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        authenticator = PasswordAuthenticator(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            username=username,
            password=password,
            sandbox=sandbox,
            json_dumps=json_dumps,
            json_loads=json_loads,
        )
        super().__init__(
            authenticator,
            replay=replay,
            replay_fallback=replay_fallback,
            replay_storage_policy=replay_storage_policy,
            connection_timeout=connection_timeout,
            max_pending_count=max_pending_count,
            json_dumps=json_dumps,
            json_loads=json_loads,
            loop=loop
        )
