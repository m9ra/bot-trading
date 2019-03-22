from bot_trading.configuration import TRADING_ENDPOINT
from bot_trading.core.configuration import BOOK_DEPTH
from bot_trading.core.networking.remote_observer import RemoteObserver
from bot_trading.core.processors.pricebook_processor import PricebookProcessor
from bot_trading.trading.utils import timestamp_to_datetime

observer = RemoteObserver(TRADING_ENDPOINT, "admin@cz.ibm.com", "no_password_yet")
observer.connect()

readers = observer.get_readers()
market_pairs = observer.get_pairs()

for reader in readers:
    print()
    print(f"CHECKING {reader.pair}")
    if reader.pair != "XRP/EUR":
        print("\t skipping because of test")
        continue
    entry_count = reader.get_entry_count()
    if entry_count == 0:
        print("\t skipping empty reader")

    print("\t first entry time")

    processor = PricebookProcessor(reader.pair)
    processor2 = PricebookProcessor(reader.pair)

    is_initialized = False
    last_entry = None

    # for i in range(entry_count):
    for i in range(1000):
        i = i + 1390 * 1000

        entry = reader.get_entry(i)
        print(entry)
        processor.accept(entry)
        if last_entry:
            processor2.accept(last_entry)
        last_entry = entry

        # print(f"\r \t {timestamp_to_datetime(processor.current_time)}  entry: {i}             ", end="")

        if processor.is_in_service_entry_area:
            continue

        is_initialized = is_initialized or processor.current_depth == BOOK_DEPTH
        if not is_initialized:
            pass
            #continue

        buy_levels = list(processor.buy_levels)
        sell_levels = list(processor.sell_levels)
        if buy_levels and sell_levels and buy_levels[0][0] > sell_levels[-1][0]:
            print(f"################## {timestamp_to_datetime(entry.timestamp)}")
            for j in range(i, i + 10):
                print(reader.get_entry(j))
            print("SELLS")
            print(str(processor2.sell_levels).replace("),", "\n"))
            print("BUYS")
            print(str(processor2.buy_levels).replace("),", "\n"))
            # raise AssertionError("Incorrect market semantic detected")
            print("Incorrect market semantic detected")

print("CHECK COMPLETE")
