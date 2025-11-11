# Learning Guide: Understanding the Codebase

## Codebase Statistics

- **21 Python files** (~2,640 lines of code)
- **29 total files** (including configs, docs, Dockerfiles)
- **4 microservices**
- **8 database tables** with stored procedures and triggers
- **Multiple technologies**: FastAPI, Kafka, PostgreSQL, TensorFlow, Docker

## Time Estimates by Skill Level

### 🟢 Beginner (New to Python/Web Development)
**Total Time: 4-6 weeks (part-time) or 2-3 weeks (full-time)**

**Breakdown:**
- **Week 1-2**: Python fundamentals, FastAPI basics, REST APIs
- **Week 2-3**: Database concepts, SQLAlchemy, PostgreSQL
- **Week 3-4**: Docker basics, microservices concepts
- **Week 4-5**: Kafka basics, message queues
- **Week 5-6**: ML basics (LSTM, scikit-learn), trading concepts

**Focus Areas:**
1. Start with `shared/models.py` - understand data structures
2. Read `services/data-ingestion/main.py` - simplest service
3. Study `shared/database.py` - database connections
4. Review `services/trading-service/main.py` - business logic
5. Explore ML service last (most complex)

### 🟡 Intermediate (Knows Python, some web dev)
**Total Time: 2-3 weeks (part-time) or 1-2 weeks (full-time)**

**Breakdown:**
- **Week 1**: Architecture overview, service interactions
- **Week 1-2**: Database schema, stored procedures, triggers
- **Week 2**: Kafka streaming, event-driven architecture
- **Week 2-3**: ML models, trading logic, risk management

**Focus Areas:**
1. Read `ARCHITECTURE.md` first for big picture
2. Trace data flow: data-ingestion → Kafka → ML → Trading
3. Study database stored procedures in `database/migrations/init_db.py`
4. Understand ML models in `services/ml-service/models.py`
5. Review risk management in `services/trading-service/main.py`

### 🟠 Advanced (Experienced developer, new to this stack)
**Total Time: 1 week (part-time) or 3-5 days (full-time)**

**Breakdown:**
- **Day 1**: Architecture and data flow
- **Day 2**: Database design and stored procedures
- **Day 3**: Kafka integration and event handling
- **Day 4**: ML models and trading algorithms
- **Day 5**: Deployment, monitoring, and optimization

**Focus Areas:**
1. Quick read of `ARCHITECTURE.md`
2. Deep dive into database stored procedures
3. Review Kafka consumer/producer patterns
4. Analyze ML model architecture
5. Study risk management and order execution logic

### 🔴 Expert (Knows all technologies)
**Total Time: 2-3 days**

**Focus Areas:**
1. Architecture patterns and design decisions
2. Database optimization and query performance
3. ML model tuning and feature engineering
4. Scalability and production considerations

## Recommended Learning Path

### Phase 1: Foundation (Days 1-3)
**Goal**: Understand the overall architecture

1. **Read Documentation** (2-3 hours)
   - `README.md` - Overview
   - `ARCHITECTURE.md` - System design
   - `QUICKSTART.md` - How it works

2. **Explore Project Structure** (1 hour)
   ```bash
   tree -L 3  # or use your IDE's file explorer
   ```

3. **Understand Data Models** (2 hours)
   - `shared/models.py` - All data structures
   - `database/models.py` - Database schema

4. **Deploy and Run** (1-2 hours)
   ```bash
   ./scripts/init.sh
   # Explore APIs at http://localhost:8000/docs
   ```

### Phase 2: Data Flow (Days 4-6)
**Goal**: Trace how data moves through the system

1. **Data Ingestion Service** (3-4 hours)
   - `services/data-ingestion/main.py`
   - How data is collected and stored
   - Kafka producer usage

2. **Kafka Integration** (2-3 hours)
   - `shared/kafka_client.py`
   - Topics and message flow
   - Consumer groups

3. **ML Service** (4-5 hours)
   - `services/ml-service/main.py`
   - `services/ml-service/models.py`
   - How predictions are generated
   - Anomaly detection logic

4. **Trading Service** (4-5 hours)
   - `services/trading-service/main.py`
   - Order execution flow
   - Risk management

### Phase 3: Database Deep Dive (Days 7-9)
**Goal**: Understand database operations

1. **Schema Design** (2 hours)
   - `database/models.py` - All tables
   - Relationships and indexes

2. **Stored Procedures** (3-4 hours)
   - `database/migrations/init_db.py`
   - `check_available_funds()`
   - `update_portfolio_value()`
   - `calculate_position_pnl()`
   - `get_portfolio_stats()`

3. **Triggers** (1-2 hours)
   - `trigger_update_portfolio_value`
   - `trigger_validate_order`

4. **Query Patterns** (2 hours)
   - Time-series queries
   - Transaction management
   - ACID properties

### Phase 4: Advanced Concepts (Days 10-12)
**Goal**: Master complex features

