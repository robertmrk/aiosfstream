"""Replay extension classes"""
from collections import namedtuple
from abc import abstractmethod
from enum import Enum, unique

from aiocometd import Extension
from aiocometd.constants import META_CHANNEL_PREFIX, MetaChannel


@unique
class ReplayOption(Enum):
    """Replay options supported by Salesforce"""

    NEW_EVENTS = -1
    ALL_EVENTS = -2


#: Class for storing a message replay id and its creation date
ReplayId = namedtuple("ReplayId", "creation_date, id")


class ReplayStorage(Extension):
    """Abstract base class for replay id storage implementations"""

    async def incoming(self, payload, headers=None):
        for message in payload:
            # messages for every channel should have a replay id except
            # meta channels
            if not message["channel"].startswith(META_CHANNEL_PREFIX):
                # extract the raplay id from the message
                await self.extract_replay_id(message)

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
        # get the stored replay id
        replay_id = await self.get_replay_id(subscription)

        # if the replay id is None, then we do not yet have a replay id for the
        # given subscription, so don't add anything to the message
        if replay_id:
            if "ext" not in message:
                message["ext"] = {}
            message["ext"]["replay"] = {subscription: replay_id.id}

    async def extract_replay_id(self, message):
        """Extract and store the replay id present int the *message*

        :param dict message: An incoming broadcast message
        """
        # get the name of the subscription
        subscription = message["channel"]
        # create the replay id object from the creation date and the actual id
        event = message["data"]["event"]
        replay_id = ReplayId(creation_date=event["createdDate"],
                             id=event["replayId"])

        # get the last, stored, replay id
        last_replay_id = await self.get_replay_id(subscription)
        # only store the extracted replay id, if there is no replay id for the
        # subscription yet, or if the stored replay id is older then the
        # extracted one (otherwise, we're seeing a replayed message, and in
        # that case, it shouldn't be stored)
        if (not last_replay_id or
                (last_replay_id and
                 last_replay_id.creation_date < replay_id.creation_date)):
            await self.set_replay_id(subscription, replay_id)

    @abstractmethod
    async def set_replay_id(self, subscription, replay_id):
        """Store the *replay_id* for the given *subscription*

        :param str subscription: Name of the subscribed channel
        :param ReplayId replay_id: A replay id
        """

    @abstractmethod
    async def get_replay_id(self, subscription):
        """Retreive a stored replay id for the given *subscription*

        :param str subscription: Name of the subscribed channel
        :return: A replay id or ``None`` if there is nothing stored for the \\
        given *subscription*
        :rtype: ReplayId
        """
