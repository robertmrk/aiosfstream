"""Replay extension classes"""
from collections import abc
from abc import abstractmethod
from enum import IntEnum, unique
import reprlib
from typing import Optional, NamedTuple, MutableMapping, Any, cast, \
    AsyncContextManager

from aiocometd import Extension
from aiocometd.typing import Payload, Headers, JsonObject
from aiocometd.constants import MetaChannel

from aiosfstream.exceptions import ReplayError


@unique
class ReplayOption(IntEnum):
    """Replay options supported by Salesforce"""
    #: Receive new events that are broadcast after the client subscribes
    NEW_EVENTS = -1
    #: Receive all events, including past events that are within the 24-hour
    #: retention window and new events sent after subscription
    ALL_EVENTS = -2


class ReplayMarker(NamedTuple):
    """Class for storing a message replay id and its creation date"""
    #: Creation date of a message, as a ISO 8601 formatted  datetime string
    date: str
    #: Replay id of a message
    replay_id: int


class ReplayMarkerStorage(Extension):
    """Abstract base class for replay marker storage implementations"""
    def __init__(self) -> None:
        super().__init__()
        self.replay_fallback: Optional[ReplayOption] = None

    async def incoming(self, payload: Payload,
                       headers: Optional[Headers] = None) -> None:
        pass

    async def outgoing(self, payload: Payload, headers: Headers) -> None:
        for message in payload:
            # if the outgoing message is a subscribe message, then insert the
            # stored replay id into the message
            if message["channel"] == MetaChannel.SUBSCRIBE:
                await self.insert_replay_id(message)

    async def insert_replay_id(self, message: JsonObject) -> None:
        """Insert the stored replay id into the *message*

        :param message: An outgoing, ``/meta/subscribe`` message
        """
        # get the name of the channel, that the message is trying to subscribe
        # to
        subscription = message["subscription"]

        # if there is a replay fallback set, then it must be used as the replay
        # id in order to successfully subscribe
        if self.replay_fallback:
            replay_id: Optional[int] = self.replay_fallback
            self.replay_fallback = None
        # otherwise get the stored replay id
        else:
            replay_id = await self.get_replay_id(subscription)

        # if the replay id is None, then we do not yet have a replay id for the
        # given subscription, so don't add anything to the message
        if replay_id:
            if "ext" not in message:
                message["ext"] = {}
            message["ext"]["replay"] = {subscription: replay_id}

    @staticmethod
    def get_message_date(message: JsonObject) -> str:
        """Return the creation date of the *message*

        :param message: An incoming message
        :return: Creation date as an ISO 8601 formatted datetime string
        :raise ReplayError: If no creation date can be found in the *message*
        """
        # get the creation date of the message from a PushTopic message
        # structure if it exists, or read it from a PlatfromEvent message
        # structure
        creation_date = None
        if "data" in message:
            if ("event" in message["data"] and
                    "createdDate" in message["data"]["event"]):
                creation_date = message["data"]["event"]["createdDate"]
            elif "payload" in message["data"]:
                creation_date = message["data"]["payload"].get("CreatedDate")

        # raise an error if no valid creation date can be found
        if not isinstance(creation_date, str):
            raise ReplayError("No message creation date found.")
        return creation_date

    async def extract_replay_id(self, message: JsonObject) -> None:
        """Extract and store the replay id present int the *message*

        :param message: An incoming broadcast message
        :raise ReplayError: If no creation date can be found in the *message*
        """
        # get the name of the subscription
        subscription = message["channel"]

        # create the replay marker object from the creation date and the
        # actual id
        marker = ReplayMarker(date=self.get_message_date(message),
                              replay_id=message["data"]["event"]["replayId"])

        # get the last, stored, replay marker
        last_marker = await self.get_replay_marker(subscription)

        # only store the extracted replay marker, if there is no replay \
        # marker for the subscription yet, or if the stored replay marker is\
        # older then the extracted one or it has the same data (otherwise,
        # we're seeing a replayed message, and in that case, it shouldn't be
        # stored)
        if not last_marker or last_marker.date <= marker.date:
            await self.set_replay_marker(subscription, marker)

    async def get_replay_id(self, subscription: str) -> Optional[int]:
        """Retrieve a stored replay id for the given *subscription*

        :param subscription: Name of the subscribed channel
        :return: A replay id or ``None`` if there is nothing stored for \
        the given *subscription*
        """
        marker = await self.get_replay_marker(subscription)
        if marker:
            return marker.replay_id
        return None

    @abstractmethod
    async def get_replay_marker(self, subscription: str) \
            -> Optional[ReplayMarker]:
        """Retrieve a stored replay marker for the given *subscription*

        :param subscription: Name of the subscribed channel
        :return: A replay marker or ``None`` if there is nothing stored for \
        the given *subscription*
        """

    @abstractmethod
    async def set_replay_marker(self, subscription: str,
                                replay_marker: ReplayMarker) -> None:
        """Store the *replay_marker* for the given *subscription*

        :param subscription: Name of the subscribed channel
        :param replay_marker: A replay marker
        """

    def __call__(self, message: JsonObject) -> AsyncContextManager[None]:
        """Return an asynchronous context manager instance for extracting the
        replay id from the *message* if no exceptions occur inside the runtime
        context

        :param message: An incoming message
        :return: An asynchronous context manager
        """
        return ReplayMarkerStorageContextManager(self, message)


