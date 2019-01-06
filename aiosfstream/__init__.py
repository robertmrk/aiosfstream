"""Salesforce Streaming API client for asyncio"""
import logging

from aiosfstream._metadata import VERSION as __version__  # noqa: F401
from aiosfstream.client import Client, SalesforceStreamingClient  # noqa: F401
from aiosfstream.client import ReplayMarkerStoragePolicy  # noqa: F401
from aiosfstream.auth import PasswordAuthenticator  # noqa: F401
from aiosfstream.auth import RefreshTokenAuthenticator  # noqa: F401
from aiosfstream.replay import ReplayMarker, ReplayOption  # noqa: F401
from aiosfstream.replay import MappingStorage  # noqa: F401
from aiosfstream.replay import DefaultMappingStorage  # noqa: F401
from aiosfstream.replay import ConstantReplayId  # noqa: F401
from aiosfstream.replay import ReplayMarkerStorage  # noqa: F401

# Create a default handler to avoid warnings in applications without logging
# configuration
logging.getLogger(__name__).addHandler(logging.NullHandler())
