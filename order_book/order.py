"""
Order and Trade Data Classes.

This module defines the core data structures for the order book:
- Order: Represents a limit order (buy or sell)
- Trade: Represents an executed trade between two orders
- Side: Enum for buy/sell side
- OrderStatus: Enum for order lifecycle states
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class Side(Enum):
    """Order side - either buying or selling."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order lifecycle status."""
    NEW = "NEW"              # Just created
    PARTIAL = "PARTIAL"      # Partially filled
    FILLED = "FILLED"        # Completely filled
    CANCELLED = "CANCELLED"  # Cancelled by user


# Global sequence number for time priority
_sequence_counter = 0


def _get_next_sequence() -> int:
    """Generate a monotonically increasing sequence number for time priority."""
    global _sequence_counter
    _sequence_counter += 1
    return _sequence_counter


def reset_sequence_counter() -> None:
    """Reset sequence counter (useful for testing)."""
    global _sequence_counter
    _sequence_counter = 0


@dataclass
class Order:
    """
    Represents a limit order in the order book.
    
    Attributes:
        side: BUY or SELL
        price: Limit price for the order
        quantity: Number of units to trade
        order_id: Unique identifier (auto-generated if not provided)
        timestamp: Unix timestamp when order was created
        sequence: Monotonic sequence for time priority (auto-generated)
        remaining_quantity: Unfilled quantity (initially equals quantity)
        status: Current order status
    
    Price-Time Priority:
        Orders are compared first by price, then by sequence number.
        For BUYS: Higher price = better (willing to pay more)
        For SELLS: Lower price = better (willing to accept less)
        At same price: Lower sequence = better (arrived earlier)
    """
    side: Side
    price: float
    quantity: int
    order_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    sequence: int = field(default_factory=_get_next_sequence)
    remaining_quantity: int = field(init=False)
    status: OrderStatus = field(default=OrderStatus.NEW)
    
    def __post_init__(self):
        """Initialize remaining quantity and generate order_id if needed."""
        self.remaining_quantity = self.quantity
        if self.order_id is None:
            self.order_id = f"ORD-{self.sequence:08d}"
    
    def fill(self, fill_quantity: int) -> None:
        """
        Fill (partially or fully) this order.
        
        Args:
            fill_quantity: Number of units filled
            
        Raises:
            ValueError: If fill_quantity exceeds remaining quantity
        """
        if fill_quantity > self.remaining_quantity:
            raise ValueError(
                f"Cannot fill {fill_quantity} units, only {self.remaining_quantity} remaining"
            )
        
        self.remaining_quantity -= fill_quantity
        
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIAL
    
    def cancel(self) -> None:
        """Cancel this order."""
        self.status = OrderStatus.CANCELLED
    
    @property
    def is_active(self) -> bool:
        """Check if order can still be matched."""
        return self.status in (OrderStatus.NEW, OrderStatus.PARTIAL)
    
    @property
    def filled_quantity(self) -> int:
        """Get the quantity that has been filled."""
        return self.quantity - self.remaining_quantity
    
    def __lt__(self, other: "Order") -> bool:
        """
        Compare orders for heap ordering.
        
        For the heap to work correctly:
        - BUY orders: Higher price is better, so we invert for min-heap
        - SELL orders: Lower price is better (natural min-heap order)
        - Ties broken by sequence (earlier is better)
        
        Note: This comparison is used internally by the heaps.
        """
        if self.side == Side.BUY:
            # For buys: higher price = better, so negate for min-heap
            if self.price != other.price:
                return self.price > other.price  # Higher price wins
            return self.sequence < other.sequence  # Earlier wins
        else:
            # For sells: lower price = better (natural for min-heap)
            if self.price != other.price:
                return self.price < other.price  # Lower price wins
            return self.sequence < other.sequence  # Earlier wins
    
    def __repr__(self) -> str:
        return (
            f"Order({self.side.value}, price={self.price:.2f}, "
            f"qty={self.remaining_quantity}/{self.quantity}, "
            f"id={self.order_id}, status={self.status.value})"
        )


@dataclass
class Trade:
    """
    Represents an executed trade between a buyer and seller.
    
    Attributes:
        buy_order_id: ID of the buy order
        sell_order_id: ID of the sell order
        price: Execution price
        quantity: Number of units traded
        timestamp: When the trade occurred
        trade_id: Unique trade identifier
    """
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int
    timestamp: float = field(default_factory=time.time)
    trade_id: Optional[str] = None
    
    # Class variable for trade numbering
    _trade_counter: int = 0
    
    def __post_init__(self):
        """Generate trade_id if not provided."""
        if self.trade_id is None:
            Trade._trade_counter += 1
            self.trade_id = f"TRD-{Trade._trade_counter:08d}"
    
    @classmethod
    def reset_counter(cls) -> None:
        """Reset trade counter (useful for testing)."""
        cls._trade_counter = 0
    
    def __repr__(self) -> str:
        return (
            f"Trade({self.trade_id}: {self.buy_order_id} <-> {self.sell_order_id}, "
            f"price={self.price:.2f}, qty={self.quantity})"
        )


def create_buy_order(price: float, quantity: int, order_id: Optional[str] = None) -> Order:
    """Convenience function to create a buy order."""
    return Order(side=Side.BUY, price=price, quantity=quantity, order_id=order_id)


def create_sell_order(price: float, quantity: int, order_id: Optional[str] = None) -> Order:
    """Convenience function to create a sell order."""
    return Order(side=Side.SELL, price=price, quantity=quantity, order_id=order_id)
