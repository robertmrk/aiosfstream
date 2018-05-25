"""Replay extension classes"""
from collections import namedtuple, abc
from abc import abstractmethod
from enum import IntEnum, unique
import reprlib

from aiocometd import Extension
from aiocometd.constants import MetaChannel


@unique
class ReplayOption(IntEnum):
    """Replay options supported by Salesforce"""
    #: Receive new events that are broadcast after the client subscribes
    NEW_EVENTS = -1
    #: Receive all events, including past events that are within the 24-hour
    #: retention window and new events sent after subscription
    ALL_EVENTS = -2


#: Class for storing a message replay id and its creation date
#:
#: :param str date: Creation date of a message, as a ISO 8601 formatted \
#:                  datetime string
#: :param int replay_id: Replay id of a message
ReplayMarker = namedtuple("ReplayMarker", "date, replay_id")


class ReplayMarkerStorage(Extension):
    """Abstract base class for replay marker storage implementations"""
    def __init__(self):
        super().__init__()
        self.replay_fallback = None

    async def incoming(self, payload, headers=None):
        pass

    async def outgoing(self, payload, headers):
        for message in payload:
            # if the outgoing message is a subscribe message, then insert the
            # stored replay id into the message
            if message["channel"] == MetaChannel.SUBSCRIBE:
                await self.insert_replay_id(message)

    async def insert_replay_id(self, message):
        """Insert the stored replay id into the *message*

        :param dict message: An outgoing, ``/meta/subscribe`` message
        """
        # get the name of the channel, that the message is trying to subscribe
        # to
        subscription = message["subscription"]

        # if there is a replay fallback set, then it must be used as the replay
        # id in order to successfully subscribe
        if self.replay_fallback:
            replay_id = self.replay_fallback
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

    async def extract_replay_id(self, message):
        """Extract and store the replay id present int the *message*

        :param dict message: An incoming broadcast message
        """
        # get the name of the subscription
        subscription = message["channel"]

        # create the replay marker object from the creation date and the
        # actual id
        event = message["data"]["event"]
        marker = ReplayMarker(date=event["createdDate"],
                              replay_id=event["replayId"])

        # get the last, stored, replay marker
        last_marker = await self.get_replay_marker(subscription)

        # only store the extracted replay marker, if there is no replay \
        # marker for the subscription yet, or if the stored replay marker is\
        # older then the extracted one or it has the same data (otherwise,
        # we're seeing a replayed message, and in that case, it shouldn't be
        # stored)
        if not last_marker or last_marker.date <= marker.date:
            await self.set_replay_marker(subscription, marker)

    async def get_replay_id(self, subscription):
        """Retrieve a stored replay id for the given *subscription*

        :param str subscription: Name of the subscribed channel
        :return: A replay id or ``None`` if there is nothing stored for \
        the given *subscription*
        :rtype: int
        """
        marker = await self.get_replay_marker(subscription)
        if marker:
            return marker.replay_id
        return None

    @abstractmethod
    async def get_replay_marker(self, subscription):
        """Retrieve a stored replay marker for the given *subscription*

        :param str subscription: Name of the subscribed channel
        :return: A replay marker or ``None`` if there is nothing stored for \
        the given *subscription*
        :rtype: ReplayMarker or None
        """

    @abstractmethod
    async def set_replay_marker(self, subscription, replay_marker):
        """Store the *replay_marker* for the given *subscription*

        :param str subscription: Name of the subscribed channel
        :param ReplayMarker replay_marker: A replay marker
        """


class MappingStorage(ReplayMarkerStorage):
    """Mapping based replay marker storage"""
    def __init__(self, mapping):
        """
        :param mapping: A MutableMapping object for storing replay markers
        :type mapping: collections.abc.MutableMapping
        """
        if not isinstance(mapping, abc.MutableMapping):
            raise TypeError("mapping parameter should be an instance of "
                            "MutableMapping.")
        super().__init__()
        #: A MutableMapping object for storing replay markers
        self.mapping = mapping

    def __repr__(self):
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(mapping={reprlib.repr(self.mapping)})"

    async def set_replay_marker(self, subscription, replay_marker):
        self.mapping[subscription] = replay_marker

    async def get_replay_marker(self, subscription):
        try:
            return self.mapping[subscription]
        except KeyError:
            return None


class DefaultReplayIdMixin:  # pylint: disable=too-few-public-methods
    """A mixin class that will return a default, constant replay id if
    there is not replay marker for the given subscription"""
    def __init__(self, default_id, **kwargs):
        """
        :param int default_id: A replay id
        """
        super().__init__(**kwargs)
        #: A replay id
        self.default_id = default_id

    async def get_replay_id(self, subscription):
        """Retrieve a stored replay id for the given *subscription*

        :param str subscription: Name of the subscribed channel
        :return: The default, constant replay id if there is not replay \
        marker for the given subscription
        :rtype: int
        """
        marker = await self.get_replay_marker(subscription)
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
    def __repr__(self):
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(default_id={reprlib.repr(self.default_id)})"

    async def set_replay_marker(self, subscription, replay_marker):
        pass

    async def get_replay_marker(self, subscription):
        return None


class DefaultMappingStorage(DefaultReplayIdMixin, MappingStorage):
    """Mapping based replay marker storage which will return a defualt
    replay id if there is not replay marker for the given subscription """
    def __init__(self, mapping, default_id):
        """
        :param mapping: A MutableMapping object for storing replay markers
        :type mapping: collections.abc.MutableMapping
        :param int default_id: A replay id
        """
        super().__init__(mapping=mapping, default_id=default_id)

    def __repr__(self):
        """Formal string representation"""
        cls_name = type(self).__name__
        return f"{cls_name}(mapping={reprlib.repr(self.mapping)}, " \
               f"default_id={reprlib.repr(self.default_id)})"
