from bot_trading.core.configuration import TRACKED_PAIRS, WS_URL
from bot_trading.core.networking.feed_connector import FeedWriter
from bot_trading.core.processors.verification_processor import VerificationProcessor

tracked_pairs = TRACKED_PAIRS
writer = FeedWriter(WS_URL, tracked_pairs, VerificationProcessor)
writer.run()