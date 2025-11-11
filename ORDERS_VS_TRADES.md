# Orders vs Trades: Key Differences

## The Fundamental Difference

**Order** = A **request** to buy or sell (may or may not be executed)
**Trade** = An **actual execution** of a buy or sell (money changed hands)

Think of it like:
- **Order** = "I want to buy 100 shares of AAPL" (request)
- **Trade** = "I just bought 100 shares of AAPL at $150" (completed transaction)

## Database Schemas

### Orders Table

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,      -- Unique order identifier
    symbol VARCHAR(10) NOT NULL,               -- Stock symbol
    side VARCHAR(10) NOT NULL,                 -- BUY or SELL
    order_type VARCHAR(10) NOT NULL,            -- MARKET, LIMIT, or STOP
    quantity FLOAT NOT NULL,                    -- How many shares requested
    price FLOAT,                                -- Limit price (if limit order)
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, FILLED, CANCELLED, REJECTED
    filled_quantity FLOAT DEFAULT 0.0,          -- How many shares actually filled
    average_fill_price FLOAT,                   -- Average price if filled
    timestamp TIMESTAMP NOT NULL,               -- When order was created
    filled_at TIMESTAMP                         -- When order was executed (if filled)
);
```

**Key Characteristics**:
- Represents a **request/intent**
- Can have different **statuses** (PENDING, FILLED, CANCELLED, REJECTED)
- May or may not be executed
- Can be partially filled
- Has a **price** field for limit orders (desired price)

### Trades Table

```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    order_id UUID FOREIGN KEY,                  -- Links to the order
    symbol VARCHAR(10) NOT NULL,                -- Stock symbol
    side VARCHAR(10) NOT NULL,                  -- BUY or SELL
    quantity FLOAT NOT NULL,                    -- Shares actually traded
    price FLOAT NOT NULL,                       -- Actual execution price
    commission FLOAT DEFAULT 0.0,               -- Trading fees
    pnl FLOAT DEFAULT 0.0,                      -- Profit/loss from this trade
    timestamp TIMESTAMP NOT NULL,               -- When trade executed
    created_at TIMESTAMP
);
```

**Key Characteristics**:
- Represents an **actual execution**
- Always has a **price** (the actual price it was executed at)
- Always has a **quantity** (the actual shares traded)
- Has **commission** (trading fees)
- Has **PnL** (profit/loss calculation)
- Links back to the original order via `order_id`

## Lifecycle: Order → Trade

### Step 1: Order Created (PENDING)

```python
Order {
    order_id: "ORD-12345",
    symbol: "AAPL",
    side: "BUY",
    order_type: "MARKET",
    quantity: 100.0,
    price: None,                    # Market order, no price specified
    status: "PENDING",              # Not executed yet
    filled_quantity: 0.0,           # Nothing filled yet
    average_fill_price: None,        # No execution yet
    timestamp: "2024-01-15 10:00:00",
    filled_at: None                 # Not filled yet
}
```

**Trade**: None (order not executed yet)

### Step 2: Order Executed (FILLED)

```python
Order {
    order_id: "ORD-12345",
    symbol: "AAPL",
    side: "BUY",
    order_type: "MARKET",
    quantity: 100.0,
    price: None,
    status: "FILLED",               # ✅ Executed!
    filled_quantity: 100.0,          # ✅ All 100 shares filled
    average_fill_price: 150.25,      # ✅ Executed at $150.25
    timestamp: "2024-01-15 10:00:00",
    filled_at: "2024-01-15 10:00:05" # ✅ Filled 5 seconds later
}
```

**Trade Created**:
```python
Trade {
    id: "TRD-67890",
    order_id: "ORD-12345",          # Links back to order
    symbol: "AAPL",
    side: "BUY",
    quantity: 100.0,                 # Actual shares traded
    price: 150.25,                   # Actual execution price
    commission: 15.03,               # 0.1% commission = $15.03
    pnl: 0.0,                        # No P&L yet (just bought)
    timestamp: "2024-01-15 10:00:05" # When trade happened
}
```

## Key Differences Summary

| Aspect | Orders | Trades |
|--------|--------|--------|
| **Purpose** | Request/intent | Actual execution |
| **Status** | PENDING, FILLED, CANCELLED, REJECTED | Always executed (exists = executed) |
| **Price** | Optional (for limit orders) | Always present (actual execution price) |
| **Quantity** | Requested quantity | Actual quantity executed |
| **Partial Fills** | Can be partially filled | Each trade is a complete execution |
| **Commission** | No | Yes (trading fees) |
| **PnL** | No | Yes (profit/loss) |
| **When Created** | When order is placed | When order is executed |
| **Can Be Cancelled** | Yes (if PENDING) | No (already happened) |

## Real-World Example

### Scenario: You Want to Buy Apple Stock

#### 1. Create Order (Request)

```python
# You place an order
POST /orders
{
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 100
}

# Order created in database
Order {
    order_id: "ORD-001",
    symbol: "AAPL",
    side: "BUY",
    quantity: 100.0,
    status: "PENDING",        # Waiting to be executed
    filled_quantity: 0.0
}
```

**Trades Table**: Empty (no trade yet)

#### 2. Order Executed

```python
# Trading service executes the order
# Gets current market price: $150.25
# Executes the buy

# Order updated
Order {
    order_id: "ORD-001",
    status: "FILLED",          # ✅ Now filled
    filled_quantity: 100.0,    # ✅ All shares filled
    average_fill_price: 150.25 # ✅ Execution price
}

