from bot_trading.core.networking.trading_server import TradingServer


class ScoreRecord(object):
    def __init__(self, username, portfolio_value, successful_command_count, declined_command_count, total_seconds,
                 is_online):
        self._username = username
        self._portfolio_value = portfolio_value
        self._accepted_command_count = successful_command_count
        self._declined_command_count = declined_command_count
        self._total_seconds = total_seconds
        self._is_online = is_online

    @classmethod
    def load_for(cls, trading_server: TradingServer):
        users = trading_server.load_accounts()
        records = []
        for user in users:
            username = user.get("_id")
            records.append(
                ScoreRecord(username,
                            user.get("portfolio_value"),
                            user.get("accepted_command_count"),
                            user.get("declined_command_count"),
                            user.get("total_seconds"),
                            is_online=trading_server.is_user_online(username)
                            )
            )

        records.sort(key=lambda x: x.portfolio_value, reverse=True)
        return records

    @property
    def is_online(self):
        return self._is_online

    @property
    def username(self):
        return self._username

    @property
    def friendly_username(self):
        return self._username.split("@")[0]

    @property
    def portfolio_value(self):
        return self._portfolio_value

    @property
    def accepted_command_count(self):
        return self._accepted_command_count

    @property
    def declined_command_count(self):
        return self._declined_command_count

    @property
    def total_time(self):
        minutes = int(self._total_seconds / 60)
        hours = int(1.0 * self._total_seconds / 60 / 60)

        if not minutes and not hours:
            return f"{int(self._total_seconds):02d}s"

        if not hours:
            return f"{minutes}m{int(self._total_seconds) % 60:02d}"

        return f"{hours}h{minutes % 60:02d}"
