#!/usr/bin/env python3
"""
Simple test runner that doesn't require pytest.
Uses Python's built-in unittest framework.

Run with: python run_tests.py
"""

import sys
import os
import unittest
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from order_book import Order, Trade, Side, OrderStatus, OrderBook, MatchingEngine
from order_book.order import reset_sequence_counter, create_buy_order, create_sell_order


class TestOrder(unittest.TestCase):
    """Test cases for the Order class."""
    
    def setUp(self):
        reset_sequence_counter()
        Trade.reset_counter()
    
    def test_create_buy_order(self):
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        self.assertEqual(order.side, Side.BUY)
        self.assertEqual(order.price, 100.0)
        self.assertEqual(order.quantity, 10)
        self.assertEqual(order.remaining_quantity, 10)
        self.assertEqual(order.status, OrderStatus.NEW)
        self.assertTrue(order.is_active)
    
    def test_create_sell_order(self):
        order = Order(side=Side.SELL, price=101.0, quantity=5)
        self.assertEqual(order.side, Side.SELL)
        self.assertEqual(order.price, 101.0)
        self.assertTrue(order.is_active)
    
    def test_fill_partial(self):
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        order.fill(3)
        self.assertEqual(order.remaining_quantity, 7)
        self.assertEqual(order.filled_quantity, 3)
        self.assertEqual(order.status, OrderStatus.PARTIAL)
        self.assertTrue(order.is_active)
    
    def test_fill_complete(self):
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        order.fill(10)
        self.assertEqual(order.remaining_quantity, 0)
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertFalse(order.is_active)
    
    def test_buy_order_price_priority(self):
        high_price = Order(side=Side.BUY, price=101.0, quantity=10)
        low_price = Order(side=Side.BUY, price=100.0, quantity=10)
        self.assertTrue(high_price < low_price)  # Higher price is "better"
    
    def test_sell_order_price_priority(self):
        high_price = Order(side=Side.SELL, price=101.0, quantity=10)
        low_price = Order(side=Side.SELL, price=100.0, quantity=10)
        self.assertTrue(low_price < high_price)  # Lower price is "better"


class TestOrderBook(unittest.TestCase):
    """Test cases for the OrderBook class."""
    
    def setUp(self):
        reset_sequence_counter()
        Trade.reset_counter()
        self.book = OrderBook()
    
    def test_empty_book(self):
        self.assertIsNone(self.book.get_best_bid())
        self.assertIsNone(self.book.get_best_ask())
        self.assertEqual(self.book.bid_count, 0)
        self.assertEqual(self.book.ask_count, 0)
    
    def test_best_bid_is_highest_price(self):
        self.book.add_order(Order(side=Side.BUY, price=99.0, quantity=10))
        self.book.add_order(Order(side=Side.BUY, price=101.0, quantity=10))
        self.book.add_order(Order(side=Side.BUY, price=100.0, quantity=10))
        self.assertEqual(self.book.get_best_bid().price, 101.0)
    
    def test_best_ask_is_lowest_price(self):
        self.book.add_order(Order(side=Side.SELL, price=102.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=100.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=101.0, quantity=10))
        self.assertEqual(self.book.get_best_ask().price, 100.0)
    
    def test_time_priority(self):
        order1 = Order(side=Side.BUY, price=100.0, quantity=10, order_id="FIRST")
        order2 = Order(side=Side.BUY, price=100.0, quantity=10, order_id="SECOND")
        self.book.add_order(order1)
        self.book.add_order(order2)
        self.assertEqual(self.book.get_best_bid().order_id, "FIRST")
    
    def test_spread(self):
        self.book.add_order(Order(side=Side.BUY, price=99.0, quantity=10))
        self.book.add_order(Order(side=Side.SELL, price=101.0, quantity=10))
        self.assertEqual(self.book.spread, 2.0)
    
    def test_heap_property_many_orders(self):
        random.seed(42)
        prices = [random.uniform(95, 105) for _ in range(100)]
        for price in prices:
            self.book.add_order(Order(side=Side.BUY, price=price, quantity=10))
        
        extracted = []
        while self.book.get_best_bid():
            extracted.append(self.book.pop_best_bid().price)
        
        self.assertEqual(extracted, sorted(extracted, reverse=True))


