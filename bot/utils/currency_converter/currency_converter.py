import aiohttp


class CurrencyConverter:
    URL='https://api.frankfurter.app/%s?from=JPY&to=%s'

    def __init__(self):
        self.known_rates: dict[str, dict[str, float]] = {}

    async def get_jpy_rate(self, date_str: str, currency: str) -> float:
        if currency != 'USD':
            raise ValueError('Only USD is supported')

        currency_rates = self.known_rates.get(date_str)
        if currency_rates is not None:
            rate = currency_rates.get(currency)
            if rate is not None:
                return rate

        async with aiohttp.ClientSession() as session:
            async with session.get(self.URL % (date_str, currency)) as response:
                if response.status == 200:
                    data = await response.json()
                    rate = data['rates'][currency]
                    if date_str not in self.known_rates:
                        self.known_rates[date_str] = {}
                    self.known_rates[date_str][currency] = rate
                    return rate
                else:
                    return 0.
