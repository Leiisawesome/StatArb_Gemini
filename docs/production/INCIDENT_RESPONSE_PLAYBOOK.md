# Incident Response Playbook

**System:** StatArb_Gemini Trading System  
**Purpose:** Guide for responding to production incidents  
**Last Updated:** October 8, 2025

---

## Incident Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| **P0 - Critical** | System down, trading halted, data loss | Immediate (<5 min) | System crash, database failure |
| **P1 - High** | Major functionality impaired | <15 minutes | Broker connection loss, high error rate |
| **P2 - Medium** | Degraded performance, partial functionality | <1 hour | Slow queries, cache failure |
| **P3 - Low** | Minor issues, no immediate impact | <4 hours | Logging errors, monitoring gaps |

---

## General Incident Response Process

### 1. Detect & Alert (0-2 minutes)
- Incident detected via monitoring alert or manual report
- Alert channels: Slack, PagerDuty, Email, SMS
- Acknowledge alert immediately

### 2. Assess & Communicate (2-5 minutes)
- Determine severity level
- Notify stakeholders based on severity
- Create incident channel/war room
- Assign incident commander

### 3. Mitigate & Stabilize (5-30 minutes)
- Stop the bleeding (halt trading if necessary)
- Apply immediate fix or workaround
- Verify mitigation successful
- Monitor for recurrence

### 4. Investigate & Resolve (30 min - hours)
- Root cause analysis
- Implement permanent fix
- Test fix thoroughly
- Deploy fix to production

### 5. Document & Learn (post-incident)
- Write incident report
- Conduct post-mortem meeting
- Identify action items
- Update runbooks
- Update monitoring/alerts

---

## P0 - Critical Incidents

### Incident: System Crash / Application Not Responding

**Symptoms:**
- Health check failing
- No response to API requests
- All services down

**Immediate Actions:**
1. **Verify the issue** (30 seconds)
   ```bash
   curl http://production-server/health
   ssh production-server
   ps aux | grep python
   ```

2. **Check if trading active** (1 minute)
   - Query broker for open orders
   - Check for open positions
   - **CRITICAL:** Determine if positions need emergency exit

3. **Attempt restart** (2 minutes)
   ```bash
   cd /opt/statarb_gemini
   source ai_integration_env/bin/activate
   systemctl restart statarb-gemini
   # OR
   supervisorctl restart statarb-gemini
   ```

4. **Verify restart** (1 minute)
   ```bash
   curl http://production-server/health
   tail -f /var/log/statarb/application.log
   ```

5. **If restart fails:**
   - Check logs: `tail -100 /var/log/statarb/application.log`
   - Check disk space: `df -h`
   - Check memory: `free -h`
   - Check database: `psql -c "SELECT 1"`
   - Escalate to P1 and continue investigation

**Rollback Decision:**
- If restart fails after 2 attempts → Rollback to previous version
- If positions at risk → Emergency liquidation first, then fix

---

### Incident: Database Failure / Data Corruption

**Symptoms:**
- Database connection errors
- Data inconsistencies
- Position tracking errors

**Immediate Actions:**
1. **Halt trading immediately** (30 seconds)
   ```bash
   curl -X POST http://production-server/api/emergency-halt
   # OR kill application if API unavailable
   ```

2. **Assess database state** (2 minutes)
   ```bash
   psql -U statarb -h db-server -c "SELECT version()"
   psql -U statarb -h db-server -c "SELECT COUNT(*) FROM positions"
   psql -U statarb -h db-server -c "SELECT COUNT(*) FROM orders"
   ```

3. **Check for corruption** (3 minutes)
   ```bash
   # Run integrity checks
   psql -U statarb -h db-server -c "VACUUM ANALYZE"
   # Check replication lag (if applicable)
   psql -U statarb -h db-server -c "SELECT * FROM pg_stat_replication"
   ```

4. **Restore from backup if necessary** (10-30 minutes)
   ```bash
   # Stop application
   systemctl stop statarb-gemini
   
   # Restore from latest backup
   pg_restore -U statarb -h db-server -d statarb_prod /backups/latest.dump
   
   # Verify data integrity
   psql -U statarb -h db-server -f /opt/statarb/scripts/verify_data.sql
   ```

