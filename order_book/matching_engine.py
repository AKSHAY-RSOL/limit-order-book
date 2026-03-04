"""
Matching Engine Implementation.

The matching engine is the core component that:
1. Receives incoming orders
2. Attempts to match them against resting orders in the book
3. Executes trades when matches occur
4. Adds unmatched (or partially matched) orders to the book

Matching Rules (Price-Time Priority):
- Price Priority: Better prices always execute first
  - For BUYS: Higher price = better
  - For SELLS: Lower price = better
- Time Priority: At the same price, earlier orders execute first
"""

from typing import List, Optional, Callable, Dict
from .order import Order, Trade, Side, OrderStatus
from .order_book import OrderBook


class MatchingEngine:
    """
    The matching engine processes orders and executes trades.
    
    For each incoming order:
    1. Check if it can match with orders on the opposite side
    2. Execute trades at the resting order's price
    3. Continue until the order is filled or no more matches
    4. If quantity remains, add to the order book
    
    Example:
        >>> engine = MatchingEngine()
        >>> engine.process_order(Order(Side.BUY, 100.0, 10))
        >>> engine.process_order(Order(Side.SELL, 99.0, 5))  # Matches!
        >>> len(engine.get_trades())
        1
    """
    
    def __init__(self):
        """Initialize the matching engine with an empty order book."""
        self._order_book = OrderBook()
        self._trades: List[Trade] = []
        self._trade_callbacks: List[Callable[[Trade], None]] = []
        self._all_orders: Dict[str, Order] = {}  # Track all orders for lookup
    
    @property
    def order_book(self) -> OrderBook:
        """Access the underlying order book."""
        return self._order_book
    
    def register_trade_callback(self, callback: Callable[[Trade], None]) -> None:
        """
        Register a callback function to be called when a trade executes.
        
        Args:
            callback: Function that takes a Trade object
        """
        self._trade_callbacks.append(callback)
    
    def _notify_trade(self, trade: Trade) -> None:
        """Notify all registered callbacks of a new trade."""
        for callback in self._trade_callbacks:
            callback(trade)
    
    def process_order(self, order: Order) -> List[Trade]:
        """
        Process an incoming order through the matching engine.
        
        The order will be matched against resting orders on the opposite
        side of the book. Trades execute at the resting order's price.
        
        Args:
            order: The incoming order to process
            
        Returns:
            List of trades that were executed
            
        Algorithm:
            1. While order has remaining quantity:
               a. Get best order from opposite side
               b. Check if prices cross (can trade)
               c. If yes: execute trade, update quantities
               d. If no: break
            2. If order has remaining quantity: add to book
        """
        trades: List[Trade] = []
        
        # Track all orders for lookup (even if fully matched)
        self._all_orders[order.order_id] = order
        
        if order.side == Side.BUY:
            trades = self._match_buy_order(order)
        else:
            trades = self._match_sell_order(order)
        
        # If order still has remaining quantity, add to book
        if order.is_active and order.remaining_quantity > 0:
            self._order_book.add_order(order)
        
        return trades
    
    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        """
        Match a buy order against resting sell orders.
        
        A buy order can match with a sell order if:
        buy_price >= sell_price (buyer willing to pay seller's ask)
        
        Trade executes at the RESTING order's price (the ask price).
        """
        trades: List[Trade] = []
        
        while buy_order.remaining_quantity > 0:
            # Get best ask (lowest sell price)
            best_ask = self._order_book.get_best_ask()
            
            # No more asks to match against
            if best_ask is None:
                break
            
            # Check if prices cross
            # Buy can match if buy_price >= ask_price
            if buy_order.price < best_ask.price:
                break  # No match possible
            
            # Calculate trade quantity
            trade_qty = min(buy_order.remaining_quantity, best_ask.remaining_quantity)
            
            # Execute at the resting order's price (the ask)
            trade_price = best_ask.price
            
            # Create the trade
            trade = Trade(
                buy_order_id=buy_order.order_id,
                sell_order_id=best_ask.order_id,
                price=trade_price,
                quantity=trade_qty
            )
            
            # Update order quantities
            buy_order.fill(trade_qty)
            best_ask.fill(trade_qty)
            
            # Note: Filled orders are cleaned up via lazy deletion
            # in get_best_ask() - no explicit pop needed
            
            trades.append(trade)
            self._trades.append(trade)
            self._notify_trade(trade)
        
        return trades
    
    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        """
        Match a sell order against resting buy orders.
        
        A sell order can match with a buy order if:
        sell_price <= buy_price (seller willing to accept buyer's bid)
        
        Trade executes at the RESTING order's price (the bid price).
        """
        trades: List[Trade] = []
        
        while sell_order.remaining_quantity > 0:
            # Get best bid (highest buy price)
            best_bid = self._order_book.get_best_bid()
            
            # No more bids to match against
            if best_bid is None:
                break
            
            # Check if prices cross
            # Sell can match if sell_price <= bid_price
            if sell_order.price > best_bid.price:
                break  # No match possible
            
            # Calculate trade quantity
            trade_qty = min(sell_order.remaining_quantity, best_bid.remaining_quantity)
            
            # Execute at the resting order's price (the bid)
            trade_price = best_bid.price
            
            # Create the trade
            trade = Trade(
                buy_order_id=best_bid.order_id,
                sell_order_id=sell_order.order_id,
                price=trade_price,
                quantity=trade_qty
            )
            
            # Update order quantities
            sell_order.fill(trade_qty)
            best_bid.fill(trade_qty)
            
            # Note: Filled orders are cleaned up via lazy deletion
            # in get_best_bid() - no explicit pop needed
            
            trades.append(trade)
            self._trades.append(trade)
            self._notify_trade(trade)
        
        return trades
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order in the book.
        
        Args:
            order_id: The ID of the order to cancel
            
        Returns:
            True if cancelled, False if not found or already inactive
        """
        return self._order_book.cancel_order(order_id)
    
    def get_trades(self) -> List[Trade]:
        """Get all executed trades."""
        return self._trades.copy()
    
    def get_trade_count(self) -> int:
        """Get the number of executed trades."""
        return len(self._trades)
    
    def get_total_volume(self) -> int:
        """Get total traded volume (sum of all trade quantities)."""
        return sum(trade.quantity for trade in self._trades)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID (includes fully matched orders)."""
        return self._all_orders.get(order_id)
    
    def get_vwap(self) -> Optional[float]:
        """
        Calculate Volume-Weighted Average Price (VWAP).
        
        VWAP = sum(price * quantity) / sum(quantity)
        
        Returns:
            VWAP if there are trades, None otherwise
        """
        if not self._trades:
            return None
        
        total_value = sum(t.price * t.quantity for t in self._trades)
        total_volume = sum(t.quantity for t in self._trades)
        
        return total_value / total_volume
    
    def __str__(self) -> str:
        """String representation showing engine statistics."""
        lines = [
            "=" * 50,
            "           MATCHING ENGINE STATUS",
            "=" * 50,
            f"Total Trades: {len(self._trades)}",
            f"Total Volume: {self.get_total_volume()}",
        ]
        
        vwap = self.get_vwap()
        if vwap:
            lines.append(f"VWAP: {vwap:.4f}")
        
        lines.append("")
        lines.append(str(self._order_book))
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"MatchingEngine(trades={len(self._trades)}, " \
               f"bids={self._order_book.bid_count}, " \
               f"asks={self._order_book.ask_count})"
