from dataclasses import dataclass


@dataclass
class MoneyProvider:
    name: str
    table_name: str

    def __hash__(self):
        return hash(self.name)