5. **Reconcile positions with broker** (10-20 minutes)
   - Query broker for actual positions
   - Compare with restored database
   - Manual reconciliation if differences found

**Do NOT restart trading until:**
- Database fully operational
- Data integrity verified
- Positions reconciled
- Risk manager approval obtained

---

### Incident: Broker Connection Lost (All Brokers)

**Symptoms:**
- Cannot send orders
- Not receiving market data
- Connection timeout errors

**Immediate Actions:**
1. **Verify the issue** (1 minute)
   ```bash
   # Check network connectivity
   ping broker-api.com
   curl -I https://broker-api.com/health
   
   # Check application logs
   tail -50 /var/log/statarb/broker.log | grep -i error
   ```

2. **Assess current positions** (2 minutes)
   - Query database for open positions
   - Determine risk exposure
   - **CRITICAL:** If large exposure, attempt emergency liquidation via broker website/API

3. **Check broker status** (2 minutes)
   - Visit broker status page
   - Check Twitter/status channels
   - Contact broker support if available

4. **Attempt reconnection** (5 minutes)
   ```bash
   # Restart broker connection manager
   curl -X POST http://production-server/api/broker/reconnect
   
   # OR restart full application
   systemctl restart statarb-gemini
   ```

5. **If connection cannot be restored:**
   - Switch to manual trading mode
   - Monitor positions via broker portal
   - Prepare manual intervention if necessary
   - Set up manual alerts for position changes

**Communication:**
- Notify risk manager immediately
- Update stakeholders every 15 minutes
- Document all actions taken

---

## P1 - High Severity Incidents

### Incident: High Error Rate (>1%)

**Symptoms:**
- Order rejection rate elevated
- Error alerts firing
- Failed executions

**Investigation Steps:**
1. **Check error types** (2 minutes)
   ```bash
   tail -1000 /var/log/statarb/application.log | grep ERROR | sort | uniq -c | sort -rn
   ```

2. **Identify pattern** (5 minutes)
   - Specific symbol causing errors?
   - Specific order type failing?
   - Time-based pattern?
   - Broker-specific?

3. **Common causes:**
   - Insufficient buying power → Check account balances
   - Position limits exceeded → Review risk limits
   - Market closed → Check trading hours
   - Symbol halted → Check market status
   - API rate limits → Review request rate

4. **Mitigation:**
   ```python
   # If specific symbol causing issues
   curl -X POST http://production-server/api/strategy/disable \
     -d '{"symbol": "PROBLEMATIC_SYMBOL"}'
   
   # If risk limits issue
   curl -X POST http://production-server/api/risk/update-limits \
     -d '{"max_position_size": 1000}'
   ```

**Resolution:**
- Fix root cause
- Re-enable affected strategies
- Monitor for 30 minutes
- Update alerts if false positive

---

### Incident: Memory Leak Detected

**Symptoms:**
- Memory usage continuously increasing
- System slowdown over time
- Eventually: OOM killer or crash

**Investigation Steps:**
1. **Confirm memory leak** (5 minutes)
   ```bash
   # Check current memory usage
   free -h
   ps aux --sort=-%mem | head -10
   
   # Check memory trend
   sar -r 1 60  # Monitor for 1 minute
   ```

2. **Get memory profile** (10 minutes)
   ```python
   # If pympler installed
   from pympler import tracker
   tr = tracker.SummaryTracker()
   # ... let system run ...
   tr.print_diff()
   ```

3. **Identify leak source** (15-30 minutes)
   - Check for unclosed connections
   - Check for unreleased resources
   - Check for growing caches
   - Check for circular references

4. **Immediate mitigation:**
   ```bash
   # If leak is slow, schedule restart
   systemctl restart statarb-gemini
   
   # Set up automated restart until fixed
   # Add to crontab: restart every 12 hours
   0 */12 * * * systemctl restart statarb-gemini
   ```

**Long-term fix:**
- Identify and fix leak in code
- Add memory monitoring
- Set up automated restarts as safety net
- Add memory usage alerts

