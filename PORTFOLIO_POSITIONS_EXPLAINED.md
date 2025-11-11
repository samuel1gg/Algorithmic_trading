# Portfolio Positions Explained

## What is a Portfolio Position?

A **portfolio position** represents **an investment you currently own** in a specific asset (like a stock).

Think of it like this:
- **Position** = "I own 100 shares of Apple stock"
- **Portfolio** = "All my positions combined" (Apple, Microsoft, Google, etc.)

## Simple Analogy

Imagine you're shopping:

```
Portfolio = Your Shopping Cart
Position = One item in your cart

Shopping Cart (Portfolio):
├── 5 apples (Position: AAPL, quantity: 5)
├── 3 bananas (Position: MSFT, quantity: 3)
└── 2 oranges (Position: GOOGL, quantity: 2)
```

## Real Trading Example

### Starting State
- **Cash**: $100,000
- **Positions**: None (empty portfolio)

### After Buying Apple Stock
- **Cash**: $95,000 (spent $5,000)
- **Positions**:
  - **AAPL**: 50 shares @ $100/share = $5,000
    - Average price: $100
    - Current price: $100
    - Unrealized P&L: $0 (no gain/loss yet)

### After Price Goes Up
- **Cash**: $95,000 (unchanged)
- **Positions**:
  - **AAPL**: 50 shares @ $100/share
    - Average price: $100 (what you paid)
    - Current price: $110 (current market price)
    - Unrealized P&L: +$500 (50 shares × $10 gain = $500 profit)
    - **You haven't sold yet, so it's "unrealized" (paper profit)**

### After Selling
- **Cash**: $105,500 (got $5,500 from sale)
- **Positions**: None (sold all shares)
- **Realized P&L**: +$500 (actual profit from the trade)

## Position Components

### In Our Codebase

```python
class Position:
    symbol: str              # Stock symbol (e.g., "AAPL")
    quantity: float          # How many shares you own (e.g., 50.0)
    average_price: float     # Average price you paid (e.g., $100.00)
    current_price: float     # Current market price (e.g., $110.00)
    unrealized_pnl: float    # Paper profit/loss (e.g., +$500.00)
    realized_pnl: float      # Actual profit/loss from closed positions
```

### Example Position Object

```python
Position(
    symbol="AAPL",
    quantity=50.0,           # You own 50 shares
    average_price=100.0,     # You bought at $100/share
    current_price=110.0,      # Current price is $110/share
    unrealized_pnl=500.0,     # 50 × ($110 - $100) = $500 profit
    realized_pnl=0.0          # No closed positions yet
)
```

## Key Concepts

### 1. Unrealized P&L (Paper Profit/Loss)

**Unrealized** = You haven't sold yet, so it's just on paper

```
Unrealized P&L = (Current Price - Average Price) × Quantity

Example:
- Bought 50 shares @ $100 = $5,000
- Current price: $110
- Unrealized P&L = ($110 - $100) × 50 = $500 profit
```

**Important**: This is NOT real money until you sell!

### 2. Realized P&L (Actual Profit/Loss)

**Realized** = You sold the position, so it's actual money

```
Realized P&L = (Sell Price - Average Price) × Quantity Sold

Example:
- Bought 50 shares @ $100
- Sold 50 shares @ $110
- Realized P&L = ($110 - $100) × 50 = $500 profit (actual money)
```

### 3. Average Price

When you buy the same stock multiple times, you calculate the average:

```
First buy:  20 shares @ $100 = $2,000
Second buy: 30 shares @ $110 = $3,300
Total:      50 shares for $5,300

Average Price = $5,300 / 50 = $106/share
```

### 4. Current Price

The current market price (what you could sell for right now)

## Portfolio vs Position

### Portfolio = All Your Investments Combined

```python
Portfolio {
    total_value: $105,000      # Cash + All positions
    cash: $95,000              # Available cash
    positions: [
        Position("AAPL", 50 shares, $500 profit),
        Position("MSFT", 30 shares, -$200 loss),
        Position("GOOGL", 20 shares, $300 profit)
    ],
    total_pnl: $600            # Sum of all P&L
}
```

### Position = One Investment

```python
Position {
    symbol: "AAPL",
    quantity: 50,
    average_price: $100,
    current_price: $110,
    unrealized_pnl: $500
}
```

## How Positions Work in Our System

### 1. Creating a Position (Buying)

```python
# You buy 50 shares of AAPL at $100
Order: BUY 50 AAPL @ $100

Result:
- Cash decreases: $100,000 → $95,000
- Position created:
  Position(
      symbol="AAPL",
      quantity=50,
      average_price=100.0,
      current_price=100.0,
      unrealized_pnl=0.0
  )
```

### 2. Adding to a Position (Buying More)

