from app import db
from app.model.agent_swap import AgentSwap
from app.model.agentcompany import AgentCompany
from app.model.agent_accounts import AgentAccount
from app.model.agent_account_balances import AgentAccountBalance
from app.model.useragent import UserAgent, user_agent_companies
from datetime import datetime, timedelta, timezone

EAT = timezone(timedelta(hours=3))


def _to_eat(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(EAT).isoformat()
from decimal import Decimal
from sqlalchemy import func


class SwapService:

    def _get_balance_for_account_type(self, agent_company_id, account_type):
        accounts = AgentAccount.query.filter_by(
            agent_company_id=agent_company_id
        ).all()

        # Match using case-insensitive contains, same as frontend
        account = None
        for acc in accounts:
            if acc.account_type and account_type.lower() in acc.account_type.lower():
                account = acc
                break

        if not account:
            return Decimal('0.00')

        latest = (
            AgentAccountBalance.query
            .filter_by(agent_account_id=account.id)
            .order_by(AgentAccountBalance.snapshot_at.desc())
            .first()
        )
        if latest and latest.current_balance is not None:
            return latest.current_balance
        return Decimal('0.00')

    def _serialize_agents(self, user_agents):
        return [
            {
                'id': ua.id,
                'name': f"{ua.firstname} {ua.lastname}",
                'idnumber': ua.idnumber,
                'phone_number': ua.phone_number
            }
            for ua in user_agents
        ]

    def initiate_swap(self, agent_company_id, new_agent_ids, notes, user_id, outgoing_agent_ids=None):
        try:
            agent_company = AgentCompany.query.get(agent_company_id)
            if not agent_company:
                return None, "Agent company not found"

            # Snapshot current balances
            float_balance = self._get_balance_for_account_type(agent_company_id, 'FLOAT')
            commission_balance = self._get_balance_for_account_type(agent_company_id, 'COMMISSION')

            current_agents = list(agent_company.user_agents)

            # Determine which agents are going out vs staying
            if outgoing_agent_ids:
                outgoing_set = set(outgoing_agent_ids)
                outgoing_agents = [a for a in current_agents if a.id in outgoing_set]
                staying_agents = [a for a in current_agents if a.id not in outgoing_set]
            else:
                outgoing_agents = current_agents
                staying_agents = []

            previous_agents_data = self._serialize_agents(outgoing_agents)

            # Validate new agents exist
            new_agents = UserAgent.query.filter(UserAgent.id.in_(new_agent_ids)).all()
            if len(new_agents) != len(new_agent_ids):
                return None, "One or more new agent IDs are invalid"
            new_agents_data = self._serialize_agents(new_agents)

            # Create swap record
            swap = AgentSwap(
                agent_company_id=agent_company_id,
                initiated_by=user_id,
                swap_date=datetime.utcnow(),
                float_balance_at_swap=float_balance,
                commission_balance_at_swap=commission_balance,
                previous_agents=previous_agents_data,
                new_agents=new_agents_data,
                notes=notes,
                status='completed'
            )
            db.session.add(swap)

            # Remove only the outgoing agents from the association table
            outgoing_ids_to_remove = [a.id for a in outgoing_agents]
            if outgoing_ids_to_remove:
                db.session.execute(
                    user_agent_companies.delete().where(
                        (user_agent_companies.c.agent_company_id == agent_company_id) &
                        (user_agent_companies.c.user_agent_id.in_(outgoing_ids_to_remove))
                    )
                )

            # Add new agents (skip any that are already staying on the till)
            staying_ids = {a.id for a in staying_agents}
            for agent in new_agents:
                if agent.id not in staying_ids:
                    db.session.execute(
                        user_agent_companies.insert().values(
                            user_agent_id=agent.id,
                            agent_company_id=agent_company_id,
                            created_at=datetime.utcnow()
                        )
                    )

            db.session.commit()
            return swap.to_dict(), None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    def revert_swap(self, swap_id, user_id):
        try:
            original_swap = AgentSwap.query.get(swap_id)
            if not original_swap:
                return None, "Swap not found"

            agent_company_id = original_swap.agent_company_id
            agent_company = AgentCompany.query.get(agent_company_id)
            if not agent_company:
                return None, "Agent company not found"

            # Restore previous agents on the company
            previous_agent_ids = [a['id'] for a in (original_swap.previous_agents or [])]
            previous_agents = UserAgent.query.filter(UserAgent.id.in_(previous_agent_ids)).all() if previous_agent_ids else []

            db.session.execute(
                user_agent_companies.delete().where(
                    user_agent_companies.c.agent_company_id == agent_company_id
                )
            )
            for agent in previous_agents:
                db.session.execute(
                    user_agent_companies.insert().values(
                        user_agent_id=agent.id,
                        agent_company_id=agent_company_id,
                        created_at=datetime.utcnow()
                    )
                )

            # Delete the swap record
            db.session.delete(original_swap)

            db.session.commit()
            return {'message': 'Swap reverted and deleted'}, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    def get_swaps_by_company(self, agent_company_id):
        try:
            swaps = (
                AgentSwap.query
                .filter_by(agent_company_id=agent_company_id)
                .order_by(AgentSwap.swap_date.desc())
                .all()
            )
            return [s.to_dict() for s in swaps], None
        except Exception as e:
            return None, str(e)

    def get_all_swaps(self, user_id, filters=None):
        try:
            filters = filters or {}

            # Get agent companies belonging to this user
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]

            if not company_ids:
                return [], None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))

            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                query = query.filter(AgentSwap.swap_date >= datetime.fromisoformat(filters['start_date']))
            if filters.get('end_date'):
                query = query.filter(AgentSwap.swap_date <= datetime.fromisoformat(filters['end_date']))

            swaps = query.order_by(AgentSwap.swap_date.desc()).all()
            return [s.to_dict() for s in swaps], None

        except Exception as e:
            return None, str(e)

    def get_swaps_grouped_by_company(self, user_id, filters=None):
        try:
            filters = filters or {}
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]

            if not company_ids:
                return [], None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))

            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                query = query.filter(AgentSwap.swap_date >= datetime.fromisoformat(filters['start_date']))
            if filters.get('end_date'):
                query = query.filter(AgentSwap.swap_date <= datetime.fromisoformat(filters['end_date']))

            swaps = query.order_by(AgentSwap.agent_company_id, AgentSwap.swap_date.desc()).all()

            # Group by company
            grouped = {}
            for swap in swaps:
                cid = swap.agent_company_id
                if cid not in grouped:
                    ac = swap.agent_company
                    grouped[cid] = {
                        'agent_company_id': cid,
                        'company_name': ac.company.company_name if ac and ac.company else None,
                        'till_name': (ac.company_name or ac.organization_name) if ac else None,
                        'till_number': ac.till_number if ac else None,
                        # kept for backward compatibility
                        'agent_company_name': (ac.company_name or ac.organization_name) if ac else None,
                        'total_swaps': 0,
                        'swaps': []
                    }
                grouped[cid]['total_swaps'] += 1
                grouped[cid]['swaps'].append(swap.to_dict())

            return list(grouped.values()), None

        except Exception as e:
            return None, str(e)

    def get_swaps_grouped_by_agent(self, user_id, filters=None):
        try:
            filters = filters or {}
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]
            if not company_ids:
                return [], None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))
            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                query = query.filter(AgentSwap.swap_date >= datetime.fromisoformat(filters['start_date']))
            if filters.get('end_date'):
                query = query.filter(AgentSwap.swap_date <= datetime.fromisoformat(filters['end_date']))

            swaps = query.order_by(AgentSwap.swap_date.desc()).all()

            # Build an agent-centric map keyed by a stable agent identifier
            agents: dict = {}

            def _agent_name(a):
                """Resolve name from agent JSON dict, trying all known field shapes."""
                if a.get("name"):
                    return a["name"]
                parts = [a.get("firstname", ""), a.get("middlename", ""), a.get("lastname", "")]
                joined = " ".join(p for p in parts if p).strip()
                return joined or a.get("idnumber") or a.get("identity_id") or "Unknown"

            for swap in swaps:
                ac = swap.agent_company
                till_name    = (ac.company_name or ac.organization_name) if ac else None
                company_name = ac.company.company_name if ac and ac.company else None
                is_scraper   = "Auto-detected" in (swap.notes or "")

                float_val      = "—" if is_scraper else str(swap.float_balance_at_swap or "0.00")
                commission_val = "—" if is_scraper else str(swap.commission_balance_at_swap or "0.00")

                prev_names    = [_agent_name(a) for a in (swap.previous_agents or [])]
                current_names = [_agent_name(a) for a in (swap.new_agents or [])]

                swap_row_base = {
                    "swap_id":            swap.id,
                    "swap_date":          _to_eat(swap.swap_date),
                    "till_name":          till_name,
                    "company_name":       company_name,
                    "float_at_swap":      float_val,
                    "commission_at_swap": commission_val,
                    "notes":              swap.notes,
                    "initiated_by":       swap.initiator.username if swap.initiator else None,
                    "previous_names":     prev_names,
                    "current_names":      current_names,
                }

                for agent_data, agent_status in [
                    (swap.previous_agents or [], "previous"),
                    (swap.new_agents      or [], "current"),
                ]:
                    for a in agent_data:
                        name = _agent_name(a)
                        key  = a.get("id") or a.get("identity_id") or name
                        if key not in agents:
                            agents[key] = {
                                "agent_id":     a.get("id"),
                                "agent_name":   name,
                                "idnumber":     a.get("idnumber"),
                                "phone_number": a.get("phone_number"),
                                "total_swaps":  0,
                                "swaps":        [],
                            }
                        elif not agents[key]["agent_name"] or agents[key]["agent_name"] == "Unknown":
                            agents[key]["agent_name"] = name
                        agents[key]["total_swaps"] += 1
                        agents[key]["swaps"].append({
                            **swap_row_base,
                            "agent_status": agent_status,
                        })

            return list(agents.values()), None

        except Exception as e:
            return None, str(e)

    def get_swaps_by_company_and_till(self, user_id, filters=None):
        """
        Three-level structure: Company → AgentCompany (till) → agents.
        Within each till:
          - current_agents : new_agents of the most-recent swap
          - previous_rows  : one entry per previous agent across all swaps
        """
        try:
            filters = filters or {}
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]
            if not company_ids:
                return [], None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))
            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                query = query.filter(AgentSwap.swap_date >= datetime.fromisoformat(filters['start_date']))
            if filters.get('end_date'):
                query = query.filter(AgentSwap.swap_date <= datetime.fromisoformat(filters['end_date']))

            swaps = query.order_by(AgentSwap.swap_date.desc()).all()

            def _prev_name(p):
                return (
                    p.get("name")
                    or " ".join(x for x in [p.get("firstname"), p.get("middlename"), p.get("lastname")] if x)
                    or p.get("idnumber") or "Unknown"
                )

            companies: dict = {}   # keyed by (company_id or ac_id)

            for swap in swaps:
                ac = swap.agent_company
                if not ac:          # orphaned swap — skip safely
                    continue

                parent    = ac.company   # may be None
                ac_id     = ac.id

                # ── Company-level grouping key & label ──────────────────────
                if parent:
                    cid          = f"co-{parent.id}"
                    company_name = parent.company_name or ac.company_name or ac.organization_name or "Unknown"
                else:
                    # No parent Company — group each till as its own company entry
                    cid          = f"ac-{ac_id}"
                    company_name = ac.company_name or ac.organization_name or f"Till {ac_id}"

                if cid not in companies:
                    companies[cid] = {
                        "company_id":   cid,
                        "company_name": company_name,
                        "tills":        {},
                    }

                # ── Till-level entry ────────────────────────────────────────
                if ac_id not in companies[cid]["tills"]:
                    till_label  = ac.company_name or ac.organization_name or f"Till {ac_id}"
                    short_code  = ac.short_code or ac.business_short_code or ""

                    # Current agents = those still linked via M2M (source of truth)
                    live_agents = [
                        {
                            "name":         f"{ua.firstname} {ua.lastname}".strip(),
                            "phone_number": ua.phone_number,
                            "idnumber":     ua.idnumber,
                            "role":         ua.operator_role,
                        }
                        for ua in ac.user_agents
                    ]

                    companies[cid]["tills"][ac_id] = {
                        "agent_company_id": ac_id,
                        "till_name":        till_label,
                        "short_code":       short_code,
                        "current_agents":   live_agents,
                        "previous_rows":    [],
                        "total_swaps":      0,
                    }

                till       = companies[cid]["tills"][ac_id]
                is_scraper = "Auto-detected" in (swap.notes or "")
                fv         = "—" if is_scraper else str(swap.float_balance_at_swap or "0.00")
                cv         = "—" if is_scraper else str(swap.commission_balance_at_swap or "0.00")

                for prev in (swap.previous_agents or []):
                    till["previous_rows"].append({
                        "swap_id":            swap.id,
                        "swap_date":          _to_eat(swap.swap_date),
                        "agent_name":         _prev_name(prev),
                        "agent_idnumber":     prev.get("idnumber"),
                        "agent_phone":        prev.get("phone_number"),
                        "current_agents":     swap.new_agents or [],
                        "float_at_swap":      fv,
                        "commission_at_swap": cv,
                        "notes":              swap.notes,
                        "initiated_by":       swap.initiator.username if swap.initiator else None,
                    })
                    till["total_swaps"] += 1

            result = []
            for cd in companies.values():
                tills = list(cd["tills"].values())
                result.append({
                    "company_id":   cd["company_id"],
                    "company_name": cd["company_name"],
                    "total_swaps":  sum(t["total_swaps"] for t in tills),
                    "tills":        tills,
                })

            return result, None

        except Exception as e:
            return None, str(e)

    def generate_swap_report(self, user_id, filters=None):
        try:
            filters = filters or {}
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]

            if not company_ids:
                return {'summary': {}, 'companies': []}, None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))

            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                start = datetime.fromisoformat(filters['start_date'])
                query = query.filter(AgentSwap.swap_date >= start)
            if filters.get('end_date'):
                end = datetime.fromisoformat(filters['end_date'])
                query = query.filter(AgentSwap.swap_date <= end)

            swaps = query.order_by(AgentSwap.swap_date.desc()).all()

            if not swaps:
                return {
                    'period': {
                        'start_date': filters.get('start_date'),
                        'end_date': filters.get('end_date')
                    },
                    'summary': {
                        'total_swaps': 0,
                        'companies_involved': 0,
                        'avg_float_at_swap': '0.00',
                        'avg_commission_at_swap': '0.00',
                        'total_float_at_swaps': '0.00',
                        'total_commission_at_swaps': '0.00',
                    },
                    'companies': []
                }, None

            total_float = sum(s.float_balance_at_swap or Decimal('0') for s in swaps)
            total_commission = sum(s.commission_balance_at_swap or Decimal('0') for s in swaps)
            total_swaps = len(swaps)
            unique_companies = len(set(s.agent_company_id for s in swaps))

            # Per-company breakdown
            company_stats = {}
            for swap in swaps:
                cid = swap.agent_company_id
                if cid not in company_stats:
                    ac = swap.agent_company
                    company_stats[cid] = {
                        'agent_company_id': cid,
                        'company_name': ac.company.company_name if ac and ac.company else None,
                        'till_name': (ac.company_name or ac.organization_name) if ac else None,
                        'till_number': ac.till_number if ac else None,
                        'swap_count': 0,
                        'total_float': Decimal('0'),
                        'total_commission': Decimal('0'),
                        'first_swap': swap.swap_date,
                        'last_swap': swap.swap_date,
                    }
                cs = company_stats[cid]
                cs['swap_count'] += 1
                cs['total_float'] += swap.float_balance_at_swap or Decimal('0')
                cs['total_commission'] += swap.commission_balance_at_swap or Decimal('0')
                if swap.swap_date < cs['first_swap']:
                    cs['first_swap'] = swap.swap_date
                if swap.swap_date > cs['last_swap']:
                    cs['last_swap'] = swap.swap_date

            companies_list = []
            for cs in company_stats.values():
                companies_list.append({
                    'agent_company_id': cs['agent_company_id'],
                    'company_name': cs['company_name'],
                    'till_name': cs['till_name'],
                    'till_number': cs['till_number'],
                    'swap_count': cs['swap_count'],
                    'avg_float_at_swap': str(round(cs['total_float'] / cs['swap_count'], 2)),
                    'avg_commission_at_swap': str(round(cs['total_commission'] / cs['swap_count'], 2)),
                    'total_float_at_swaps': str(cs['total_float']),
                    'total_commission_at_swaps': str(cs['total_commission']),
                    'first_swap': _to_eat(cs['first_swap']),
                    'last_swap': _to_eat(cs['last_swap']),
                })

            report = {
                'period': {
                    'start_date': filters.get('start_date'),
                    'end_date': filters.get('end_date')
                },
                'summary': {
                    'total_swaps': total_swaps,
                    'companies_involved': unique_companies,
                    'avg_float_at_swap': str(round(total_float / total_swaps, 2)),
                    'avg_commission_at_swap': str(round(total_commission / total_swaps, 2)),
                    'total_float_at_swaps': str(total_float),
                    'total_commission_at_swaps': str(total_commission),
                },
                'companies': companies_list
            }

            return report, None

        except Exception as e:
            return None, str(e)

    def export_swap_report(self, user_id, filters=None, format='csv'):
        import io
        import csv

        report, error = self.generate_swap_report(user_id, filters)
        if error:
            return None, error

        swaps_data, _ = self.get_all_swaps(user_id, filters)
        if not swaps_data:
            swaps_data = []

        if format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'Swap ID', 'Company', 'Till', 'Till Number', 'Swap Date',
                'Float Balance at Swap', 'Commission Balance at Swap',
                'Previous Agents', 'New Agents',
                'Initiated By', 'Notes', 'Status'
            ])
            for swap in swaps_data:
                prev_names = ', '.join(a.get('name', '') for a in (swap.get('previous_agents') or []))
                new_names = ', '.join(a.get('name', '') for a in (swap.get('new_agents') or []))
                writer.writerow([
                    swap['id'],
                    swap.get('company_name', ''),
                    swap.get('till_name', swap.get('agent_company_name', '')),
                    swap.get('till_number', ''),
                    swap.get('swap_date', ''),
                    swap.get('float_balance_at_swap', '0.00'),
                    swap.get('commission_balance_at_swap', '0.00'),
                    prev_names,
                    new_names,
                    swap.get('initiator_name', ''),
                    swap.get('notes', ''),
                    swap.get('status', ''),
                ])
            return output.getvalue(), None

        return None, f"Unsupported format: {format}"
