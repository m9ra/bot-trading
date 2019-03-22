from bot_trading.core.configuration import TRACKED_PAIRS, WS_URL
from bot_trading.core.networking.feed_connector import FeedWriter
from bot_trading.core.processors.storage_processor import StorageProcessor

tracked_pairs = TRACKED_PAIRS
writer = FeedWriter(WS_URL, tracked_pairs, StorageProcessor)
writer.run()