class ReplayMarkerStorageContextManager(AsyncContextManager[None]):
    """Asynchronous context manager for conditionally extracting the replay \
    id from a message

    If the runtime context is exited with an exception then the given exception
    will be raised, otherwise if the context is exited normally, then the
    replay id will be extracted from the managed response message.
    """
    def __init__(self, replay_storage: ReplayMarkerStorage,
                 message: JsonObject) -> None:
        """
        :param replay_storage: A :obj:`ReplayMarkerStorage` instance
        :param message: A response message
        """
        self.replay_storage = replay_storage
        self.message = message

    async def __aenter__(self) -> None:
        """Enter the runtime context"""

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) \
            -> None:
        """Extract the replay id from the message managed by the context or \
        raise any exception triggered within the runtime context.
        """
        if exc_val is None:
            await self.replay_storage.extract_replay_id(self.message)


class MappingStorage(ReplayMarkerStorage):
    """Mapping based replay marker storage"""
    def __init__(self, mapping: MutableMapping[str, ReplayMarker]) -> None:
        """
        :param mapping: A MutableMapping object for storing replay markers
        """
        if not isinstance(mapping, abc.MutableMapping):
            raise TypeError("mapping parameter should be an instance of "
                            "MutableMapping.")
        super().__init__()
        #: A MutableMapping object for storing replay markers
        self.mapping = mapping

    def __repr__(self) -> str:
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(mapping={reprlib.repr(self.mapping)})"

    async def set_replay_marker(self, subscription: str,
                                replay_marker: ReplayMarker) -> None:
        self.mapping[subscription] = replay_marker

    async def get_replay_marker(self, subscription: str) \
            -> Optional[ReplayMarker]:
        try:
            return self.mapping[subscription]
        except KeyError:
            return None


class DefaultReplayIdMixin:  # pylint: disable=too-few-public-methods
    """A mixin class that will return a default, constant replay id if
    there is not replay marker for the given subscription"""
    def __init__(self, default_id: int, **kwargs: Any) -> None:
        """
        :param default_id: A replay id
        """
        super().__init__(**kwargs)  # type: ignore
        #: A replay id
        self.default_id = default_id

    async def get_replay_id(self, subscription: str) -> int:
        """Retrieve a stored replay id for the given *subscription*

        :param subscription: Name of the subscribed channel
        :return: The default, constant replay id if there is not replay \
        marker for the given subscription
        """
        marker = await cast(ReplayMarkerStorage, self)\
            .get_replay_marker(subscription)
        if marker:
            return marker.replay_id
        return self.default_id


class ConstantReplayId(DefaultReplayIdMixin, ReplayMarkerStorage):
    """A replay marker storage which will return a constant replay id for
    every subscription

    .. note::

        This implementations doesn't actually stores anything for later
        retrieval.
    """
    def __repr__(self) -> str:
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(default_id={reprlib.repr(self.default_id)})"

    async def set_replay_marker(self, subscription: str,
                                replay_marker: ReplayMarker) -> None:
        pass

    async def get_replay_marker(self, subscription: str) \
            -> Optional[ReplayMarker]:
        return None


class DefaultMappingStorage(DefaultReplayIdMixin, MappingStorage):
    """Mapping based replay marker storage which will return a defualt
    replay id if there is not replay marker for the given subscription """
    def __init__(self, mapping: MutableMapping[str, ReplayMarker],
                 default_id: int) -> None:
        """
        :param mapping: A MutableMapping object for storing replay markers
        :param default_id: A replay id
        """
        super().__init__(mapping=mapping, default_id=default_id)

    def __repr__(self) -> str:
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(mapping={reprlib.repr(self.mapping)}, " \
               f"default_id={reprlib.repr(self.default_id)})"