```python
# You already own 50 shares @ $100
# You buy 30 more shares @ $110

Old position: 50 shares @ $100 = $5,000
New purchase: 30 shares @ $110 = $3,300
Total:        80 shares for $8,300

New average price = $8,300 / 80 = $103.75

Updated Position:
  Position(
      symbol="AAPL",
      quantity=80,              # Increased
      average_price=103.75,     # New average
      current_price=110.0,
      unrealized_pnl=500.0      # (110 - 103.75) × 80
  )
```

### 3. Reducing a Position (Selling Some)

```python
# You own 80 shares @ $103.75 average
# You sell 30 shares @ $110

Result:
- Cash increases: $95,000 → $98,300
- Position updated:
  Position(
      symbol="AAPL",
      quantity=50,              # Reduced from 80
      average_price=103.75,     # Stays the same
      current_price=110.0,
      unrealized_pnl=312.5,     # (110 - 103.75) × 50
      realized_pnl=187.5        # (110 - 103.75) × 30 (sold)
  )
```

### 4. Closing a Position (Selling All)

```python
# You own 50 shares @ $103.75
# You sell all 50 shares @ $110

Result:
- Cash increases: $98,300 → $103,800
- Position deleted (quantity = 0)
- Realized P&L: $312.50 (from this position)
```

## Database Representation

### Positions Table

```sql
CREATE TABLE positions (
    id UUID PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,    -- "AAPL"
    quantity FLOAT NOT NULL,                -- 50.0 shares
    average_price FLOAT NOT NULL,           -- $100.00
    current_price FLOAT NOT NULL,           -- $110.00
    unrealized_pnl FLOAT DEFAULT 0.0,      -- $500.00
    realized_pnl FLOAT DEFAULT 0.0,         -- $0.00
    last_updated TIMESTAMP
);
```

### Example Database Record

```
symbol: "AAPL"
quantity: 50.0
average_price: 100.0
current_price: 110.0
unrealized_pnl: 500.0
realized_pnl: 0.0
```

## Real-World Example

### Day 1: Buy Apple
```
Action: BUY 100 AAPL @ $150
Cash: $100,000 → $85,000
Position: AAPL 100 shares @ $150
```

### Day 2: Price Goes Up
```
Market price: $155
Position: AAPL 100 shares @ $150
Unrealized P&L: (155 - 150) × 100 = +$500
Portfolio value: $85,000 + (100 × $155) = $100,500
```

### Day 3: Buy More
```
Action: BUY 50 AAPL @ $160
Cash: $85,000 → $77,000
Position: AAPL 150 shares @ $153.33 average
  (100 @ $150 + 50 @ $160 = $23,000 / 150 = $153.33)
```

### Day 4: Sell Some
```
Action: SELL 75 AAPL @ $165
Cash: $77,000 → $89,375
Position: AAPL 75 shares @ $153.33 average
Realized P&L: (165 - 153.33) × 75 = +$875.25
Unrealized P&L: (165 - 153.33) × 75 = +$875.25
```

## In Our Trading System

### How Positions Are Created

```python
# In trading-service/main.py
def execute_order(order):
    if order.side == "BUY":
        position = db.query(Position).filter(
            Position.symbol == order.symbol
        ).first()
        
        if position:
            # Add to existing position
            total_cost = (position.quantity * position.average_price) + \
                        (order.quantity * execution_price)
            total_quantity = position.quantity + order.quantity
            position.average_price = total_cost / total_quantity
            position.quantity = total_quantity
        else:
            # Create new position
            position = Position(
                symbol=order.symbol,
                quantity=order.quantity,
                average_price=execution_price,
                current_price=execution_price
            )
            db.add(position)
```

### How Positions Are Updated

```python
# Position prices updated every minute
def update_positions_prices():
    positions = db.query(Position).all()
    for position in positions:
        # Get latest market price
        market_data = get_latest_price(position.symbol)
        position.current_price = market_data.close
        
        # Calculate unrealized P&L
        position.unrealized_pnl = (
            market_data.close - position.average_price
        ) * position.quantity
```

## Summary

**Position** = One investment you currently own
- Symbol (e.g., "AAPL")
- Quantity (how many shares)
- Average price (what you paid)
- Current price (market value)
- Unrealized P&L (paper profit/loss)
- Realized P&L (actual profit/loss from sales)

**Portfolio** = All your positions combined
- Total value = Cash + Sum of all positions
- Total P&L = Sum of all unrealized + realized P&L

**Key Points**:
- Position = You own it right now
- Unrealized P&L = Paper profit (not sold yet)
- Realized P&L = Actual profit (from sales)
- Average price = Weighted average of all purchases
- Portfolio = All positions + cash

Think of it like a shopping cart:
- **Position** = One item in your cart
- **Portfolio** = Your entire cart + wallet

