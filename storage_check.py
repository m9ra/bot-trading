import time

from configuration import TRACKED_PAIRS
from data.storage_index import StorageIndex
from data.storage_reader import StorageReader

last_entry_counts = []
readers = []
for pair in TRACKED_PAIRS:
    reader = StorageReader(pair)
    readers.append(reader)
    last_entry_counts.append(0)

for reader in readers:
    entry_count = reader.get_entry_count()
    index = StorageIndex(reader.pair)
    start = time.time()
    index.update_by(reader._parse_entry_block(0, entry_count))
    end = time.time()

    duration = end - start

    print(f"{reader.pair} {entry_count} {entry_count / duration} {duration}")

while True:
    has_update = False
    for i, reader in enumerate(readers):
        entry_count = reader.get_entry_count()
        last_entry_count = last_entry_counts[i]
        if entry_count != last_entry_count:
            print(f"{reader.pair}: {entry_count - last_entry_count}")
            last_entry_counts[i] = entry_count
            has_update = True

    if has_update:
        print("==============")

    time.sleep(1)
