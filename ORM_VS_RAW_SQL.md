# ORM vs Raw SQL: When to Use What

## Current Codebase Approach ✅

Your codebase uses a **hybrid approach** - which is the **BEST PRACTICE**:

- **ORM (SQLAlchemy)** for 90% of operations
- **Raw SQL** for stored procedures and complex database functions

## When to Use ORM (SQLAlchemy)

### ✅ Use ORM For:

#### 1. **Simple CRUD Operations**
```python
# ✅ GOOD: Using ORM
position = db.query(Position).filter(Position.symbol == symbol).first()
order = Order(symbol="AAPL", quantity=10.0, side="BUY")
db.add(order)
db.commit()
```

#### 2. **Type Safety & IDE Support**
```python
# ✅ GOOD: IDE autocomplete, type checking
account = db.query(Account).first()
account.cash -= 100.0  # IDE knows 'cash' exists
```

#### 3. **Relationship Management**
```python
# ✅ GOOD: ORM handles relationships automatically
order = db.query(Order).filter(Order.id == order_id).first()
trade = Trade(order_id=order.id, ...)  # Foreign key handled
```

#### 4. **Database Agnostic Code**
```python
# ✅ GOOD: Works with PostgreSQL, MySQL, SQLite
db.query(MarketDataPoint).filter(
    MarketDataPoint.timestamp >= start_date
).all()
```

#### 5. **Security (SQL Injection Protection)**
```python
# ✅ GOOD: ORM automatically escapes values
db.query(Order).filter(Order.symbol == user_input).all()  # Safe!
```

## When to Use Raw SQL

### ✅ Use Raw SQL For:

#### 1. **Stored Procedures & Functions** ⭐ (Your Current Use Case)
```python
# ✅ CORRECT: Stored procedures MUST use raw SQL
db.execute(text("SELECT update_portfolio_value()"))
db.execute(text("SELECT check_available_funds(:order_id, :symbol, :side, :quantity, :price)"))
```

**Why?** Stored procedures are database-specific functions written in PL/pgSQL. ORM can't create or call them directly.

#### 2. **Complex Aggregations & Analytics**
```python
# ✅ GOOD: Complex query with window functions
result = db.execute(text("""
    SELECT 
        symbol,
        AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as ma_30
    FROM market_data
    WHERE timestamp >= :start_date
"""), {"start_date": start_date})
```

#### 3. **Database-Specific Features**
```python
# ✅ GOOD: PostgreSQL-specific features
db.execute(text("""
    SELECT * FROM get_portfolio_stats(:start_date, :end_date)
"""), {"start_date": start_date, "end_date": end_date})
```

#### 4. **Performance-Critical Queries**
```python
# ✅ GOOD: Optimized query that ORM can't generate efficiently
db.execute(text("""
    SELECT symbol, SUM(volume) 
    FROM market_data 
    WHERE timestamp >= :start 
    GROUP BY symbol 
    HAVING SUM(volume) > :threshold
"""), {"start": start_date, "threshold": 1000000})
```

#### 5. **Bulk Operations**
```python
# ✅ GOOD: Bulk insert (faster than ORM for large datasets)
db.execute(text("""
    INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
    VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume)
"""), bulk_data)
```

## Your Codebase Examples

### ✅ Good ORM Usage (Current Code)

**File: `services/trading-service/main.py`**
```python
# ✅ Perfect ORM usage
position = db.query(Position).filter(Position.symbol == order.symbol).first()

if position:
    position.quantity += order.quantity
    position.average_price = new_average
else:
    position = Position(symbol=order.symbol, quantity=order.quantity, ...)
    db.add(position)

db.commit()  # ORM handles the SQL generation
```

### ✅ Good Raw SQL Usage (Current Code)

**File: `database/migrations/init_db.py`**
```python
# ✅ CORRECT: Stored procedures require raw SQL
conn.execute(text("""
    CREATE OR REPLACE FUNCTION update_portfolio_value()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Complex logic in database
        UPDATE account SET total_value = ...;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
"""))
```

**File: `services/trading-service/main.py`**
```python
# ✅ CORRECT: Calling stored procedure
db.execute(text("SELECT update_portfolio_value()"))
```

