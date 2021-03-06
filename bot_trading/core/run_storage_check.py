from bot_trading.core.configuration import TRACKED_PAIRS
from bot_trading.core.data.storage_reader import StorageReader
from bot_trading.core.data.storage_writer import StorageWriter

last_entry_counts = []
readers = []

print("SERVICE ENTRY CHECKS")
for pair in TRACKED_PAIRS:
    print(f"\t checking {pair}")
    reader = StorageReader(pair)

    for bucket_index in range(int(reader.get_entry_count() / StorageWriter.bucket_entry_count)):
        entry_index = bucket_index * StorageWriter.bucket_entry_count
        entry = reader.get_entry(entry_index)

        if not entry.is_reset:
            print(f"\t\t {pair} entry at position {entry_index} is not service entry")
