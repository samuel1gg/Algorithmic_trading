"""Initialize database with schema, stored procedures, and triggers."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text
from shared.database import engine, Base
from database.models import (
    MarketDataPoint, TradingSignal, Anomaly, Order, 
    Position, Trade, Portfolio, Account
)
from shared.logger import setup_logger

logger = setup_logger(__name__)


def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully")


def create_stored_procedures():
    """Create stored procedures for complex operations."""
    logger.info("Creating stored procedures...")
    
    with engine.connect() as conn:
        # Stored procedure: Check available funds before order
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION check_available_funds(
                p_order_id UUID,
                p_symbol VARCHAR,
                p_side VARCHAR,
                p_quantity FLOAT,
                p_price FLOAT
            ) RETURNS BOOLEAN AS $$
            DECLARE
                v_cash FLOAT;
                v_required FLOAT;
                v_position_quantity FLOAT;
            BEGIN
                -- Get current cash
                SELECT cash INTO v_cash FROM account LIMIT 1;
                
                IF p_side = 'BUY' THEN
                    v_required := p_quantity * p_price;
                    IF v_cash < v_required THEN
                        RETURN FALSE;
                    END IF;
                ELSIF p_side = 'SELL' THEN
                    -- Check if we have the position
                    SELECT COALESCE(quantity, 0) INTO v_position_quantity 
                    FROM positions WHERE symbol = p_symbol;
                    
                    IF v_position_quantity < p_quantity THEN
                        RETURN FALSE;
                    END IF;
                END IF;
                
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        # Stored procedure: Update portfolio value
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_portfolio_value()
            RETURNS TRIGGER AS $$
            DECLARE
                v_total_value FLOAT;
                v_cash FLOAT;
                v_positions_value FLOAT;
            BEGIN
                -- Calculate positions value
                SELECT COALESCE(SUM(quantity * current_price), 0) INTO v_positions_value
                FROM positions;
                
                -- Get cash
                SELECT cash INTO v_cash FROM account LIMIT 1;
                
                -- Calculate total value
                v_total_value := v_cash + v_positions_value;
                
                -- Update account
                UPDATE account SET 
                    total_value = v_total_value,
                    last_updated = NOW();
                
                -- Insert portfolio snapshot
                INSERT INTO portfolio_snapshots (total_value, cash, total_pnl, total_return, timestamp)
                VALUES (
                    v_total_value,
                    v_cash,
                    v_total_value - 100000.0,  -- Assuming initial capital
                    (v_total_value - 100000.0) / 100000.0,
                    NOW()
                );
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        # Stored procedure: Calculate position PnL
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION calculate_position_pnl(
                p_symbol VARCHAR
            ) RETURNS VOID AS $$
            DECLARE
                v_position RECORD;
                v_unrealized_pnl FLOAT;
            BEGIN
                FOR v_position IN 
                    SELECT * FROM positions WHERE symbol = p_symbol
                LOOP
                    v_unrealized_pnl := (v_position.current_price - v_position.average_price) * v_position.quantity;
                    
                    UPDATE positions 
                    SET unrealized_pnl = v_unrealized_pnl,
                        last_updated = NOW()
                    WHERE symbol = p_symbol;
                END LOOP;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        # Stored procedure: Get portfolio statistics
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION get_portfolio_stats(
                p_start_date TIMESTAMP,
                p_end_date TIMESTAMP
            ) RETURNS TABLE (
                total_return FLOAT,
                sharpe_ratio FLOAT,
                max_drawdown FLOAT,
                volatility FLOAT
            ) AS $$
            DECLARE
                v_returns FLOAT[];
                v_mean_return FLOAT;
                v_std_return FLOAT;
                v_sharpe FLOAT;
                v_max_dd FLOAT;
                v_peak FLOAT;
                v_current FLOAT;
            BEGIN
                -- Get returns
                SELECT ARRAY_AGG(total_return ORDER BY timestamp) INTO v_returns
                FROM portfolio_snapshots
                WHERE timestamp BETWEEN p_start_date AND p_end_date;
                
                -- Calculate statistics
                SELECT AVG(r), STDDEV(r) INTO v_mean_return, v_std_return
                FROM unnest(v_returns) AS r;
                
                -- Sharpe ratio (assuming 252 trading days, risk-free rate = 0)
                IF v_std_return > 0 THEN
                    v_sharpe := (v_mean_return * 252) / (v_std_return * SQRT(252));
                ELSE
                    v_sharpe := 0;
                END IF;
                
                -- Max drawdown
                v_peak := 0;
                v_max_dd := 0;
                FOR i IN 1..array_length(v_returns, 1) LOOP
                    v_current := v_returns[i];
                    IF v_current > v_peak THEN
                        v_peak := v_current;
                    END IF;
                    IF (v_peak - v_current) > v_max_dd THEN
                        v_max_dd := v_peak - v_current;
                    END IF;
                END LOOP;
                
                RETURN QUERY SELECT 
                    v_returns[array_length(v_returns, 1)] as total_return,
                    v_sharpe as sharpe_ratio,
                    v_max_dd as max_drawdown,
                    v_std_return * SQRT(252) as volatility;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        conn.commit()
        logger.info("Stored procedures created successfully")


def create_triggers():
    """Create database triggers."""
    logger.info("Creating database triggers...")
    
    with engine.connect() as conn:
        # Trigger: Update portfolio value when position changes
        conn.execute(text("""
            DROP TRIGGER IF EXISTS trigger_update_portfolio_value ON positions;
            CREATE TRIGGER trigger_update_portfolio_value
            AFTER INSERT OR UPDATE OR DELETE ON positions
            FOR EACH ROW
            EXECUTE FUNCTION update_portfolio_value();
        """))
        
        # Trigger: Validate order before insertion
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION validate_order()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Check if order has valid quantity
                IF NEW.quantity <= 0 THEN
                    RAISE EXCEPTION 'Order quantity must be positive';
                END IF;
                
                -- Check if limit order has price
                IF NEW.order_type = 'LIMIT' AND NEW.price IS NULL THEN
                    RAISE EXCEPTION 'Limit order must have a price';
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        conn.execute(text("""
            DROP TRIGGER IF EXISTS trigger_validate_order ON orders;
            CREATE TRIGGER trigger_validate_order
            BEFORE INSERT ON orders
            FOR EACH ROW
            EXECUTE FUNCTION validate_order();
        """))
        
        conn.commit()
        logger.info("Triggers created successfully")


def initialize_account():
    """Initialize trading account with initial capital."""
    logger.info("Initializing trading account...")
    
    from shared.config import settings
    
    with engine.connect() as conn:
        # Check if account exists
        result = conn.execute(text("SELECT COUNT(*) FROM account"))
        count = result.scalar()
        
        if count == 0:
            conn.execute(text(f"""
                INSERT INTO account (cash, total_value)
                VALUES ({settings.initial_capital}, {settings.initial_capital})
            """))
            conn.commit()
            logger.info(f"Account initialized with ${settings.initial_capital}")
        else:
            logger.info("Account already exists")


def init_database():
    """Initialize the entire database."""
    logger.info("Initializing database...")
    try:
        create_tables()
        create_stored_procedures()
        create_triggers()
        initialize_account()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    init_database()