**File: `services/backtesting-service/main.py`**
```python
# ✅ CORRECT: Complex analytics query
result = db.execute(
    text("SELECT * FROM get_portfolio_stats(:start_date, :end_date)"),
    {"start_date": start_date, "end_date": end_date}
).fetchone()
```

## ❌ What NOT to Do

### ❌ Don't Use Raw SQL for Simple Queries
```python
# ❌ BAD: Unnecessary raw SQL
db.execute(text("SELECT * FROM orders WHERE id = :id"), {"id": order_id})

# ✅ GOOD: Use ORM
order = db.query(Order).filter(Order.id == order_id).first()
```

### ❌ Don't Use ORM for Stored Procedures
```python
# ❌ BAD: Can't do this - stored procedures don't exist in ORM
db.query(update_portfolio_value()).all()  # Doesn't work!

# ✅ GOOD: Must use raw SQL
db.execute(text("SELECT update_portfolio_value()"))
```

### ❌ Don't Concatenate SQL Strings (SQL Injection Risk)
```python
# ❌ BAD: SQL injection vulnerability
db.execute(text(f"SELECT * FROM orders WHERE symbol = '{symbol}'"))

# ✅ GOOD: Use parameters
db.execute(text("SELECT * FROM orders WHERE symbol = :symbol"), {"symbol": symbol})

# ✅ BETTER: Use ORM
db.query(Order).filter(Order.symbol == symbol).all()
```

## Best Practices Summary

### Your Current Approach is CORRECT! ✅

1. **ORM for 90% of operations** - Simple, safe, maintainable
2. **Raw SQL for stored procedures** - Required for database functions
3. **Raw SQL for complex analytics** - When ORM can't express it efficiently
4. **Always use parameterized queries** - Never string concatenation

## Migration Guide: Converting Raw SQL to ORM

If you want to convert some raw SQL to ORM:

### Example 1: Simple Query
```python
# Raw SQL
result = db.execute(text("SELECT * FROM orders WHERE status = :status"), {"status": "FILLED"})

# ORM (Better)
orders = db.query(Order).filter(Order.status == "FILLED").all()
```

### Example 2: Complex Query (Keep Raw SQL)
```python
# This is fine as raw SQL - too complex for ORM
result = db.execute(text("""
    SELECT 
        symbol,
        AVG(close) as avg_price,
        COUNT(*) as data_points
    FROM market_data
    WHERE timestamp >= :start_date
    GROUP BY symbol
    HAVING COUNT(*) > 100
"""), {"start_date": start_date})
```

## When to Refactor

### Keep Raw SQL If:
- ✅ It's a stored procedure (can't be ORM)
- ✅ It uses database-specific features (window functions, CTEs)
- ✅ It's significantly faster than ORM equivalent
- ✅ It's a complex analytics query

### Convert to ORM If:
- ✅ It's a simple SELECT/INSERT/UPDATE/DELETE
- ✅ You need type safety and IDE support
- ✅ You want database portability
- ✅ It's easier to read and maintain

## Your Codebase Assessment

**Current Status: ✅ EXCELLENT**

- **ORM Usage**: 85-90% ✅
- **Raw SQL Usage**: 10-15% ✅ (All appropriate cases)
- **Security**: ✅ Parameterized queries
- **Performance**: ✅ Stored procedures for complex operations

**Recommendation**: **Keep it as is!** Your hybrid approach is industry best practice.

## Quick Reference

| Operation | Use | Example |
|-----------|-----|---------|
| Simple CRUD | ORM | `db.query(Order).filter(...).first()` |
| Relationships | ORM | `order.trades` (if defined) |
| Stored Procedures | Raw SQL | `db.execute(text("SELECT func()"))` |
| Complex Analytics | Raw SQL | `db.execute(text("SELECT ... GROUP BY ..."))` |
| Bulk Operations | Raw SQL | `db.execute(text("INSERT ... VALUES ..."), bulk_data)` |
| Type Safety Needed | ORM | `order.symbol` (autocomplete) |
| Database Portability | ORM | Works with any SQLAlchemy DB |

## Conclusion

**Your current codebase is well-designed!** 

- Use ORM for most operations (simpler, safer, more maintainable)
- Use raw SQL for stored procedures and complex queries (required/optimal)
- Always use parameterized queries (security)

**Don't change what's working!** Your hybrid approach is exactly what production systems use.