1. **ML Models** (4-5 hours)
   - LSTM architecture
   - Feature engineering
   - Model training pipeline
   - Anomaly detection algorithm

2. **Risk Management** (2-3 hours)
   - Position sizing
   - Stop loss/take profit
   - Portfolio limits
   - Cash management

3. **Backtesting Engine** (3-4 hours)
   - `services/backtesting-service/main.py`
   - Strategy simulation
   - Performance metrics

4. **Monitoring** (1-2 hours)
   - Prometheus metrics
   - Grafana dashboards
   - Logging patterns

### Phase 5: Production Readiness (Days 13-14)
**Goal**: Understand deployment and operations

1. **Docker Setup** (2 hours)
   - `docker-compose.yml`
   - Service dependencies
   - Volume management

2. **Configuration** (1 hour)
   - `shared/config.py`
   - Environment variables
   - Service configuration

3. **Deployment** (2 hours)
   - `DEPLOYMENT.md`
   - Scaling considerations
   - Production best practices

## Key Files to Study (Priority Order)

### 🔴 Critical (Must Understand)
1. `shared/models.py` - Data structures
2. `shared/config.py` - Configuration
3. `services/trading-service/main.py` - Core business logic
4. `database/migrations/init_db.py` - Database setup
5. `docker-compose.yml` - System architecture

### 🟡 Important (Should Understand)
6. `services/ml-service/models.py` - ML models
7. `services/ml-service/main.py` - ML service logic
8. `shared/kafka_client.py` - Message queue
9. `services/data-ingestion/main.py` - Data collection
10. `database/models.py` - Database schema

### 🟢 Helpful (Nice to Understand)
11. `services/backtesting-service/main.py` - Backtesting
12. `shared/database.py` - Database connections
13. `shared/logger.py` - Logging setup
14. `monitoring/prometheus.yml` - Metrics
15. `scripts/init.sh` - Deployment automation

## Learning Tips

### 1. Start Small
- Don't try to understand everything at once
- Focus on one service at a time
- Use the API docs to see what each service does

### 2. Run and Experiment
```bash
# Start the system
./scripts/init.sh

# Make API calls
curl http://localhost:8000/portfolio
curl http://localhost:8000/positions

# Check logs
docker-compose logs -f trading-service
```

### 3. Use Debugging Tools
- Set breakpoints in your IDE
- Use `print()` statements (or logger)
- Check database directly: `docker-compose exec postgres psql -U algo_trader algo_trading`

### 4. Trace Data Flow
1. Trigger data ingestion: `POST /ingest/AAPL`
2. Watch Kafka: Check if message appears
3. Check ML service: See if signal generated
4. Check trading service: See if order created
5. Check database: Query orders/positions

### 5. Read Code with Questions
- What does this function do?
- Why was it designed this way?
- What happens if this fails?
- How does this scale?

### 6. Modify and Test
- Change a parameter (e.g., `MAX_POSITION_SIZE`)
- Add logging to understand flow
- Create a simple test script
- Modify a stored procedure

## Common Questions & Answers

**Q: Where does trading logic live?**
A: `services/trading-service/main.py` - `execute_order()`, `check_risk_limits()`

**Q: How are ML predictions made?**
A: `services/ml-service/models.py` - `PricePredictor.predict()`

**Q: Where is portfolio value calculated?**
A: Database stored procedure `update_portfolio_value()` in `database/migrations/init_db.py`

**Q: How does data flow from ingestion to trading?**
A: Data Ingestion → Kafka → ML Service → Kafka → Trading Service

**Q: Where are risk limits enforced?**
A: `services/trading-service/main.py` - `check_risk_limits()`

## Practice Exercises

### Beginner
1. Add a new endpoint to get account balance
2. Add logging to order execution
3. Modify position size limit
4. Add a new symbol to data ingestion

### Intermediate
1. Add a new stored procedure for trade statistics
2. Implement a new trading strategy
3. Add a new ML feature
4. Create a new Grafana dashboard

### Advanced
1. Optimize database queries
2. Add caching layer (Redis)
3. Implement circuit breakers
4. Add distributed tracing

## Resources

### Documentation
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Kafka: https://kafka.apache.org/documentation/
- TensorFlow: https://www.tensorflow.org/learn

### Code Reading Tools
- Use IDE with "Go to Definition"
- Use grep to find usages: `grep -r "function_name"`
- Use database tools to explore schema
- Use API docs (Swagger UI) to understand endpoints

## Time Investment Summary

| Skill Level | Part-Time | Full-Time | Focus Areas |
|------------|-----------|-----------|------------|
| Beginner | 4-6 weeks | 2-3 weeks | Basics of each technology |
| Intermediate | 2-3 weeks | 1-2 weeks | Architecture & integration |
| Advanced | 1 week | 3-5 days | Deep dives & optimization |
| Expert | 2-3 days | 1-2 days | Design patterns & scaling |

**Remember**: Understanding comes from doing. Don't just read - run, modify, break, and fix!

