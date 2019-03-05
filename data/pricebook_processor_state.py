class PricebookProcessorState(object):
    def __init__(self, current_index, timestamp):
        self.current_index = current_index
        self.current_time = timestamp

        self._buy_container = None
        self._sell_container = None
        self._w_buy_container = {}
        self._w_sell_container = {}

    def create_pricebook_processor_data(self):
        buy_container, w_buy_container = self._create_containers(self._buy_container, self._w_buy_container)
        sell_container, w_sell_container = self._create_containers(self._sell_container, self._w_sell_container)

        return buy_container, sell_container, w_buy_container, w_sell_container

    def inject_to(self, processor):
        data = self.create_pricebook_processor_data()
        processor.inject(*data)

    def load_from(self, processor):
        data = processor.get_dump()
        self._buy_container, self._sell_container = self._create_containers(data[0], data[1])
        self._w_buy_container, self._w_sell_container = self._create_containers(data[2], data[3])

    def _create_containers(self, container, w_container):
        if container is w_container:
            result = self._replicate_container(container)
            return result, result

        else:
            return self._replicate_container(container), self._replicate_container(w_container)

    def _replicate_container(self, container):
        if container is None:
            return None

        return dict(container)

    def __repr__(self):
        return f"PricebookViewState {self.current_time}: {self.current_index}"
