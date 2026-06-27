import os
import re
import json
import logging
from anthropic import Anthropic
from sqlalchemy import text
from app import db
from app.model.company import Company
from app.model.agentcompany import AgentCompany
from sqlalchemy import or_

logger = logging.getLogger(__name__)

client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

SCHEMA = """
PostgreSQL database schema (exact column names — use these precisely):

TABLE: companies
  id, company_name, registration_number, shortcode, compliance_status,
  total_float_balance, commission_balance, user_id, created_at

TABLE: agentcompanies  (each row = one till / agent company)
  id, company_id (FK → companies.id), user_id,
  company_name, organization_name,
  till_number,          -- the M-Pesa till number shown on portal
  short_code,           -- business short code (use this to join with transactions)
  business_short_code,  -- alternate short code used for scraping
  float_balance, commission_balance, commission_account_status,
  status, is_active_on_portal, fraud_risk_level,
  created_at, last_scraped_at

TABLE: transactions  (float and commission transactions)
  id, receipt_no, completion_time, initiation_time,
  transaction_status,   -- 'Completed', 'Failed', 'Pending'
  transaction_type,     -- 'float', 'commission', 'commission_clawback'
  paid_in, withdrawn, balance,
  business_shortcode,   -- matches agentcompanies.short_code (NOTE: no underscore before 'code')
  details, other_party_info, account_number,
  company_id (FK → companies.id),
  agent_id, created_at

  IMPORTANT JOIN: transactions → agentcompanies via:
    transactions.business_shortcode = agentcompanies.short_code

TABLE: agent_swaps
  id, agent_company_id (FK → agentcompanies.id),
  initiated_by, swap_date,
  float_balance_at_swap, commission_balance_at_swap,
  previous_agents (jsonb array), new_agents (jsonb array),
  notes, status, created_at

TABLE: useragents
  id, firstname, lastname, idnumber, phone_number, operator_role, user_id

TABLE: fraud_alerts
  id, user_id,
  fraud_type,      -- e.g. 'split_transaction', 'rollover_fraud', 'rapid_back_forth'
  account_phone, account_name,
  transaction_count, total_amount, fraud_score,
  risk_level,      -- 'HIGH', 'MEDIUM', 'LOW'
  receipt_nos, resolved, resolved_at, created_at
"""


def _ids_sql(ids: list) -> str:
    """Format a list of ints for SQL IN clause, e.g. (1,2,3) or (NULL)."""
    if not ids:
        return "(NULL)"
    return "(" + ",".join(str(int(i)) for i in ids) + ")"


def _get_user_scope(user_id):
    """Return (company_ids, ac_ids) the user can access."""
    companies = (
        Company.query
        .filter_by(user_id=user_id)
        .with_entities(Company.id)
        .all()
    )
    company_ids = [c.id for c in companies]

    if company_ids:
        acs = AgentCompany.query.filter(
            or_(
                AgentCompany.user_id == user_id,
                AgentCompany.company_id.in_(company_ids),
            )
        ).with_entities(AgentCompany.id).all()
    else:
        acs = AgentCompany.query.filter_by(user_id=user_id).with_entities(AgentCompany.id).all()

    ac_ids = [ac.id for ac in acs]
    return company_ids, ac_ids


def _run_sql(query: str, company_ids: list, ac_ids: list) -> dict:
    """Execute a read-only SQL query. Returns {"rows": [...]} or {"error": "..."}."""
    q = query.strip().rstrip(';')

    if not re.match(r'^\s*SELECT\b', q, re.IGNORECASE):
        return {"error": "Only SELECT queries are permitted."}

    for kw in ('DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'GRANT', 'EXEC'):
        if re.search(r'\b' + kw + r'\b', q, re.IGNORECASE):
            return {"error": f"Forbidden keyword detected: {kw}"}

    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(q))
            rows = [dict(r._mapping) for r in result]
            # Serialise decimals / dates
            for row in rows:
                for k, v in row.items():
                    if hasattr(v, 'isoformat'):
                        row[k] = v.isoformat()
                    elif hasattr(v, '__float__'):
                        row[k] = float(v)
            return {"rows": rows[:500], "total": len(rows)}
    except Exception as e:
        logger.warning(f"[CHAT SQL] Error: {e} | Query: {q[:200]}")
        return {"error": str(e)}


