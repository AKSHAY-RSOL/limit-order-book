"""
Unit Tests for Order and Trade Classes.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from order_book.order import (
    Order, Trade, Side, OrderStatus,
    create_buy_order, create_sell_order,
    reset_sequence_counter
)


class TestOrder:
    """Test cases for the Order class."""
    
    def setup_method(self):
        """Reset sequence counter before each test."""
        reset_sequence_counter()
        Trade.reset_counter()
    
    def test_create_buy_order(self):
        """Test creating a basic buy order."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        
        assert order.side == Side.BUY
        assert order.price == 100.0
        assert order.quantity == 10
        assert order.remaining_quantity == 10
        assert order.status == OrderStatus.NEW
        assert order.is_active
    
    def test_create_sell_order(self):
        """Test creating a basic sell order."""
        order = Order(side=Side.SELL, price=101.0, quantity=5)
        
        assert order.side == Side.SELL
        assert order.price == 101.0
        assert order.quantity == 5
        assert order.remaining_quantity == 5
        assert order.status == OrderStatus.NEW
        assert order.is_active
    
    def test_order_id_auto_generated(self):
        """Test that order IDs are auto-generated."""
        order1 = Order(side=Side.BUY, price=100.0, quantity=10)
        order2 = Order(side=Side.BUY, price=100.0, quantity=10)
        
        assert order1.order_id is not None
        assert order2.order_id is not None
        assert order1.order_id != order2.order_id
    
    def test_order_id_custom(self):
        """Test setting custom order ID."""
        order = Order(side=Side.BUY, price=100.0, quantity=10, order_id="CUSTOM-001")
        assert order.order_id == "CUSTOM-001"
    
    def test_fill_partial(self):
        """Test partially filling an order."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        order.fill(3)
        
        assert order.remaining_quantity == 7
        assert order.filled_quantity == 3
        assert order.status == OrderStatus.PARTIAL
        assert order.is_active
    
    def test_fill_complete(self):
        """Test completely filling an order."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        order.fill(10)
        
        assert order.remaining_quantity == 0
        assert order.filled_quantity == 10
        assert order.status == OrderStatus.FILLED
        assert not order.is_active
    
    def test_fill_multiple_times(self):
        """Test filling an order in multiple steps."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        order.fill(3)
        order.fill(4)
        order.fill(3)
        
        assert order.remaining_quantity == 0
        assert order.filled_quantity == 10
        assert order.status == OrderStatus.FILLED
    
    def test_fill_exceeds_remaining_raises_error(self):
        """Test that overfilling raises an error."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        
        with pytest.raises(ValueError):
            order.fill(11)
    
    def test_cancel_order(self):
        """Test cancelling an order."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        order.cancel()
        
        assert order.status == OrderStatus.CANCELLED
        assert not order.is_active
    
    def test_sequence_numbers_monotonic(self):
        """Test that sequence numbers are monotonically increasing."""
        order1 = Order(side=Side.BUY, price=100.0, quantity=10)
        order2 = Order(side=Side.BUY, price=100.0, quantity=10)
        order3 = Order(side=Side.BUY, price=100.0, quantity=10)
        
        assert order1.sequence < order2.sequence < order3.sequence
    
    def test_buy_order_comparison_price_priority(self):
        """Test that buy orders compare by price (higher is better)."""
        # Higher price should be "less than" for heap ordering
        high_price = Order(side=Side.BUY, price=101.0, quantity=10)
        low_price = Order(side=Side.BUY, price=100.0, quantity=10)
        
        # high_price should come first (be "less than" for min-heap)
        assert high_price < low_price
    
    def test_buy_order_comparison_time_priority(self):
        """Test that buy orders at same price compare by time."""
        order1 = Order(side=Side.BUY, price=100.0, quantity=10)
        order2 = Order(side=Side.BUY, price=100.0, quantity=10)
        
        # Earlier order should come first
        assert order1 < order2
    
    def test_sell_order_comparison_price_priority(self):
        """Test that sell orders compare by price (lower is better)."""
        high_price = Order(side=Side.SELL, price=101.0, quantity=10)
        low_price = Order(side=Side.SELL, price=100.0, quantity=10)
        
        # low_price should come first (be "less than" for min-heap)
        assert low_price < high_price
    
    def test_sell_order_comparison_time_priority(self):
        """Test that sell orders at same price compare by time."""
        order1 = Order(side=Side.SELL, price=100.0, quantity=10)
        order2 = Order(side=Side.SELL, price=100.0, quantity=10)
        
        # Earlier order should come first
        assert order1 < order2
    
    def test_convenience_functions(self):
        """Test create_buy_order and create_sell_order helpers."""
        buy = create_buy_order(100.0, 10)
        sell = create_sell_order(101.0, 5)
        
        assert buy.side == Side.BUY
        assert buy.price == 100.0
        assert buy.quantity == 10
        
        assert sell.side == Side.SELL
        assert sell.price == 101.0
        assert sell.quantity == 5


class TestTrade:
    """Test cases for the Trade class."""
    
    def setup_method(self):
        """Reset trade counter before each test."""
        Trade.reset_counter()
    
    def test_create_trade(self):
        """Test creating a basic trade."""
        trade = Trade(
            buy_order_id="BUY-001",
            sell_order_id="SELL-001",
            price=100.0,
            quantity=10
        )
        
        assert trade.buy_order_id == "BUY-001"
        assert trade.sell_order_id == "SELL-001"
        assert trade.price == 100.0
        assert trade.quantity == 10
        assert trade.trade_id is not None
    
    def test_trade_id_auto_generated(self):
        """Test that trade IDs are auto-generated."""
        trade1 = Trade(
            buy_order_id="BUY-001",
            sell_order_id="SELL-001",
            price=100.0,
            quantity=10
        )
        trade2 = Trade(
            buy_order_id="BUY-002",
            sell_order_id="SELL-002",
            price=100.0,
            quantity=10
        )
        
        assert trade1.trade_id != trade2.trade_id
    
    def test_trade_repr(self):
        """Test trade string representation."""
        trade = Trade(
            buy_order_id="BUY-001",
            sell_order_id="SELL-001",
            price=100.0,
            quantity=10
        )
        
        repr_str = repr(trade)
        assert "BUY-001" in repr_str
        assert "SELL-001" in repr_str
        assert "100.00" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
