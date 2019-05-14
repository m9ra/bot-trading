class PricebookProcessorState(object):
    def __init__(self, current_index, timestamp):
        self.current_index = current_index
        self.current_time = timestamp

        self._buy_container = None
        self._sell_container = None
        self._buffer = []

    def create_pricebook_processor_data(self):
        buy_container = self._replicate_container(self._buy_container)
        sell_container = self._replicate_container(self._sell_container)
        buffer = list(self._buffer)

        return buy_container, sell_container, buffer

    def inject_to(self, processor):
        data = self.create_pricebook_processor_data()
        processor.inject(*data)

    def load_from(self, processor):
        data = processor.get_dump()
        self._buy_container = self._replicate_container(data[0])
        self._sell_container = self._replicate_container(data[1])
        self._buffer = list(data[2])

    def _replicate_container(self, container):
        if container is None:
            return None

        return dict(container)

    def __repr__(self):
        return f"PricebookViewState {self.current_time}: {self.current_index}"
