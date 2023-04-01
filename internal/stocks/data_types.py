from dataclasses import dataclass


@dataclass
class NotificationRow:
    ticker: str = None
    book_cost: float = None
    current_price: float = None

    delta_tracked_amount: float = None
    delta_tracked_pct: float = None

    delta_week_amount: float = None
    delta_week_pct: float = None

    def __list__(self):
        return [
            self.ticker,
            self.book_cost,
            self.current_price,
            self.delta_tracked_amount,
            self.delta_tracked_pct,
            self.delta_week_amount,
            self.delta_week_pct,
        ]