# Trade created
Trade {
    order_id: "ORD-001",       # Links to order
    symbol: "AAPL",
    side: "BUY",
    quantity: 100.0,
    price: 150.25,             # Actual price paid
    commission: 15.03,         # Fees
    pnl: 0.0                   # No P&L (just bought)
}
```

#### 3. Later: You Sell

```python
# You place a sell order
POST /orders
{
    "symbol": "AAPL",
    "side": "SELL",
    "order_type": "MARKET",
    "quantity": 100
}

# Order created
Order {
    order_id: "ORD-002",
    symbol: "AAPL",
    side: "SELL",
    quantity: 100.0,
    status: "PENDING"
}

# Order executed at $155.00
Order {
    order_id: "ORD-002",
    status: "FILLED",
    filled_quantity: 100.0,
    average_fill_price: 155.00
}

# Trade created
Trade {
    order_id: "ORD-002",
    symbol: "AAPL",
    side: "SELL",
    quantity: 100.0,
    price: 155.00,             # Sold at $155
    commission: 15.50,         # Fees
    pnl: 469.47                # Profit: (155 - 150.25) × 100 - fees
}
```

## Partial Fills

### Order Can Be Partially Filled

```python
# You place order for 100 shares
Order {
    order_id: "ORD-003",
    quantity: 100.0,
    status: "PARTIALLY_FILLED",  # Not fully executed
    filled_quantity: 50.0,        # Only 50 shares filled so far
    average_fill_price: 150.00
}

# First trade (50 shares)
Trade {
    order_id: "ORD-003",
    quantity: 50.0,              # First 50 shares
    price: 150.00
}

# Later: Remaining 50 shares filled
# Second trade created
Trade {
    order_id: "ORD-003",
    quantity: 50.0,               # Remaining 50 shares
    price: 150.50                # Different price!
}

# Order updated
Order {
    order_id: "ORD-003",
    status: "FILLED",            # Now fully filled
    filled_quantity: 100.0,      # All 100 shares
    average_fill_price: 150.25   # Average of both trades
}
```

**Key Point**: One order can result in **multiple trades** if partially filled!

## Limit Orders

### Limit Order Example

```python
# You place a limit order: "Buy 100 AAPL, but only if price is $150 or less"
Order {
    order_id: "ORD-004",
    symbol: "AAPL",
    side: "BUY",
    order_type: "LIMIT",
    quantity: 100.0,
    price: 150.00,               # Maximum price you'll pay
    status: "PENDING"             # Waiting for price to drop
}

# If market price is $151:
# Order stays PENDING (price too high)
# No trade created

# If market price drops to $149:
# Order executed
Order {
    status: "FILLED",
    filled_quantity: 100.0,
    average_fill_price: 149.00   # Actually got it for $149!
}

Trade {
    order_id: "ORD-004",
    price: 149.00                 # Actual execution price
}
```

## In Our Codebase

### Order Creation

```python
# In trading-service/main.py
def create_order(order_data):
    # Create order record
    order = Order(
        order_id=str(uuid.uuid4()),
        symbol=order_data.symbol,
        side=order_data.side,
        order_type=order_data.order_type,
        quantity=order_data.quantity,
        price=order_data.price,  # Optional for market orders
        status="PENDING"
    )
    db.add(order)
    db.commit()
    
    # If market order, execute immediately
    if order.order_type == "MARKET":
        execute_order(order)
```

### Order Execution (Creates Trade)

```python
def execute_order(order):
    # Get current market price
    market_price = get_current_price(order.symbol)
    
    # Update order
    order.status = "FILLED"
    order.filled_quantity = order.quantity
    order.average_fill_price = market_price
    order.filled_at = datetime.utcnow()
    
    # Create trade record
    trade = Trade(
        order_id=order.id,              # Link to order
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        price=market_price,             # Actual execution price
        commission=calculate_commission(order.quantity, market_price),
        pnl=0.0                          # Will be calculated later
    )
    db.add(trade)
    db.commit()
```

## Why Both Tables?

### Orders Table Tracks:
- ✅ **Intent**: What you wanted to do
- ✅ **Status**: Whether it was executed, cancelled, or rejected
- ✅ **Request Details**: Original quantity, limit price
- ✅ **Execution Summary**: How much was filled, at what average price

### Trades Table Tracks:
- ✅ **Actual Executions**: What really happened
- ✅ **Exact Prices**: Actual execution prices (may differ from order price)
- ✅ **Fees**: Commission paid
- ✅ **PnL**: Profit/loss from each trade
- ✅ **History**: Complete record of all actual transactions

## Query Examples

### Get All Pending Orders
```sql
SELECT * FROM orders WHERE status = 'PENDING';
```

### Get All Executed Trades
```sql
SELECT * FROM trades ORDER BY timestamp DESC;
```

### Get Order and Its Trade
```sql
SELECT o.*, t.*
FROM orders o
LEFT JOIN trades t ON t.order_id = o.id
WHERE o.order_id = 'ORD-001';
```

### Calculate Total Trading Volume
```sql
SELECT SUM(quantity * price) as total_volume
FROM trades
WHERE timestamp >= '2024-01-01';
```

## Summary

| Concept | Orders | Trades |
|---------|--------|--------|
| **What it is** | Request to buy/sell | Actual buy/sell execution |
| **When created** | When you place order | When order is executed |
| **Status** | PENDING → FILLED/CANCELLED | Always executed (exists = happened) |
| **Price** | Desired price (limit) | Actual execution price |
| **Multiple per order?** | One order | Can have multiple (partial fills) |
| **Purpose** | Track requests/intent | Track actual transactions |

**Analogy**:
- **Order** = Restaurant order ("I'd like a pizza")
- **Trade** = The actual pizza delivered to your table

**In Trading**:
- **Order** = "I want to buy 100 shares"
- **Trade** = "I just bought 100 shares at $150.25"

Both are important:
- **Orders** show your trading strategy and intent
- **Trades** show what actually happened and your performance

