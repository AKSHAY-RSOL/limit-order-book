"""
Unit Tests for the OrderBook Class.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from order_book.order import Order, Side, OrderStatus, reset_sequence_counter, Trade
from order_book.order_book import OrderBook


class TestOrderBook:
    """Test cases for the OrderBook class."""
    
    def setup_method(self):
        """Reset state before each test."""
        reset_sequence_counter()
        Trade.reset_counter()
        self.book = OrderBook()
    
    def test_empty_book(self):
        """Test empty order book state."""
        assert self.book.get_best_bid() is None
        assert self.book.get_best_ask() is None
        assert self.book.bid_count == 0
        assert self.book.ask_count == 0
        assert self.book.spread is None
        assert self.book.midpoint is None
    
    def test_add_single_bid(self):
        """Test adding a single bid order."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        self.book.add_order(order)
        
        assert self.book.bid_count == 1
        assert self.book.ask_count == 0
        assert self.book.get_best_bid() == order
    
    def test_add_single_ask(self):
        """Test adding a single ask order."""
        order = Order(side=Side.SELL, price=101.0, quantity=10)
        self.book.add_order(order)
        
        assert self.book.bid_count == 0
        assert self.book.ask_count == 1
        assert self.book.get_best_ask() == order
    
    def test_best_bid_is_highest_price(self):
        """Test that best bid is the highest price."""
        self.book.add_order(Order(side=Side.BUY, price=99.0, quantity=10))
        self.book.add_order(Order(side=Side.BUY, price=101.0, quantity=10))
        self.book.add_order(Order(side=Side.BUY, price=100.0, quantity=10))
        
        assert self.book.get_best_bid().price == 101.0
    
    def test_best_ask_is_lowest_price(self):
        """Test that best ask is the lowest price."""
        self.book.add_order(Order(side=Side.SELL, price=102.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=100.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=101.0, quantity=10))
        
        assert self.book.get_best_ask().price == 100.0
    
    def test_time_priority_for_bids(self):
        """Test that earlier bids at same price have priority."""
        order1 = Order(side=Side.BUY, price=100.0, quantity=10, order_id="FIRST")
        order2 = Order(side=Side.BUY, price=100.0, quantity=10, order_id="SECOND")
        
        self.book.add_order(order1)
        self.book.add_order(order2)
        
        # First order should be best bid
        assert self.book.get_best_bid().order_id == "FIRST"
        
        # After popping, second should be best
        self.book.pop_best_bid()
        assert self.book.get_best_bid().order_id == "SECOND"
    
    def test_time_priority_for_asks(self):
        """Test that earlier asks at same price have priority."""
        order1 = Order(side=Side.SELL, price=100.0, quantity=10, order_id="FIRST")
        order2 = Order(side=Side.SELL, price=100.0, quantity=10, order_id="SECOND")
        
        self.book.add_order(order1)
        self.book.add_order(order2)
        
        # First order should be best ask
        assert self.book.get_best_ask().order_id == "FIRST"
        
        # After popping, second should be best
        self.book.pop_best_ask()
        assert self.book.get_best_ask().order_id == "SECOND"
    
    def test_pop_best_bid(self):
        """Test removing best bid."""
        order1 = Order(side=Side.BUY, price=100.0, quantity=10)
        order2 = Order(side=Side.BUY, price=99.0, quantity=10)
        
        self.book.add_order(order1)
        self.book.add_order(order2)
        
        popped = self.book.pop_best_bid()
        assert popped.price == 100.0
        assert self.book.get_best_bid().price == 99.0
    
    def test_pop_best_ask(self):
        """Test removing best ask."""
        order1 = Order(side=Side.SELL, price=100.0, quantity=10)
        order2 = Order(side=Side.SELL, price=101.0, quantity=10)
        
        self.book.add_order(order1)
        self.book.add_order(order2)
        
        popped = self.book.pop_best_ask()
        assert popped.price == 100.0
        assert self.book.get_best_ask().price == 101.0
    
    def test_cancel_order(self):
        """Test cancelling an order."""
        order = Order(side=Side.BUY, price=100.0, quantity=10, order_id="TO_CANCEL")
        self.book.add_order(order)
        
        result = self.book.cancel_order("TO_CANCEL")
        
        assert result is True
        assert order.status == OrderStatus.CANCELLED
        assert not order.is_active
    
    def test_cancel_nonexistent_order(self):
        """Test cancelling an order that doesn't exist."""
        result = self.book.cancel_order("NONEXISTENT")
        assert result is False
    
    def test_cancelled_orders_cleaned_from_heap(self):
        """Test that cancelled orders are cleaned when accessing best."""
        order1 = Order(side=Side.BUY, price=100.0, quantity=10, order_id="CANCEL_ME")
        order2 = Order(side=Side.BUY, price=99.0, quantity=10, order_id="KEEP_ME")
        
        self.book.add_order(order1)
        self.book.add_order(order2)
        
        self.book.cancel_order("CANCEL_ME")
        
        # Best bid should now be order2
        assert self.book.get_best_bid().order_id == "KEEP_ME"
    
    def test_spread_calculation(self):
        """Test bid-ask spread calculation."""
        self.book.add_order(Order(side=Side.BUY, price=99.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=101.0, quantity=10))
        
        assert self.book.spread == 2.0
    
    def test_midpoint_calculation(self):
        """Test midpoint calculation."""
        self.book.add_order(Order(side=Side.BUY, price=99.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=101.0, quantity=10))
        
        assert self.book.midpoint == 100.0
    
    def test_get_order(self):
        """Test retrieving order by ID."""
        order = Order(side=Side.BUY, price=100.0, quantity=10, order_id="FIND_ME")
        self.book.add_order(order)
        
        found = self.book.get_order("FIND_ME")
        assert found == order
        assert self.book.get_order("NOT_FOUND") is None
    
    def test_duplicate_order_raises_error(self):
        """Test that adding duplicate order ID raises error."""
        order1 = Order(side=Side.BUY, price=100.0, quantity=10, order_id="DUPE")
        order2 = Order(side=Side.BUY, price=100.0, quantity=10, order_id="DUPE")
        
        self.book.add_order(order1)
        
        with pytest.raises(ValueError):
            self.book.add_order(order2)
    
    def test_inactive_order_rejected(self):
        """Test that inactive orders cannot be added."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        order.cancel()
        
        with pytest.raises(ValueError):
            self.book.add_order(order)
    
    def test_get_depth(self):
        """Test market depth calculation."""
        # Add multiple orders at different price levels
        self.book.add_order(Order(side=Side.BUY, price=100.0, quantity=10))
        self.book.add_order(Order(side=Side.BUY, price=100.0, quantity=5))  # Same level
        self.book.add_order(Order(side=Side.BUY, price=99.0, quantity=20))
        
        self.book.add_order(Order(side=Side.SELL, price=101.0, quantity=8))
        self.book.add_order(Order(side=Side.SELL, price=102.0, quantity=12))
        
        depth = self.book.get_depth(5)
        
        # Bids should be sorted high to low
        assert depth['bids'][0] == (100.0, 15)  # 10 + 5
        assert depth['bids'][1] == (99.0, 20)
        
        # Asks should be sorted low to high
        assert depth['asks'][0] == (101.0, 8)
        assert depth['asks'][1] == (102.0, 12)
    
    def test_many_orders_heap_property(self):
        """Test that heap property is maintained with many orders."""
        import random
        random.seed(42)
        
        prices = [random.uniform(95, 105) for _ in range(100)]
        
        for price in prices:
            self.book.add_order(Order(side=Side.BUY, price=price, quantity=10))
        
        # Extract all in order - should be sorted high to low
        extracted_prices = []
        while self.book.get_best_bid():
            extracted_prices.append(self.book.pop_best_bid().price)
        
        # Verify sorted high to low
        assert extracted_prices == sorted(extracted_prices, reverse=True)
    
    def test_str_representation(self):
        """Test string representation of order book."""
        self.book.add_order(Order(side=Side.BUY, price=100.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=101.0, quantity=5))
        
        book_str = str(self.book)
        
        assert "ORDER BOOK" in book_str
        assert "100.00" in book_str
        assert "101.00" in book_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