def chat(user_id, message: str, history: list) -> dict:
    """
    Multi-turn chat with Claude + SQL tool use.

    history: [{"role": "user"|"assistant", "content": str}]
    Returns {"reply": str, "data": list|None}
    """
    company_ids, ac_ids = _get_user_scope(user_id)

    system_prompt = f"""You are a smart data analyst assistant embedded in an M-Pesa agent management platform.
Your job is to help users understand their business data through natural language conversation.

{SCHEMA}

--- DATA ACCESS SCOPE ---
This user owns the following records (always filter to these IDs in every query):
  company IDs       : {company_ids}
  agent_company IDs : {ac_ids}

SQL rules:
- Always scope companies with:      WHERE id IN {_ids_sql(company_ids)}
- Always scope agentcompanies with: WHERE id IN {_ids_sql(ac_ids)}
- Always scope transactions with:   WHERE company_id IN {_ids_sql(company_ids)}
- Always scope agent_swaps with:    WHERE agent_company_id IN {_ids_sql(ac_ids)}
- Only generate SELECT statements
- Prefer readable column aliases
- Limit results to 100 rows unless the user asks for more
- Use PostgreSQL syntax (e.g. ILIKE, DATE_TRUNC, NOW(), INTERVAL)

When you need data, call the run_sql tool. After getting results, explain them in clear,
business-friendly language. Round monetary values to 2 decimal places in your answer.
If you have no data (empty scope), tell the user they have no companies onboarded yet."""

    tools = [
        {
            "name": "run_sql",
            "description": "Execute a PostgreSQL SELECT query and return the results as JSON.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A valid PostgreSQL SELECT query scoped to the user's IDs."
                    }
                },
                "required": ["query"]
            }
        }
    ]

    # Build messages from simplified text history + new user message
    messages = []
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    all_datasets = []  # {"label": str, "rows": list} — one entry per SQL call with results
    query_counter = [0]

    def _label_from_query(q: str, n: int) -> str:
        """Derive a short human-readable label from the SQL query text."""
        q_lower = q.lower()
        if 'fraud' in q_lower:
            return f"Fraud Alerts"
        if 'agent_swap' in q_lower or 'swap' in q_lower:
            return f"Agent Swaps"
        if 'transaction' in q_lower:
            return f"Transactions"
        if 'agentcompan' in q_lower:
            return f"Tills / Agent Companies"
        if 'compan' in q_lower:
            return f"Companies"
        if 'useragent' in q_lower:
            return f"User Agents"
        return f"Query {n}"

    # Agentic loop — Claude may call run_sql one or more times
    for _ in range(5):  # safety cap on tool-call rounds
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            break

        # Execute each tool call
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                raw_query = block.input.get("query", "")
                result = _run_sql(raw_query, company_ids, ac_ids)
                rows = result.get("rows", [])
                logger.info(f"[CHAT SQL] {raw_query[:120]} → {len(rows)} rows")
                if rows:
                    query_counter[0] += 1
                    label = _label_from_query(raw_query, query_counter[0])
                    # Merge into existing dataset with same label rather than duplicating
                    existing = next((d for d in all_datasets if d["label"] == label), None)
                    if existing:
                        existing["rows"].extend(rows)
                    else:
                        all_datasets.append({"label": label, "rows": rows})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    # Extract final text reply
    reply = " ".join(
        block.text for block in response.content if hasattr(block, "text")
    ).strip()
    return {
        "reply": reply or "I couldn't generate a response. Please try rephrasing your question.",
        "data": all_datasets if all_datasets else None,
    }
