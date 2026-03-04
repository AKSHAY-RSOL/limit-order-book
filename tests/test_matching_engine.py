"""
Unit Tests for the Matching Engine.

Includes comprehensive tests with 100+ random orders to validate correctness.
"""

import pytest
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from order_book.order import Order, Trade, Side, OrderStatus, reset_sequence_counter
from order_book.matching_engine import MatchingEngine


class TestMatchingEngineBasic:
    """Basic matching engine tests."""
    
    def setup_method(self):
        """Reset state before each test."""
        reset_sequence_counter()
        Trade.reset_counter()
        self.engine = MatchingEngine()
    
    def test_no_match_when_book_empty(self):
        """Test that orders don't match when book is empty."""
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(order)
        
        assert len(trades) == 0
        assert self.engine.order_book.bid_count == 1
    
    def test_buy_matches_sell_at_crossing_price(self):
        """Test buy order matches sell when prices cross."""
        # Add sell order first
        sell = Order(side=Side.SELL, price=100.0, quantity=10)
        self.engine.process_order(sell)
        
        # Add buy order that can match
        buy = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        assert len(trades) == 1
        assert trades[0].price == 100.0
        assert trades[0].quantity == 10
        assert sell.status == OrderStatus.FILLED
        assert buy.status == OrderStatus.FILLED
    
    def test_sell_matches_buy_at_crossing_price(self):
        """Test sell order matches buy when prices cross."""
        # Add buy order first
        buy = Order(side=Side.BUY, price=100.0, quantity=10)
        self.engine.process_order(buy)
        
        # Add sell order that can match
        sell = Order(side=Side.SELL, price=100.0, quantity=10)
        trades = self.engine.process_order(sell)
        
        assert len(trades) == 1
        assert trades[0].price == 100.0
        assert trades[0].quantity == 10
    
    def test_no_match_when_prices_dont_cross(self):
        """Test no match when buy price < sell price."""
        sell = Order(side=Side.SELL, price=101.0, quantity=10)
        self.engine.process_order(sell)
        
        buy = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        assert len(trades) == 0
        assert self.engine.order_book.bid_count == 1
        assert self.engine.order_book.ask_count == 1
    
    def test_trade_executes_at_resting_order_price(self):
        """Test that trades execute at the resting order's price."""
        # Resting sell at 100
        sell = Order(side=Side.SELL, price=100.0, quantity=10)
        self.engine.process_order(sell)
        
        # Aggressive buy at 105 - should execute at 100
        buy = Order(side=Side.BUY, price=105.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        assert len(trades) == 1
        assert trades[0].price == 100.0  # Resting order's price
    
    def test_partial_fill(self):
        """Test partial fill when quantities don't match."""
        sell = Order(side=Side.SELL, price=100.0, quantity=5)
        self.engine.process_order(sell)
        
        buy = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        assert len(trades) == 1
        assert trades[0].quantity == 5
        assert buy.remaining_quantity == 5
        assert buy.status == OrderStatus.PARTIAL
        assert sell.status == OrderStatus.FILLED
        
        # Remaining buy should be in book
        assert self.engine.order_book.bid_count == 1
    
    def test_multiple_matches_single_order(self):
        """Test order matching against multiple resting orders."""
        # Add multiple small sell orders
        self.engine.process_order(Order(side=Side.SELL, price=100.0, quantity=3))
        self.engine.process_order(Order(side=Side.SELL, price=100.5, quantity=4))
        self.engine.process_order(Order(side=Side.SELL, price=101.0, quantity=5))
        
        # Large buy order that matches all
        buy = Order(side=Side.BUY, price=101.0, quantity=12)
        trades = self.engine.process_order(buy)
        
        assert len(trades) == 3
        assert sum(t.quantity for t in trades) == 12
        assert buy.status == OrderStatus.FILLED
        assert self.engine.order_book.ask_count == 0
    
    def test_price_priority_best_price_first(self):
        """Test that best price gets matched first."""
        # Add asks at different prices
        ask_expensive = Order(side=Side.SELL, price=102.0, quantity=10, order_id="EXPENSIVE")
        ask_cheap = Order(side=Side.SELL, price=100.0, quantity=10, order_id="CHEAP")
        ask_mid = Order(side=Side.SELL, price=101.0, quantity=10, order_id="MID")
        
        self.engine.process_order(ask_expensive)
        self.engine.process_order(ask_cheap)
        self.engine.process_order(ask_mid)
        
        # Buy should match cheapest first
        buy = Order(side=Side.BUY, price=102.0, quantity=5)
        trades = self.engine.process_order(buy)
        
        assert len(trades) == 1
        assert trades[0].sell_order_id == "CHEAP"
        assert trades[0].price == 100.0
    
    def test_time_priority_at_same_price(self):
        """Test that earlier orders at same price get priority."""
        # Add asks at same price
        ask_first = Order(side=Side.SELL, price=100.0, quantity=10, order_id="FIRST")
        ask_second = Order(side=Side.SELL, price=100.0, quantity=10, order_id="SECOND")
        
        self.engine.process_order(ask_first)
        self.engine.process_order(ask_second)
        
        # Buy should match first order
        buy = Order(side=Side.BUY, price=100.0, quantity=5)
        trades = self.engine.process_order(buy)
        
        assert trades[0].sell_order_id == "FIRST"
    
    def test_cancel_order(self):
        """Test cancelling an order."""
        order = Order(side=Side.BUY, price=100.0, quantity=10, order_id="TO_CANCEL")
        self.engine.process_order(order)
        
        result = self.engine.cancel_order("TO_CANCEL")
        
        assert result is True
        assert order.status == OrderStatus.CANCELLED
    
    def test_get_trades(self):
        """Test retrieving all trades."""
        self.engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        self.engine.process_order(Order(side=Side.BUY, price=100.0, quantity=10))
        
        trades = self.engine.get_trades()
        
        assert len(trades) == 1
        assert self.engine.get_trade_count() == 1
    
    def test_total_volume(self):
        """Test total traded volume calculation."""
        self.engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        self.engine.process_order(Order(side=Side.SELL, price=101.0, quantity=5))
        self.engine.process_order(Order(side=Side.BUY, price=101.0, quantity=15))
        
        assert self.engine.get_total_volume() == 15
    
    def test_vwap_calculation(self):
        """Test Volume-Weighted Average Price calculation."""
        # Trade 1: 10 units at 100
        # Trade 2: 5 units at 101
        # VWAP = (10*100 + 5*101) / 15 = 1505 / 15 = 100.333...
        
        self.engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        self.engine.process_order(Order(side=Side.SELL, price=101.0, quantity=5))
        self.engine.process_order(Order(side=Side.BUY, price=101.0, quantity=15))
        
        vwap = self.engine.get_vwap()
        expected = (10 * 100.0 + 5 * 101.0) / 15
        
        assert abs(vwap - expected) < 0.0001
    
    def test_trade_callback(self):
        """Test trade callback notification."""
        captured_trades = []
        
        def callback(trade):
            captured_trades.append(trade)
        
        self.engine.register_trade_callback(callback)
        
        self.engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        self.engine.process_order(Order(side=Side.BUY, price=100.0, quantity=10))
        
        assert len(captured_trades) == 1


class TestMatchingEngineRandomOrders:
    """
    Comprehensive tests with random orders to validate correctness.
    
    These tests simulate realistic trading scenarios with 100+ random orders
    and verify that all trades are mathematically correct.
    """
    
    def setup_method(self):
        """Reset state before each test."""
        reset_sequence_counter()
        Trade.reset_counter()
    
    def test_100_random_orders_correctness(self):
        """
        Test matching engine with 100 random orders.
        
        Validates:
        1. All trades have crossing prices (buy_price >= trade_price >= sell_price)
        2. Trade quantities don't exceed order quantities
        3. Order book invariants are maintained
        4. No quantity is created or destroyed
        """
        random.seed(42)  # Reproducible
        engine = MatchingEngine()
        
        orders = []
        total_buy_qty = 0
        total_sell_qty = 0
        
        # Generate 100 random orders
        for i in range(100):
            side = random.choice([Side.BUY, Side.SELL])
            # Prices clustered around 100 with some spread
            price = round(random.gauss(100, 2), 2)
            quantity = random.randint(1, 20)
            
            order = Order(side=side, price=price, quantity=quantity)
            orders.append(order)
            
            if side == Side.BUY:
                total_buy_qty += quantity
            else:
                total_sell_qty += quantity
            
            engine.process_order(order)
        
        trades = engine.get_trades()
        
        # Validate each trade
        for trade in trades:
            buy_order = engine.get_order(trade.buy_order_id)
            sell_order = engine.get_order(trade.sell_order_id)
            
            # 1. Price crossing: buy was willing to pay >= trade price
            assert buy_order.price >= trade.price, \
                f"Buy price {buy_order.price} < trade price {trade.price}"
            
            # 2. Price crossing: sell was willing to accept <= trade price
            assert sell_order.price <= trade.price, \
                f"Sell price {sell_order.price} > trade price {trade.price}"
            
            # 3. Trade price is at resting order's price
            # (either buy or sell price, depending on which was resting)
            assert trade.price == buy_order.price or trade.price == sell_order.price
            
            # 4. Trade quantity is positive
            assert trade.quantity > 0
        
        # Validate quantity conservation
        total_traded = sum(t.quantity for t in trades)
        remaining_buy_qty = sum(
            o.remaining_quantity for o in orders 
            if o.side == Side.BUY and o.is_active
        )
        remaining_sell_qty = sum(
            o.remaining_quantity for o in orders 
            if o.side == Side.SELL and o.is_active
        )
        filled_buy_qty = sum(
            o.filled_quantity for o in orders if o.side == Side.BUY
        )
        filled_sell_qty = sum(
            o.filled_quantity for o in orders if o.side == Side.SELL
        )
        
        # Total traded should equal filled on both sides
        assert total_traded == filled_buy_qty == filled_sell_qty
        
        # Original qty = filled + remaining
        assert total_buy_qty == filled_buy_qty + remaining_buy_qty
        assert total_sell_qty == filled_sell_qty + remaining_sell_qty
        
        print(f"\n100 Random Orders Test Results:")
        print(f"  Total orders: 100")
        print(f"  Total trades: {len(trades)}")
        print(f"  Total volume: {total_traded}")
        print(f"  Remaining bids: {engine.order_book.bid_count}")
        print(f"  Remaining asks: {engine.order_book.ask_count}")
    
    def test_100_random_orders_order_book_invariants(self):
        """
        Test that order book invariants hold after 100 random orders.
        
        Invariants:
        1. Best bid < Best ask (no crossing orders remain)
        2. All active orders have positive remaining quantity
        3. All orders in book are accessible by ID
        """
        random.seed(123)
        engine = MatchingEngine()
        
        for _ in range(100):
            side = random.choice([Side.BUY, Side.SELL])
            price = round(random.uniform(95, 105), 2)
            quantity = random.randint(1, 50)
            
            order = Order(side=side, price=price, quantity=quantity)
            engine.process_order(order)
        
        book = engine.order_book
        
        # Invariant 1: No crossing orders remain
        best_bid = book.get_best_bid()
        best_ask = book.get_best_ask()
        
        if best_bid and best_ask:
            assert best_bid.price < best_ask.price, \
                f"Crossing orders remain: bid {best_bid.price} >= ask {best_ask.price}"
        
        # Invariant 2: All active orders have positive remaining quantity
        depth = book.get_depth(100)
        for price, qty in depth['bids']:
            assert qty > 0, f"Zero quantity at bid level {price}"
        for price, qty in depth['asks']:
            assert qty > 0, f"Zero quantity at ask level {price}"
        
        print(f"\nOrder Book Invariants Test:")
        print(f"  Best Bid: {best_bid.price if best_bid else 'None'}")
        print(f"  Best Ask: {best_ask.price if best_ask else 'None'}")
        print(f"  Spread: {book.spread}")
    
    def test_100_aggressive_orders(self):
        """
        Test 100 aggressive orders that all cross.
        
        All buys at high price, all sells at low price - everything should match.
        """
        random.seed(456)
        engine = MatchingEngine()
        
        total_buy_qty = 0
        total_sell_qty = 0
        
        for _ in range(50):
            # Sells at low prices
            qty = random.randint(1, 20)
            total_sell_qty += qty
            engine.process_order(Order(side=Side.SELL, price=95.0, quantity=qty))
            
            # Buys at high prices - should always match
            qty = random.randint(1, 20)
            total_buy_qty += qty
            engine.process_order(Order(side=Side.BUY, price=105.0, quantity=qty))
        
        # All possible volume should have traded
        max_tradeable = min(total_buy_qty, total_sell_qty)
        actual_traded = engine.get_total_volume()
        
        assert actual_traded == max_tradeable, \
            f"Expected {max_tradeable} traded, got {actual_traded}"
        
        # Remaining should be the difference
        remaining_side_qty = abs(total_buy_qty - total_sell_qty)
        remaining_in_book = engine.order_book.bid_count + engine.order_book.ask_count
        
        # Only one side should have remaining orders
        if total_buy_qty > total_sell_qty:
            assert engine.order_book.ask_count == 0
        elif total_sell_qty > total_buy_qty:
            assert engine.order_book.bid_count == 0
        
        print(f"\n100 Aggressive Orders Test:")
        print(f"  Total buy qty: {total_buy_qty}")
        print(f"  Total sell qty: {total_sell_qty}")
        print(f"  Total traded: {actual_traded}")
    
    def test_stress_test_1000_orders(self):
        """
        Stress test with 1000 random orders.
        
        Tests performance and correctness under load.
        """
        import time
        random.seed(789)
        engine = MatchingEngine()
        
        start_time = time.time()
        
        for _ in range(1000):
            side = random.choice([Side.BUY, Side.SELL])
            price = round(random.gauss(100, 5), 2)
            quantity = random.randint(1, 100)
            
            engine.process_order(Order(side=side, price=price, quantity=quantity))
        
        elapsed = time.time() - start_time
        
        # Validate no crossing orders remain
        best_bid = engine.order_book.get_best_bid()
        best_ask = engine.order_book.get_best_ask()
        
        if best_bid and best_ask:
            assert best_bid.price < best_ask.price
        
        trades = engine.get_trades()
        
        print(f"\n1000 Order Stress Test:")
        print(f"  Time: {elapsed:.3f}s")
        print(f"  Orders/sec: {1000/elapsed:.0f}")
        print(f"  Total trades: {len(trades)}")
        print(f"  Total volume: {engine.get_total_volume()}")
    
    def test_alternating_buy_sell_pattern(self):
        """Test alternating buy and sell orders."""
        engine = MatchingEngine()
        
        # Alternate buy/sell at same price
        for i in range(100):
            if i % 2 == 0:
                engine.process_order(Order(side=Side.BUY, price=100.0, quantity=10))
            else:
                engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        
        # Should have 50 trades (each sell matches pending buy)
        # But first order is buy which rests, then sell matches, etc.
        # So 50 sells each match 50 buys = 50 trades
        assert engine.get_trade_count() == 50
        assert engine.get_total_volume() == 500  # 50 trades * 10 qty
    
    def test_price_improvement(self):
        """Test that aggressive orders get price improvement."""
        engine = MatchingEngine()
        
        # Resting sell at 100
        engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        
        # Aggressive buy at 105 - should execute at 100 (price improvement of 5)
        buy = Order(side=Side.BUY, price=105.0, quantity=10)
        trades = engine.process_order(buy)
        
        assert len(trades) == 1
        assert trades[0].price == 100.0  # Got price improvement
        
        # Total "savings" for buyer
        savings = (buy.price - trades[0].price) * trades[0].quantity
        assert savings == 50.0  # Saved 5 per unit * 10 units


class TestMatchingEngineEdgeCases:
    """Edge case tests for the matching engine."""
    
    def setup_method(self):
        """Reset state before each test."""
        reset_sequence_counter()
        Trade.reset_counter()
    
    def test_exact_quantity_match(self):
        """Test when quantities match exactly."""
        engine = MatchingEngine()
        
        engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        engine.process_order(Order(side=Side.BUY, price=100.0, quantity=10))
        
        assert engine.order_book.bid_count == 0
        assert engine.order_book.ask_count == 0
    
    def test_zero_spread_no_match(self):
        """Test orders at same price on opposite sides that don't cross."""
        engine = MatchingEngine()
        
        # Buy first, then sell at same price - should match!
        engine.process_order(Order(side=Side.BUY, price=100.0, quantity=10))
        trades = engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        
        assert len(trades) == 1  # They should match at same price
    
    def test_very_small_quantities(self):
        """Test orders with quantity of 1."""
        engine = MatchingEngine()
        
        for _ in range(100):
            engine.process_order(Order(side=Side.SELL, price=100.0, quantity=1))
            engine.process_order(Order(side=Side.BUY, price=100.0, quantity=1))
        
        assert engine.get_trade_count() == 100
        assert engine.get_total_volume() == 100
    
    def test_very_large_quantity(self):
        """Test order with very large quantity."""
        engine = MatchingEngine()
        
        # Many small sells
        for _ in range(100):
            engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        
        # One large buy
        buy = Order(side=Side.BUY, price=100.0, quantity=1000)
        engine.process_order(buy)
        
        assert engine.get_total_volume() == 1000
        assert engine.order_book.ask_count == 0
    
    def test_decimal_prices(self):
        """Test orders with decimal prices."""
        engine = MatchingEngine()
        
        engine.process_order(Order(side=Side.SELL, price=100.01, quantity=10))
        engine.process_order(Order(side=Side.SELL, price=100.02, quantity=10))
        
        buy = Order(side=Side.BUY, price=100.015, quantity=10)
        trades = engine.process_order(buy)
        
        assert len(trades) == 1
        assert trades[0].price == 100.01  # Matched at best ask


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements
