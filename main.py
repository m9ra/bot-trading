from configuration import TRACKED_PAIRS, WS_URL
from core.feed_writer import FeedWriter

writer = FeedWriter(WS_URL, TRACKED_PAIRS)
writer.run()
