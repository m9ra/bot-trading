def get_pair_id(pair: str):
    return pair.lower().replace("/", "_")


def parse_pair(pair: str):
    return pair.upper().split("/")


def make_pair(source_currency: str, target_currency: str):
    return source_currency.upper() + "/" + target_currency.upper()


def reverse_pair(pair: str):
    c1, c2 = parse_pair(pair)
    return make_pair(c2, c1)