class TestMatchingEngine(unittest.TestCase):
    """Test cases for the MatchingEngine class."""
    
    def setUp(self):
        reset_sequence_counter()
        Trade.reset_counter()
        self.engine = MatchingEngine()
    
    def test_no_match_empty_book(self):
        order = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(order)
        self.assertEqual(len(trades), 0)
        self.assertEqual(self.engine.order_book.bid_count, 1)
    
    def test_basic_match(self):
        sell = Order(side=Side.SELL, price=100.0, quantity=10)
        self.engine.process_order(sell)
        
        buy = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 10)
    
    def test_no_match_when_prices_dont_cross(self):
        sell = Order(side=Side.SELL, price=101.0, quantity=10)
        self.engine.process_order(sell)
        
        buy = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        self.assertEqual(len(trades), 0)
    
    def test_trade_at_resting_price(self):
        sell = Order(side=Side.SELL, price=100.0, quantity=10)
        self.engine.process_order(sell)
        
        buy = Order(side=Side.BUY, price=105.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        self.assertEqual(trades[0].price, 100.0)  # Resting price
    
    def test_partial_fill(self):
        sell = Order(side=Side.SELL, price=100.0, quantity=5)
        self.engine.process_order(sell)
        
        buy = Order(side=Side.BUY, price=100.0, quantity=10)
        trades = self.engine.process_order(buy)
        
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 5)
        self.assertEqual(buy.remaining_quantity, 5)
    
    def test_price_priority(self):
        self.engine.process_order(Order(side=Side.SELL, price=102.0, quantity=10, order_id="EXPENSIVE"))
        self.engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10, order_id="CHEAP"))
        
        buy = Order(side=Side.BUY, price=102.0, quantity=5)
        trades = self.engine.process_order(buy)
        
        self.assertEqual(trades[0].sell_order_id, "CHEAP")
    
    def test_100_random_orders(self):
        """
        Test matching engine with 100 random orders.
        Validates all trades are mathematically correct.
        """
        random.seed(42)
        
        for _ in range(100):
            side = random.choice([Side.BUY, Side.SELL])
            price = round(random.gauss(100, 2), 2)
            quantity = random.randint(1, 20)
            
            order = Order(side=side, price=price, quantity=quantity)
            self.engine.process_order(order)
        
        trades = self.engine.get_trades()
        
        # Validate each trade
        for trade in trades:
            buy_order = self.engine.get_order(trade.buy_order_id)
            sell_order = self.engine.get_order(trade.sell_order_id)
            
            # Buy price >= trade price
            self.assertGreaterEqual(buy_order.price, trade.price)
            
            # Sell price <= trade price
            self.assertLessEqual(sell_order.price, trade.price)
            
            # Positive quantity
            self.assertGreater(trade.quantity, 0)
        
        # No crossing orders remain
        best_bid = self.engine.order_book.get_best_bid()
        best_ask = self.engine.order_book.get_best_ask()
        
        if best_bid and best_ask:
            self.assertLess(best_bid.price, best_ask.price)
        
        print(f"\n✅ 100 Random Orders Test: {len(trades)} trades validated")
    
    def test_vwap(self):
        self.engine.process_order(Order(side=Side.SELL, price=100.0, quantity=10))
        self.engine.process_order(Order(side=Side.SELL, price=101.0, quantity=5))
        self.engine.process_order(Order(side=Side.BUY, price=101.0, quantity=15))
        
        expected_vwap = (10 * 100.0 + 5 * 101.0) / 15
        self.assertAlmostEqual(self.engine.get_vwap(), expected_vwap, places=4)


def run_all_tests():
    """Run all test suites and print summary."""
    print("=" * 60)
    print("   LIMIT ORDER BOOK - TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOrder))
    suite.addTests(loader.loadTestsFromTestCase(TestOrderBook))
    suite.addTests(loader.loadTestsFromTestCase(TestMatchingEngine))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("   ✅ ALL TESTS PASSED!")
    else:
        print("   ❌ SOME TESTS FAILED")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
