"""Client class implementation"""
from aiocometd import Client as CometdClient


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
    def __init__(self, authenticator):
        """
        :param authenticator: An authenticator object
        :type authenticator: aiosfstream.auth.AuthenticatorBase
        """
        # set authenticator as the auth extension
        super().__init__("", auth=authenticator)

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
