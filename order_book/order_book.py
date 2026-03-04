"""
Order Book Implementation using Binary Heaps.

This module implements the order book with efficient data structures:
- Bids (buy orders): Max-heap (highest price first)
- Asks (sell orders): Min-heap (lowest price first)

Time Complexity:
- Add order: O(log N)
- Get best bid/ask: O(1)
- Remove best bid/ask: O(log N)
- Cancel order: O(N) - requires linear search
"""

import heapq
from typing import Optional, List, Dict, Tuple
from collections import defaultdict
from .order import Order, Side, OrderStatus


class OrderBook:
    """
    A limit order book maintaining bid and ask sides.
    
    Uses binary heaps for efficient price-time priority ordering:
    - Bids: Max-heap implemented via negated comparison
    - Asks: Min-heap (natural ordering)
    
    The Order.__lt__ method handles the comparison logic for proper heap ordering.
    
    Attributes:
        bids: Heap of buy orders (best = highest price)
        asks: Heap of sell orders (best = lowest price)
        orders: Dictionary mapping order_id to Order for O(1) lookup
    
    Time Complexity:
        - add_order: O(log N)
        - get_best_bid/ask: O(1) amortized
        - pop_best_bid/ask: O(log N)
        - cancel_order: O(1) for marking, O(N) for removal
    """
    
    def __init__(self):
        """Initialize empty order book."""
        self._bids: List[Order] = []  # Max-heap (via Order.__lt__)
        self._asks: List[Order] = []  # Min-heap (via Order.__lt__)
        self._orders: Dict[str, Order] = {}  # order_id -> Order
        
        # Statistics
        self._total_orders_added = 0
        self._total_orders_cancelled = 0
    
    def add_order(self, order: Order) -> None:
        """
        Add an order to the appropriate side of the book.
        
        Args:
            order: The order to add
            
        Raises:
            ValueError: If order is not active or already in book
        """
        if not order.is_active:
            raise ValueError(f"Cannot add inactive order: {order}")
        
        if order.order_id in self._orders:
            raise ValueError(f"Order {order.order_id} already exists in book")
        
        self._orders[order.order_id] = order
        self._total_orders_added += 1
        
        if order.side == Side.BUY:
            heapq.heappush(self._bids, order)
        else:
            heapq.heappush(self._asks, order)
    
    def _clean_heap_top(self, heap: List[Order]) -> None:
        """Remove inactive orders from the top of a heap."""
        while heap and not heap[0].is_active:
            heapq.heappop(heap)
    
    def get_best_bid(self) -> Optional[Order]:
        """
        Get the best (highest price) bid order.
        
        Returns:
            The best bid order, or None if no active bids
            
        Time Complexity: O(1) amortized (may need to clean inactive orders)
        """
        self._clean_heap_top(self._bids)
        return self._bids[0] if self._bids else None
    
    def get_best_ask(self) -> Optional[Order]:
        """
        Get the best (lowest price) ask order.
        
        Returns:
            The best ask order, or None if no active asks
            
        Time Complexity: O(1) amortized (may need to clean inactive orders)
        """
        self._clean_heap_top(self._asks)
        return self._asks[0] if self._asks else None
    
    def pop_best_bid(self) -> Optional[Order]:
        """
        Remove and return the best bid order.
        
        Returns:
            The best bid order, or None if no active bids
            
        Time Complexity: O(log N)
        """
        self._clean_heap_top(self._bids)
        if self._bids:
            return heapq.heappop(self._bids)
        return None
    
    def pop_best_ask(self) -> Optional[Order]:
        """
        Remove and return the best ask order.
        
        Returns:
            The best ask order, or None if no active asks
            
        Time Complexity: O(log N)
        """
        self._clean_heap_top(self._asks)
        if self._asks:
            return heapq.heappop(self._asks)
        return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order by ID.
        
        The order is marked as cancelled but not immediately removed from
        the heap (lazy deletion). It will be cleaned up when it reaches
        the top of the heap.
        
        Args:
            order_id: The ID of the order to cancel
            
        Returns:
            True if order was found and cancelled, False otherwise
        """
        if order_id not in self._orders:
            return False
        
        order = self._orders[order_id]
        if not order.is_active:
            return False
        
        order.cancel()
        self._total_orders_cancelled += 1
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        return self._orders.get(order_id)
    
    @property
    def bid_count(self) -> int:
        """Count of active bid orders."""
        return sum(1 for o in self._bids if o.is_active)
    
    @property
    def ask_count(self) -> int:
        """Count of active ask orders."""
        return sum(1 for o in self._asks if o.is_active)
    
    @property
    def spread(self) -> Optional[float]:
        """
        Calculate the bid-ask spread.
        
        Returns:
            The difference between best ask and best bid prices,
            or None if either side is empty.
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        return best_ask.price - best_bid.price
    
    @property
    def midpoint(self) -> Optional[float]:
        """
        Calculate the midpoint price.
        
        Returns:
            The average of best bid and best ask prices,
            or None if either side is empty.
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        return (best_bid.price + best_ask.price) / 2
    
    def get_bids_at_price(self, price: float) -> List[Order]:
        """Get all active bid orders at a specific price level."""
        return [o for o in self._bids if o.is_active and o.price == price]
    
    def get_asks_at_price(self, price: float) -> List[Order]:
        """Get all active ask orders at a specific price level."""
        return [o for o in self._asks if o.is_active and o.price == price]
    
    def get_depth(self, levels: int = 5) -> Dict[str, List[Tuple[float, int]]]:
        """
        Get market depth (price levels and quantities).
        
        Args:
            levels: Number of price levels to return
            
        Returns:
            Dictionary with 'bids' and 'asks', each containing
            list of (price, total_quantity) tuples sorted by price priority.
        """
        # Aggregate quantities by price level
        bid_levels: Dict[float, int] = defaultdict(int)
        ask_levels: Dict[float, int] = defaultdict(int)
        
        for order in self._bids:
            if order.is_active:
                bid_levels[order.price] += order.remaining_quantity
        
        for order in self._asks:
            if order.is_active:
                ask_levels[order.price] += order.remaining_quantity
        
        # Sort and take top levels
        sorted_bids = sorted(bid_levels.items(), key=lambda x: -x[0])[:levels]
        sorted_asks = sorted(ask_levels.items(), key=lambda x: x[0])[:levels]
        
        return {
            'bids': sorted_bids,
            'asks': sorted_asks
        }
    
    def __str__(self) -> str:
        """Pretty print the order book."""
        depth = self.get_depth(10)
        
        lines = ["=" * 50]
        lines.append("              ORDER BOOK")
        lines.append("=" * 50)
        lines.append(f"{'Price':>12} {'Qty':>10} │ {'Qty':<10} {'Price':<12}")
        lines.append("-" * 50)
        
        # Get max rows to display
        max_rows = max(len(depth['bids']), len(depth['asks']))
        
        for i in range(max_rows):
            bid_str = ""
            ask_str = ""
            
            if i < len(depth['bids']):
                price, qty = depth['bids'][i]
                bid_str = f"{price:>12.2f} {qty:>10}"
            else:
                bid_str = " " * 23
            
            if i < len(depth['asks']):
                price, qty = depth['asks'][i]
                ask_str = f"{qty:<10} {price:<12.2f}"
            
            lines.append(f"{bid_str} │ {ask_str}")
        
        lines.append("=" * 50)
        
        spread = self.spread
        midpoint = self.midpoint
        spread_str = f"{spread:.2f}" if spread is not None else "N/A"
        midpoint_str = f"{midpoint:.2f}" if midpoint is not None else "N/A"
        
        lines.append(f"Spread: {spread_str} | Midpoint: {midpoint_str}")
        lines.append(f"Active Bids: {self.bid_count} | Active Asks: {self.ask_count}")
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"OrderBook(bids={self.bid_count}, asks={self.ask_count})"
