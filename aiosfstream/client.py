"""Client class implementation"""
from collections import abc
from http import HTTPStatus

from aiocometd import Client as CometdClient
from aiocometd.exceptions import ServerError

from .auth import AuthenticatorBase
from .replay import ReplayOption, ReplayMarkerStorage, MappingStorage, \
    ConstantReplayId


COMETD_PATH = "cometd"
API_VERSION = "42.0"


class Client(CometdClient):
    """Salesforce Streaming API client"""
    def __init__(self, authenticator, *, replay=ReplayOption.NEW_EVENTS,
                 replay_fallback=None, connection_timeout=10.0,
                 max_pending_count=100, loop=None):
        """
        :param authenticator: An authenticator object
        :type authenticator: aiosfstream.auth.AuthenticatorBase
        :param replay: A ReplayOption or ann object capable of storing replay \
        ids if you want to take advantage of Salesforce's replay extension. \
        You can use one of the available :obj:`~replay.ReplayOption`s, or an \
        object that supports the MutableMapping protocol like :obj:`dict` or \
        :obj:`defaultdict`, :obj:`shelve.Shelf` etc., or a custom \
        :obj:`replay.ReplayMarkerStorage` implementation.
        :type replay: replay.ReplayOption, replay.ReplayMarkerStorage, \
        collections.abc.MutableMapping or None
        :param replay_fallback: Replay fallback policy, for when a subscribe \
        operation fails because of a way too old replay id
        :type replay: replay.ReplayOption
        :param connection_timeout: The maximum amount of time to wait for the \
        transport to re-establish a connection with the server when the \
        connection fails.
        :type connection_timeout: int, float or None
        :param int max_pending_count: The maximum number of messages to \
        prefetch from the server. If the number of prefetched messages reach \
        this size then the connection will be suspended, until messages are \
        consumed. \
        If it is less than or equal to zero, the count is infinite.
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        if not isinstance(authenticator, AuthenticatorBase):
            raise ValueError(f"authenticator should be an instance of "
                             f"{AuthenticatorBase.__name__}.")

        self.replay_fallback = replay_fallback

        extensions = None
        self.replay_storage = self.create_replay_storage(replay)
        if self.replay_storage:
            extensions = [self.replay_storage]

        # set authenticator as the auth extension
        super().__init__("",
                         auth=authenticator,
                         extensions=extensions,
                         connection_timeout=connection_timeout,
                         max_pending_count=max_pending_count,
                         loop=loop)

    async def open(self):
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
        # authenticate
        await self.auth.authenticate()
        # construct the URL of the CometD endpoint using the instance URL
        self.url = self.get_cometd_url(self.auth.instance_url)
        # open the CometD client
        await super().open()

    async def subscribe(self, channel):
        try:
            await super().subscribe(channel)
        except ServerError as error:
            if (self.replay_fallback and self.replay_storage and
                    error.error_code == HTTPStatus.BAD_REQUEST):
                self.replay_storage.replay_fallback = self.replay_fallback
                await super().subscribe(channel)
            else:
                raise

    @staticmethod
    def create_replay_storage(replay_param):
        """Create a :obj:`ReplayMarkerStorage` object based from *replay_param*

        :param replay_param: One of the supported *replay_param* type objects
        :type replay_param: ReplayMarkerStorage, ReplayOption, \
        collections.abc.MutableMapping or None
        :return: A new :obj:`ReplayMarkerStorage` object or *replay_param* if \
        it's already an instance of :obj:`ReplayMarkerStorage` object, or \
        None if *replay_param* is None
        :rtype: ReplayMarkerStorage or None
        """
        if isinstance(replay_param, ReplayMarkerStorage):
            return replay_param
        elif isinstance(replay_param, abc.MutableMapping):
            return MappingStorage(replay_param)
        elif isinstance(replay_param, ReplayOption):
            return ConstantReplayId(replay_param)
        return None

    @staticmethod
    def get_cometd_url(instance_url):
        """Get the CometD URL associated with the *instance_url*

        :param str instance_url: Salesforce instance URL
        :return: CometD URL associated with the *instance_url*
        :rtype: str
        """
        return "/".join((instance_url, COMETD_PATH, API_VERSION))