---

### Incident: Extreme Latency (>1 second)

**Symptoms:**
- Slow order execution
- Market data delayed
- System unresponsive

**Investigation Steps:**
1. **Identify bottleneck** (5 minutes)
   ```bash
   # Check CPU usage
   top
   
   # Check I/O wait
   iostat -x 1 5
   
   # Check network latency
   ping -c 10 broker-api.com
   
   # Check database performance
   psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active'"
   ```

2. **Common causes:**
   - Database slow queries → Check `pg_stat_statements`
   - Network issues → Check ping times
   - CPU overload → Check top/htop
   - Disk I/O → Check iostat
   - Lock contention → Check database locks

3. **Quick wins:**
   ```bash
   # Kill long-running queries
   psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes'"
   
   # Clear cache if corrupted
   redis-cli FLUSHALL
   
   # Restart application
   systemctl restart statarb-gemini
   ```

4. **Monitor improvement:**
   ```bash
   # Watch latency metrics
   watch -n 1 'curl -s http://production-server/metrics | grep latency'
   ```

---

## P2 - Medium Severity Incidents

### Incident: Cache (Redis) Failure

**Symptoms:**
- Increased database load
- Slower response times
- Redis connection errors

**Response:**
1. **Verify system continues functioning** (2 minutes)
   - Check if application has cache fallback
   - Verify database can handle load
   - Monitor response times

