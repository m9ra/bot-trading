from time import sleep

from configuration import TRACKED_PAIRS, BOOK_DEPTH
from data.storage_reader import StorageReader

last_entry_counts = []
readers = []
for pair in TRACKED_PAIRS:
    reader = StorageReader(pair)
    readers.append(reader)
    last_entry_counts.append(0)

    drange = reader.get_date_range()

    print(reader.pair)
    print(reader.get_entry_count())
    print(drange)

    last_start_index = 0
    slots = 10000
    for i in range(slots):
        date_diff = drange[1] - drange[0]
        date = drange[0] + date_diff / slots * i
        start = reader.find_pricebook_start(date, BOOK_DEPTH)

        if last_start_index > start:
            print(f"Incorrect start finding algorithm: {last_start_index} {start} {date}")

        last_start_index = start

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

    sleep(1)
