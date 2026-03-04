# Limit Order Book (Matching Engine)
<p align="center">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>


A high-performance order matching engine implementing **price-time priority** matching using **binary heaps** for O(log N) operations.

> Built as a demonstration of trading systems knowledge and data structure optimization.

## Overview

This project simulates the core component of any trading system - the **Limit Order Book**. It maintains outstanding Buy (Bid) and Sell (Ask) orders and matches them according to price-time priority rules.

## Key Features

- **Efficient Data Structures**: Uses Binary Heaps (Priority Queues) for O(log N) insertion and O(1) best-price lookup
- **Price-Time Priority**: Orders are matched first by price, then by arrival time
- **Support for Multiple Order Types**: Limit orders with partial fills
- **Comprehensive Testing**: Unit tests with 100+ random orders to validate correctness

## Time Complexity

| Operation | Complexity |
|-----------|------------|
| Add Order | O(log N) |
| Get Best Bid/Ask | O(1) |
| Match Order | O(log N) per match |
| Cancel Order | O(N) |

## Project Structure

```
limit_order_book/
├── README.md
├── order_book/
│   ├── __init__.py
│   ├── order.py          # Order and Trade data classes
│   ├── order_book.py     # OrderBook with bid/ask heaps
│   └── matching_engine.py # Core matching logic
├── tests/
│   ├── __init__.py
│   ├── test_order.py
│   ├── test_order_book.py
│   └── test_matching_engine.py
└── demo.py               # Demo with 100 random orders
```

## Usage

```python
from order_book import MatchingEngine, Order, Side

# Create the matching engine
engine = MatchingEngine()

# Submit orders
engine.process_order(Order(side=Side.BUY, price=100.0, quantity=10))
engine.process_order(Order(side=Side.SELL, price=99.5, quantity=5))

# Get executed trades
trades = engine.get_trades()

# View the order book
print(engine.order_book)
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Running the Demo

```bash
python demo.py
```

## Design Decisions

### Why Heaps over Lists?

Using a simple list and sorting would give O(N log N) for each insertion. By using a min-heap for asks and a max-heap for bids, we achieve:
- O(log N) insertion
- O(1) peek at best price
- O(log N) removal of best price

### Price-Time Priority

When multiple orders exist at the same price level, the order that arrived first gets priority. This is implemented by including a monotonically increasing sequence number in each order.

## Author

Built with <3 by AKSHAY GUPTA BURELA