2. **Investigate Redis issue** (5 minutes)
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Check Redis logs
   tail -100 /var/log/redis/redis.log
   
   # Check Redis memory
   redis-cli INFO memory
   ```

3. **Restart Redis if needed** (2 minutes)
   ```bash
   systemctl restart redis
   redis-cli ping
   ```

4. **Warm up cache** (5-10 minutes)
   ```bash
   # Run cache warmup script
   python /opt/statarb/scripts/warmup_cache.py
   ```

**Note:** This is P2 because system should continue functioning without cache, just slower.

---

### Incident: Monitoring/Alerting Down

**Symptoms:**
- No alerts being received
- Dashboards not updating
- Metrics gaps

**Response:**
1. **Verify production system is healthy** (2 minutes)
   ```bash
   # Direct health checks
   curl http://production-server/health
   ssh production-server "ps aux | grep python"
   ```

2. **Check monitoring system** (5 minutes)
   ```bash
   # Prometheus
   systemctl status prometheus
   curl http://prometheus-server:9090/-/healthy
   
   # Grafana
   systemctl status grafana
   curl http://grafana-server:3000/api/health
   ```

3. **Restart monitoring if needed** (5 minutes)
   ```bash
   systemctl restart prometheus
   systemctl restart grafana
   ```

4. **Verify alerts resume** (10 minutes)
   - Check alert channels
   - Send test alert
   - Verify dashboards updating

---

## P3 - Low Severity Incidents

### Incident: Log Rotation Failure / Disk Space

**Symptoms:**
- Logs not rotating
- Disk space warnings
- Cannot write logs

**Response:**
1. **Check disk space** (1 minute)
   ```bash
   df -h
   du -sh /var/log/* | sort -h
   ```

2. **Free up space immediately** (5 minutes)
   ```bash
   # Compress old logs
   gzip /var/log/statarb/*.log.1
   
   # Delete old compressed logs
   find /var/log/statarb -name "*.gz" -mtime +30 -delete
   
   # Clear temp files
   rm -rf /tmp/*
   ```

3. **Fix log rotation** (10 minutes)
   ```bash
   # Test logrotate config
   logrotate -d /etc/logrotate.d/statarb
   
   # Force rotation
   logrotate -f /etc/logrotate.d/statarb
   ```

4. **Set up better monitoring:**
   - Add disk space alerts at 75%
   - Increase log rotation frequency
   - Reduce log retention period

---

## Emergency Procedures

### Emergency: Halt All Trading Immediately

**When to use:**
- Critical system malfunction
- Data corruption detected
- Unauthorized access suspected
- Regulatory requirement

**Procedure:**
1. **Stop application** (30 seconds)
   ```bash
   curl -X POST http://production-server/api/emergency-halt
   # OR
   systemctl stop statarb-gemini
   ```

2. **Cancel all open orders** (2 minutes)
   ```bash
   python /opt/statarb/scripts/cancel_all_orders.py
   ```

3. **Document positions** (5 minutes)
   ```bash
   python /opt/statarb/scripts/export_positions.py > positions_$(date +%Y%m%d_%H%M%S).csv
   ```

4. **Notify stakeholders** (immediate)
   - Send alert to all channels
   - Explain reason for halt
   - Provide ETA for resolution (or "unknown")

5. **Determine next steps:**
   - Emergency liquidation needed?
   - Wait for market close?
   - Manual position management?

---

### Emergency: Liquidate All Positions

**When to use:**
- System cannot be restored quickly
- Risk exposure too high
- Regulatory requirement
- Business decision

**Procedure:**
1. **Assess positions** (2 minutes)
   ```bash
   python /opt/statarb/scripts/export_positions.py
   # Review current positions and exposure
   ```

2. **Calculate liquidation plan** (5 minutes)
   - Prioritize largest/riskiest positions
   - Check market conditions
   - Estimate market impact
   - Get approvals

3. **Execute liquidation** (10-30 minutes)
   ```bash
   # Automated liquidation
   python /opt/statarb/scripts/emergency_liquidation.py --confirm
   
   # OR manual via broker platform
   # Place market orders to close all positions
   ```

4. **Verify liquidation** (5 minutes)
   ```bash
   # Check broker positions
   python /opt/statarb/scripts/check_broker_positions.py
   
   # Should show all positions flat
   ```

5. **Document everything:**
   - Time of liquidation
   - Positions closed
   - Prices achieved
   - P&L impact
   - Reason for liquidation

---

## Communication Templates

### Template: Critical Incident Alert

```
🚨 P0 CRITICAL INCIDENT - StatArb_Gemini

Status: ONGOING
Severity: P0 - Critical
Impact: Trading halted / System down
Start Time: [TIMESTAMP]

Issue: [Brief description]

Current Actions:
- [Action 1]
- [Action 2]

ETA to Resolution: [TIME] (or "Investigating")

Incident Commander: [NAME]
Updates: Every 15 minutes

Next Update: [TIME]
```

### Template: Resolution Notice

```
✅ INCIDENT RESOLVED - StatArb_Gemini

Status: RESOLVED
Severity: [P0/P1/P2/P3]
Duration: [START] to [END] ([DURATION])

Issue: [Brief description]

Root Cause: [Explanation]

Resolution: [What was done]

Impact: [What was affected]

Prevention: [Steps taken to prevent recurrence]

Post-Mortem: Scheduled for [DATE/TIME]
```

---

## Post-Incident Review

After every P0/P1 incident:

1. **Schedule post-mortem** (within 48 hours)
2. **Collect data:**
   - Timeline of events
   - Actions taken
   - Root cause
   - Impact assessment
   - Response effectiveness

3. **Conduct blameless post-mortem:**
   - What happened?
   - Why did it happen?
   - How did we respond?
   - What worked well?
   - What could be improved?

4. **Create action items:**
   - Code fixes
   - Process improvements
   - Documentation updates
   - Monitoring enhancements
   - Training needs

5. **Track to completion:**
   - Assign owners
   - Set deadlines
   - Verify implementation
   - Close incident

---

## Contact Information

### On-Call Rotation
- **Current On-Call:** [Check PagerDuty]
- **Backup On-Call:** [Check PagerDuty]

### Escalation Path
1. On-Call Engineer → Resolve within SLA
2. Tech Lead → If on-call needs assistance
3. Engineering Manager → If critical/prolonged
4. CTO → If business-critical

### External Contacts
- **Broker Support:** [PHONE] / [EMAIL]
- **Database Admin:** [PHONE] / [EMAIL]
- **DevOps Team:** [PHONE] / [EMAIL]
- **Cloud Provider:** [SUPPORT URL]

---

**Document Version:** 1.0  
**Last Updated:** October 8, 2025  
**Next Review:** After each major incident
