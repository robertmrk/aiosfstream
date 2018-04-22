from datetime import datetime, timezone, timedelta

from asynctest import TestCase, mock
from aiocometd.constants import MetaChannel

from aiosfstream.replay import ReplayStorage, ReplayId, MappingReplayStorage


class ReplayStorageStub(ReplayStorage):
    async def set_replay_id(self, subscription, replay_id):
        pass

    async def get_replay_id(self, subscription):
        pass


class TestReplayStorage(TestCase):
    def setUp(self):
        self.replay_storage = ReplayStorageStub()

    async def test_incoming_with_meta_channel(self):
        self.replay_storage.extract_replay_id = mock.CoroutineMock()
        message = {
            "channel": MetaChannel.HANDSHAKE
        }

        await self.replay_storage.incoming([message])

        self.replay_storage.extract_replay_id.assert_not_called()

    async def test_incoming_with_broadcast_channel(self):
        self.replay_storage.extract_replay_id = mock.CoroutineMock()
        message = {
            "channel": "/foo/bar"
        }

        await self.replay_storage.incoming([message])

        self.replay_storage.extract_replay_id.assert_called_with(message)

    async def test_outgoing_with_subscribe(self):
        self.replay_storage.insert_replay_id = mock.CoroutineMock()
        message = {
            "channel": MetaChannel.SUBSCRIBE
        }

        await self.replay_storage.outgoing([message], {})

        self.replay_storage.insert_replay_id.assert_called_with(message)

    async def test_outgoing_with_non_subscribe(self):
        self.replay_storage.insert_replay_id = mock.CoroutineMock()
        message = {
            "channel": MetaChannel.HANDSHAKE
        }

        await self.replay_storage.outgoing([message], {})

        self.replay_storage.insert_replay_id.assert_not_called()

    async def test_insert_replay_id(self):
        replay_id = ReplayId(
            creation_date=datetime.now(timezone.utc).isoformat(),
            id="id"
        )
        self.replay_storage.get_replay_id = mock.CoroutineMock(
            return_value=replay_id
        )
        message = {
            "channel": MetaChannel.SUBSCRIBE,
            "subscription": "/foo/bar",
            "ext": {}
        }

        await self.replay_storage.insert_replay_id(message)

        self.assertEqual(message["ext"]["replay"][message["subscription"]],
                         replay_id.id)
        self.replay_storage.get_replay_id.assert_called_with(
            message["subscription"])

    async def test_insert_replay_id_inserts_ext(self):
        replay_id = ReplayId(
            creation_date=datetime.now(timezone.utc).isoformat(),
            id="id"
        )
        self.replay_storage.get_replay_id = mock.CoroutineMock(
            return_value=replay_id
        )
        message = {
            "channel": MetaChannel.SUBSCRIBE,
            "subscription": "/foo/bar"
        }

        await self.replay_storage.insert_replay_id(message)

        self.assertEqual(message["ext"]["replay"][message["subscription"]],
                         replay_id.id)
        self.replay_storage.get_replay_id.assert_called_with(
            message["subscription"])

    async def test_insert_replay_id_doesnt_insert_none(self):
        replay_id = None
        self.replay_storage.get_replay_id = mock.CoroutineMock(
            return_value=replay_id
        )
        message = {
            "channel": MetaChannel.SUBSCRIBE,
            "subscription": "/foo/bar"
        }

        await self.replay_storage.insert_replay_id(message)

        self.assertNotIn("ext", message)
        self.replay_storage.get_replay_id.assert_called_with(
            message["subscription"])

    async def test_extract_replay_id_on_no_previous_id(self):
        self.replay_storage.set_replay_id = mock.CoroutineMock()
        self.replay_storage.get_replay_id = mock.CoroutineMock(
            return_value=None
        )
        date = datetime.now(timezone.utc).isoformat()
        id_value = "id"
        message = {
            "channel": "/foo/bar",
            "data": {
                "event": {
                    "createdDate": date,
                    "replayId": id_value
                }
            }
        }

        await self.replay_storage.extract_replay_id(message)

        self.replay_storage.set_replay_id.assert_called_with(
            message["channel"],
            ReplayId(creation_date=date, id=id_value)
        )

    async def test_extract_replay_id_on_previous_id_older(self):
        self.replay_storage.set_replay_id = mock.CoroutineMock()
        prev_replay_id = ReplayId(
            creation_date=(datetime.now(timezone.utc) -
                           timedelta(seconds=1)).isoformat(),
            id="old_id"
        )
        self.replay_storage.get_replay_id = mock.CoroutineMock(
            return_value=prev_replay_id
        )
        date = datetime.now(timezone.utc).isoformat()
        id_value = "id"
        message = {
            "channel": "/foo/bar",
            "data": {
                "event": {
                    "createdDate": date,
                    "replayId": id_value
                }
            }
        }

        await self.replay_storage.extract_replay_id(message)

        self.replay_storage.set_replay_id.assert_called_with(
            message["channel"],
            ReplayId(creation_date=date, id=id_value)
        )

    async def test_extract_replay_id_on_previous_id_newer(self):
        self.replay_storage.set_replay_id = mock.CoroutineMock()
        prev_replay_id = ReplayId(
            creation_date=(datetime.now(timezone.utc) +
                           timedelta(days=1)).isoformat(),
            id="newer_id"
        )
        self.replay_storage.get_replay_id = mock.CoroutineMock(
            return_value=prev_replay_id
        )
        date = datetime.now(timezone.utc).isoformat()
        id_value = "id"
        message = {
            "channel": "/foo/bar",
            "data": {
                "event": {
                    "createdDate": date,
                    "replayId": id_value
                }
            }
        }

        await self.replay_storage.extract_replay_id(message)

        self.replay_storage.set_replay_id.assert_not_called()


class TestMappingReplayStorage(TestCase):
    def setUp(self):
        self.mapping = {}
        self.storage = MappingReplayStorage(self.mapping)

    def test_init(self):
        self.assertIs(self.storage.mapping, self.mapping)

    def test_init_error_on_non_mapping(self):
        with self.assertRaisesRegex(TypeError,
                                    "mapping parameter should be an "
                                    "instance of MutableMapping."):
            MappingReplayStorage([])

    async def test_set_replay_id(self):
        self.storage.mapping = mock.MagicMock()
        subscription = "/foo/bar"
        replay_id = ReplayId(creation_date="", id="id")

        await self.storage.set_replay_id(subscription, replay_id)

        self.storage.mapping.__setitem__.assert_called_with(subscription,
                                                            replay_id)

    async def test_get_replay_id(self):
        subscription = "/foo/bar"
        replay_id = ReplayId(creation_date="", id="id")
        self.storage.mapping = mock.MagicMock()
        self.storage.mapping.__getitem__.return_value = replay_id

        result = await self.storage.get_replay_id(subscription)

        self.assertEqual(result, replay_id)
        self.storage.mapping.__getitem__.assert_called_with(subscription)

    async def test_get_replay_id_none_on_key_error(self):
        subscription = "/foo/bar"
        self.storage.mapping = mock.MagicMock()
        self.storage.mapping.__getitem__.side_effect = KeyError()

        result = await self.storage.get_replay_id(subscription)

        self.assertIsNone(result)
        self.storage.mapping.__getitem__.assert_called_with(subscription)
