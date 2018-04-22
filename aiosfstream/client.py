"""Client class implementation"""
from aiocometd import Client as CometdClient

from .auth import AuthenticatorBase


COMETD_PATH = "cometd"
API_VERSION = "42.0"


def get_cometd_url(instance_url):
    """Get the CometD URL associated with the *instance_url*

    :param str instance_url: Salesforce instance URL
    :return: CometD URL associated with the *instance_url*
    :rtype: str
    """
    return "/".join((instance_url, COMETD_PATH, API_VERSION))


class Client(CometdClient):
    """Salesforce Streaming API client"""
    def __init__(self, authenticator, *, connection_timeout=10.0,
                 max_pending_count=100, loop=None):
        """
        :param authenticator: An authenticator object
        :type authenticator: aiosfstream.auth.AuthenticatorBase
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

        # set authenticator as the auth extension
        super().__init__("",
                         auth=authenticator,
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
        self.url = get_cometd_url(self.auth.instance_url)
        # open the CometD client
        await super().open()
