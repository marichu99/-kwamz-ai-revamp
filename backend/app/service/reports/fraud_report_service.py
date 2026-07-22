import bisect
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from app.model.transaction import Transaction
from app.service.fraud_detector import FraudDetectionService
from app.service.date_service import DateService
import logging
import sys

logger = logging.getLogger(__name__)
if not logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', '%H:%M:%S'))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# Fixed thresholds — not bound to any DB config
HARDCODED_CONFIG = {
    'time_window_minutes': 5,
    'amount_variance': 0.1,
    'min_transactions_rollover': 3,
    'split_threshold': 3,
    'rapid_back_forth_threshold': 2,
    'high_risk_score': 50,
    'medium_risk_score': 30,
    'max_alerts_per_group': 999,
    'split_min_amount': 50.0,
    'split_max_amount': 150000.0,
    'split_total_amount_threshold': 1000.0,
    'daily_split_threshold': 3,
    'daily_time_window_hours': 24,
}

# Deposit-withdrawal recovery thresholds
DWR_MIN_DEPOSIT = 20000.0        # minimum deposit to flag
DWR_RECOVERY_PCT = 0.50          # withdrawal must be >= 50% of deposit
DWR_WINDOW_HOURS = 24            # look for withdrawals within 24 hrs of deposit

# Split transaction thresholds
SPLIT_MIN_ANCHOR = 1000.0        # minimum anchor deposit (KES)
SPLIT_WINDOW_MINUTES = 120       # 2-hour window after the anchor deposit
SPLIT_MIN_SUBSEQUENT = 3         # minimum number of follow-up withdrawals
SPLIT_MIN_COVERAGE = 0.70        # withdrawals must total >= 70% of deposit
SPLIT_MAX_COVERAGE = 1.50        # withdrawals must total <= 150% of deposit

# Rapid back-and-forth thresholds
RBF_WINDOW_MINUTES = 1           # time window in minutes
RBF_MIN_TRANSACTIONS = 3         # minimum transactions in that window

# High-frequency daily activity
HF_MIN_TRANSACTIONS = 5          # minimum transactions in a single day to flag

# Same-phone rapid same-direction (structuring)
STRUCT_WINDOW_MINUTES = 180      # 3-hour window
STRUCT_MIN_TRANSACTIONS = 3      # minimum same-direction transactions
STRUCT_MIN_TOTAL = 5000.0        # minimum combined amount (KES)

# Split deposit: one person's deposit split into several deposits in quick succession
SPLITDEP_MAX_GAP_MINUTES = 10    # max gap between consecutive deposits in a chain
SPLITDEP_MIN_COUNT = 3           # chains of 3+ deposits always qualify
SPLITDEP_MIN_TOTAL = 10000.0     # minimum combined amount for a 3+ chain (KES)
SINGLE_DEPOSIT_CAP = 250000.0    # platform's per-transaction deposit limit — a deposit at
                                  # or above this is a legitimate max-out, never split evidence
SPLITDEP_PAIR_MIN_TOTAL = SINGLE_DEPOSIT_CAP  # 2-deposit chains (both members already
                                  # sub-cap) only qualify once their combined total reaches
                                  # the cap — i.e. they were kept under the cap on purpose

# Continuous rapid activity: till kept busy with back-to-back transactions
CRA_MAX_GAP_MINUTES = 2          # max gap between consecutive transactions in a chain
CRA_MIN_DURATION_MINUTES = 60    # chain must run at least this long without a break

# Float cycling (till-level pass-through)
FLOAT_TOP_UP_REASONS = {
    'Organization Transfer from MMF Account to Float Account via STK',
    'Organization Transfer from MMF Account to Float Account via API',
    'Organization Transfer from MMF Account to Float Account via web',
    'Merchant Withdraw at Agent Till',
    'Merchant Withdraw at Agent Till with OD',
}
FLOAT_DRAIN_REASONS = {
    'Business Deposit of Funds via API',
    'Organization Transfer from Float Account to MMF Account via STK',
    'Agency Redistribution of Float Funds via web',
    'Business Withdrawal of Funds',
}
CYCLING_MIN_TOP_UP = 50000.0     # minimum single top-up to consider (KES)
CYCLING_DRAIN_PCT  = 0.50        # drain events must total >= 50 % of the top-up
CYCLING_WINDOW_MINUTES = 120     # top-up → drain must all land within this window


class FraudReportService:
    def __init__(self):
        self.date_service = DateService()

    def generate_report(self, start_date=None, end_date=None, date_range='custom', company_id=None, company_ids=None):
        start_dt, end_dt = self.date_service.calculate_date_range(date_range, start_date, end_date)
        logger.info(f"[FraudReport] Period: {start_dt} → {end_dt}  company_id={company_id}")

        transactions = self._fetch_transactions(start_dt, end_dt, company_id, company_ids)
        logger.info(f"[FraudReport] Fetched {len(transactions)} transactions from DB")
        if not transactions:
            logger.warning("[FraudReport] No transactions found — returning empty report")
            return self._empty_report(start_dt, end_dt)

        txn_dicts = self._to_dicts(transactions)

        detector = FraudDetectionService(config=HARDCODED_CONFIG)

        # Parse phone + name into each dict
        parsed_with_phone = 0
        for txn in txn_dicts:
            phone, name = detector._parse_other_party_info(txn.get('other_party_info', ''))
            txn['phone_number'] = phone
            txn['name'] = name
            if phone:
                parsed_with_phone += 1

        logger.info(f"[FraudReport] {parsed_with_phone}/{len(txn_dicts)} transactions have a parsed phone number")

        # Sample first 3 other_party_info values to check parsing
        for i, txn in enumerate(txn_dicts[:3]):
            logger.info(
                f"[FraudReport] Sample txn[{i}]: other_party_info={txn.get('other_party_info')!r} "
                f"→ phone={txn.get('phone_number')!r}  reason_type={txn.get('reason_type')!r}  "
                f"paid_in={txn.get('paid_in')}  withdrawn={txn.get('withdrawn')}"
            )

        split_results = self._detect_split_transactions(txn_dicts, detector)
        logger.info(f"[FraudReport] split_transactions findings: {len(split_results)}")

        rollover_results = detector.detect_rollover_fraud(txn_dicts)
        logger.info(f"[FraudReport] rollover_fraud findings: {len(rollover_results)}")

        # Use our own window-based rapid back-and-forth detector
        rapid_results = self._detect_rapid_back_forth_window(txn_dicts, detector)
        logger.info(f"[FraudReport] rapid_back_forth findings: {len(rapid_results)}")

        # Deposit-withdrawal recovery
        dwr_results = self._detect_deposit_withdrawal_recovery(txn_dicts, detector)
        logger.info(f"[FraudReport] deposit_withdrawal_recovery findings: {len(dwr_results)}")

        # High-frequency: same party, 5+ transactions in a single day
        hf_results = self._detect_high_frequency_daily(txn_dicts, detector)
        logger.info(f"[FraudReport] high_frequency_daily findings: {len(hf_results)}")

        # Structuring: same phone, same direction (all deposits or all withdrawals), rapid bursts
        struct_results = self._detect_same_phone_rapid_same_direction(txn_dicts, detector)
        logger.info(f"[FraudReport] structuring findings: {len(struct_results)}")

        # Float cycling: till-level pass-through (large top-up immediately drained)
        cycling_results = self._detect_float_cycling(txn_dicts, detector)
        logger.info(f"[FraudReport] float_cycling findings: {len(cycling_results)}")

        # Split deposit: same person splits one deposit into several rapid deposits
        splitdep_results = self._detect_split_deposits(txn_dicts, detector)
        logger.info(f"[FraudReport] split_deposit findings: {len(splitdep_results)}")

        # Continuous rapid activity: till running back-to-back txns for an hour+
        cra_results = self._detect_continuous_rapid_activity(txn_dicts, detector)
        logger.info(f"[FraudReport] continuous_rapid_activity findings: {len(cra_results)}")

        all_results = (split_results + rollover_results + rapid_results + dwr_results
                       + hf_results + struct_results + cycling_results
                       + splitdep_results + cra_results)
        logger.info(f"[FraudReport] Total findings: {len(all_results)}")

        # Assign risk levels
        for r in all_results:
            score = r.get('fraud_score', 0)
            if score >= HARDCODED_CONFIG['high_risk_score']:
                r['risk_level'] = 'HIGH'
            elif score >= HARDCODED_CONFIG['medium_risk_score']:
                r['risk_level'] = 'MEDIUM'
            else:
                r['risk_level'] = 'LOW'

        serialized = [self._serialize_result(r) for r in all_results]

        return {
            'period': f"{start_dt.strftime('%d %b %Y')} - {end_dt.strftime('%d %b %Y')}",
            'summary': {
                'total_transactions_analyzed': len(txn_dicts),
                'total_findings': len(all_results),
                'split_transactions': len(split_results),
                'rollover_fraud': len(rollover_results),
                'rapid_back_forth': len(rapid_results),
                'deposit_withdrawal_recovery': len(dwr_results),
                'high_frequency_daily': len(hf_results),
                'structuring': len(struct_results),
                'float_cycling': len(cycling_results),
                'split_deposit': len(splitdep_results),
                'continuous_rapid_activity': len(cra_results),
                'high_risk': sum(1 for r in all_results if r.get('risk_level') == 'HIGH'),
                'medium_risk': sum(1 for r in all_results if r.get('risk_level') == 'MEDIUM'),
                'low_risk': sum(1 for r in all_results if r.get('risk_level') == 'LOW'),
            },
            'findings': serialized,
        }

    # ------------------------------------------------------------------
    # Split Transactions (till-level, depositor-must-withdraw rule)
    #
    # Qualifying pattern:
    #   1. One large "Deposit at Agent Till" (anchor) — the depositor gets
    #      M-Pesa credit on their phone.
    #   2. Within 2 hours at the same till, 3+ "Customer Withdrawal" transactions
    #      whose total covers 70–150 % of the deposit.
    #   3. The DEPOSITOR'S own phone must appear among the withdrawers — they
    #      reclaim the majority of the cash themselves while accomplices cover
    #      the rest, making the activity look like routine agent traffic.
    #   4. Recurring withdrawer flags: any withdrawer who has appeared in 3+
    #      other split incidents at the same till is tagged as a known associate.
    # ------------------------------------------------------------------
    def _detect_split_transactions(self, txn_dicts, detector):
        DEPOSIT_REASONS = {'Deposit at Agent Till'}
        WITHDRAWAL_REASONS = {
            'Customer Withdrawal at Agent Till',
            'Customer Withdrawal at Agent Till with OD',
        }
        ALL_RELEVANT = DEPOSIT_REASONS | WITHDRAWAL_REASONS

        # Group by shortcode
        by_shortcode = defaultdict(list)
        for txn in txn_dicts:
            if txn.get('reason_type') in ALL_RELEVANT:
                sc = txn.get('business_shortcode') or ''
                if sc:
                    by_shortcode[sc].append(txn)

        logger.info(f"[SPLIT] {len(by_shortcode)} shortcodes with relevant transactions")

        # ── First pass: detect qualifying incidents ────────────────────────────
        raw_results = []
        used_receipts = set()
        split_window = timedelta(minutes=SPLIT_WINDOW_MINUTES)

        for shortcode, txns in by_shortcode.items():
            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])

            # Withdrawals only, still time-sorted — lets us binary-search the
            # 2-hour window per anchor instead of rescanning every transaction
            # at this till for every anchor (that rescan was O(n^2) per till
            # and dominated report generation time on busy tills).
            withdrawals = [
                t for t in sorted_txns
                if t.get('reason_type') in WITHDRAWAL_REASONS and t.get('paid_in', 0) > 0
            ]
            withdrawal_times = [t['completion_time'] for t in withdrawals]

            for anchor in sorted_txns:
                if anchor['receipt_no'] in used_receipts:
                    continue
                if anchor.get('reason_type') not in DEPOSIT_REASONS:
                    continue

                anchor_amount = abs(anchor.get('withdrawn', 0))
                if anchor_amount < SPLIT_MIN_ANCHOR:
                    continue

                anchor_time = anchor['completion_time']
                depositor_phone = anchor.get('phone_number') or ''

                # Must have a parseable phone to enforce the depositor-is-withdrawer rule
                if not depositor_phone:
                    continue

                # Subsequent withdrawals at the same till within the window
                lo = bisect.bisect_right(withdrawal_times, anchor_time)
                hi = bisect.bisect_right(withdrawal_times, anchor_time + split_window)
                subsequent = [
                    t for t in withdrawals[lo:hi]
                    if t['receipt_no'] not in used_receipts
                ]

                if len(subsequent) < SPLIT_MIN_SUBSEQUENT:
                    continue

                total_subsequent = sum(t.get('paid_in', 0) for t in subsequent)
                coverage_ratio = total_subsequent / anchor_amount if anchor_amount > 0 else 0

                if not (SPLIT_MIN_COVERAGE <= coverage_ratio <= SPLIT_MAX_COVERAGE):
                    continue

                # ── Core rule: the depositor must also be one of the withdrawers ──
                depositor_withdrawals = [
                    t for t in subsequent if t.get('phone_number') == depositor_phone
                ]
                if not depositor_withdrawals:
                    continue

                candidate_receipts = {anchor['receipt_no']} | {t['receipt_no'] for t in subsequent}
                if candidate_receipts & used_receipts:
                    continue
                used_receipts |= candidate_receipts

                unique_phones = {t.get('phone_number') for t in subsequent if t.get('phone_number')}
                unique_withdrawers = max(len(unique_phones), 1)

                elapsed_total = (subsequent[-1]['completion_time'] - anchor_time).total_seconds() / 60
                depositor_name = anchor.get('name') or depositor_phone

                depositor_own_withdrawal = sum(t.get('paid_in', 0) for t in depositor_withdrawals)
                depositor_withdrawal_pct = round(depositor_own_withdrawal / anchor_amount * 100, 1)

                # Score: base + splits + unique withdrawers + bonus if depositor reclaims >70%
                fraud_score = min(
                    40 + len(subsequent) * 6 + unique_withdrawers * 2
                    + (10 if depositor_withdrawal_pct >= 70 else 0),
                    100
                )

                explanation = (
                    f"SPLIT TRANSACTION: {depositor_name} deposited KES {anchor_amount:,.2f} "
                    f"(receipt {anchor['receipt_no']}) at shortcode {shortcode}, then personally "
                    f"withdrew KES {depositor_own_withdrawal:,.2f} ({depositor_withdrawal_pct}% of the deposit) "
                    f"alongside {unique_withdrawers - 1} accomplice{'s' if unique_withdrawers - 1 != 1 else ''} "
                    f"— {len(subsequent)} withdrawals in total covering KES {total_subsequent:,.2f} "
                    f"({coverage_ratio*100:.0f}% of the deposit) within {elapsed_total:.1f} minute(s). "
                    f"The depositor reclaiming the bulk of funds through their own withdrawal while "
                    f"accomplices withdraw the remainder is the defining signature of split fraud."
                )

                txn_details = [
                    {
                        'receipt_no': anchor['receipt_no'],
                        'amount': anchor_amount,
                        'type': 'Deposit',
                        'time': anchor['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(anchor['completion_time'], 'strftime') else str(anchor['completion_time']),
                        'party_phone': depositor_phone,
                        'party_name': depositor_name,
                        'other_party_info': anchor.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'is_anchor': True,
                        'is_depositor_withdrawal': False,
                    }
                ] + [
                    {
                        'receipt_no': t['receipt_no'],
                        'amount': t.get('paid_in', 0),
                        'type': 'Withdrawal',
                        'time': t['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(t['completion_time'], 'strftime') else str(t['completion_time']),
                        'party_phone': t.get('phone_number') or '',
                        'party_name': t.get('name') or '',
                        'other_party_info': t.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'is_anchor': False,
                        # Flag rows where the depositor withdraws their own share
                        'is_depositor_withdrawal': t.get('phone_number') == depositor_phone,
                    }
                    for t in subsequent
                ]

                agent_info = detector._extract_agent_info_from_transactions([anchor] + subsequent)

                raw_results.append({
                    'fraud_type': 'split_transaction',
                    'account_phone': depositor_phone,
                    'account_name': depositor_name,
                    'transaction_count': 1 + len(subsequent),
                    'total_amount': anchor_amount + total_subsequent,
                    'anchor_amount': anchor_amount,
                    'anchor_type': 'deposit',
                    'subsequent_total': total_subsequent,
                    'subsequent_count': len(subsequent),
                    'unique_withdrawers': unique_withdrawers,
                    'coverage_ratio': round(coverage_ratio * 100, 1),
                    'depositor_own_withdrawal': depositor_own_withdrawal,
                    'depositor_withdrawal_pct': depositor_withdrawal_pct,
                    'time_window_minutes': round(elapsed_total, 1),
                    'receipt_nos': list(candidate_receipts),
                    'transaction_details': txn_details,
                    'explanation': explanation,
                    'detection_time': datetime.now(),
                    'fraud_score': fraud_score,
                    'agent_info': agent_info,
                    'business_shortcode': shortcode,
                    # Withdrawer phone list for second pass
                    '_withdrawer_phones': [t.get('phone_number') for t in subsequent if t.get('phone_number')],
                })

        # ── Second pass: tag recurring withdrawers ────────────────────────────
        # Count how many incidents each withdrawer phone appears in, per shortcode
        from collections import Counter
        withdrawer_incident_count: dict = defaultdict(Counter)  # {shortcode: {phone: count}}
        for r in raw_results:
            sc = r['business_shortcode']
            for ph in r['_withdrawer_phones']:
                withdrawer_incident_count[sc][ph] += 1

        results = []
        for r in raw_results:
            sc = r['business_shortcode']
            # Annotate each transaction detail with a recurring flag
            for txn in r['transaction_details']:
                ph = txn.get('party_phone', '')
                count = withdrawer_incident_count[sc].get(ph, 0)
                txn['recurring_incident_count'] = count
                txn['is_recurring_suspect'] = count >= 3 and not txn.get('is_anchor')
            # Build a summary list of recurring associates for quick display
            r['recurring_associates'] = [
                {'phone': ph, 'incident_count': cnt}
                for ph, cnt in withdrawer_incident_count[sc].items()
                if cnt >= 3 and ph != r['account_phone']
            ]
            del r['_withdrawer_phones']
            results.append(r)

        results.sort(key=lambda r: r['fraud_score'], reverse=True)
        logger.info(f"[SPLIT] {len(results)} qualifying findings (depositor-is-withdrawer rule applied)")
        return results

    # ------------------------------------------------------------------
    # Deposit → Withdrawal Recovery
    # ------------------------------------------------------------------
    def _detect_deposit_withdrawal_recovery(self, txn_dicts, detector):
        """
        Flag a large deposit followed by withdrawal(s) from the same phone at
        the same shortcode within 24 hours, where total withdrawn >= 50% of deposit.
        """
        RELEVANT_REASONS = {
            'Deposit at Agent Till',
            'Customer Withdrawal at Agent Till',
            'Customer Withdrawal at Agent Till with OD',
        }

        relevant = [
            t for t in txn_dicts
            if t.get('reason_type') in RELEVANT_REASONS and t.get('phone_number')
        ]
        logger.info(f"[DWR] {len(relevant)}/{len(txn_dicts)} txns match relevant reason_types and have a phone")

        # Group by (phone, shortcode)
        groups = defaultdict(list)
        for txn in relevant:
            key = (txn['phone_number'], txn.get('business_shortcode') or '')
            groups[key].append(txn)
        logger.info(f"[DWR] {len(groups)} (phone, shortcode) groups")

        results = []
        used_receipts = set()

        for (phone, shortcode), txns in groups.items():
            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])

            deposits = [t for t in sorted_txns if t.get('paid_in', 0) >= DWR_MIN_DEPOSIT]
            withdrawals = [t for t in sorted_txns if abs(t.get('withdrawn', 0)) >= 1000]

            if deposits:
                logger.debug(f"[DWR] ({phone}, {shortcode}): {len(deposits)} deposits >= {DWR_MIN_DEPOSIT}, {len(withdrawals)} withdrawals >= 1000")

            for dep in deposits:
                if dep['receipt_no'] in used_receipts:
                    continue

                dep_amount = dep['paid_in']
                dep_time = dep['completion_time']

                # Find withdrawals after this deposit within DWR_WINDOW_HOURS
                matching_withdrawals = [
                    w for w in withdrawals
                    if w['receipt_no'] not in used_receipts
                    and w['completion_time'] > dep_time
                    and (w['completion_time'] - dep_time).total_seconds() / 3600 <= DWR_WINDOW_HOURS
                ]

                if not matching_withdrawals:
                    logger.debug(f"[DWR] ({phone}) deposit {dep['receipt_no']} KES {dep_amount} — no matching withdrawals within {DWR_WINDOW_HOURS}h")
                    continue

                total_withdrawn = sum(abs(w['withdrawn']) for w in matching_withdrawals)
                recovery_pct = total_withdrawn / dep_amount if dep_amount > 0 else 0

                if recovery_pct < DWR_RECOVERY_PCT:
                    logger.debug(f"[DWR] ({phone}) deposit {dep['receipt_no']} KES {dep_amount} → recovery {recovery_pct*100:.1f}% < {DWR_RECOVERY_PCT*100}% threshold — skipped")
                    continue

                candidate_receipts = {dep['receipt_no']} | {w['receipt_no'] for w in matching_withdrawals}
                used_receipts |= candidate_receipts

                time_to_first = (matching_withdrawals[0]['completion_time'] - dep_time).total_seconds() / 60
                overdraw = recovery_pct > 1.0

                fraud_score = 80 if (time_to_first <= 10 or overdraw) else (60 if time_to_first <= 60 else 40)

                explanation = (
                    f"DEPOSIT-WITHDRAWAL RECOVERY: {dep['name'] or phone} deposited "
                    f"KES {dep_amount:,.2f} (receipt {dep['receipt_no']}) then withdrew a total of "
                    f"KES {total_withdrawn:,.2f} ({recovery_pct * 100:.1f}% recovery) across "
                    f"{len(matching_withdrawals)} transaction(s) within "
                    f"{time_to_first:.0f} minute(s).{' Withdrawal EXCEEDS the deposit (possible pre-existing balance exploitation).' if overdraw else ''} "
                    f"Shortcode: {shortcode}."
                )

                txn_details = [
                    {
                        'receipt_no': dep['receipt_no'],
                        'amount': dep_amount,
                        'type': 'Deposit',
                        'time': dep['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(dep['completion_time'], 'strftime') else str(dep['completion_time']),
                        'party_phone': phone,
                        'party_name': dep['name'],
                        'other_party_info': dep.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'agent_id': dep.get('agent_id'),
                    }
                ] + [
                    {
                        'receipt_no': w['receipt_no'],
                        'amount': abs(w['withdrawn']),
                        'type': 'Withdrawal',
                        'time': w['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(w['completion_time'], 'strftime') else str(w['completion_time']),
                        'party_phone': phone,
                        'party_name': w['name'],
                        'other_party_info': w.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'agent_id': w.get('agent_id'),
                    }
                    for w in matching_withdrawals
                ]

                agent_info = detector._extract_agent_info_from_transactions([dep] + matching_withdrawals)

                results.append({
                    'fraud_type': 'deposit_withdrawal_recovery',
                    'account_phone': phone,
                    'account_name': dep['name'],
                    'transaction_count': 1 + len(matching_withdrawals),
                    'total_amount': dep_amount + total_withdrawn,
                    'deposit_amount': dep_amount,
                    'total_withdrawn': total_withdrawn,
                    'recovery_pct': round(recovery_pct * 100, 1),
                    'time_to_first_withdrawal_minutes': round(time_to_first, 1),
                    'overdraw': overdraw,
                    'receipt_nos': [dep['receipt_no']] + [w['receipt_no'] for w in matching_withdrawals],
                    'transaction_details': txn_details,
                    'explanation': explanation,
                    'detection_time': datetime.now(),
                    'fraud_score': fraud_score,
                    'agent_info': agent_info,
                    'business_shortcode': shortcode,
                })

        return results

    # ------------------------------------------------------------------
    # Rapid Back-and-Forth (window-based: 5+ txns in ≤3 minutes)
    # ------------------------------------------------------------------
    def _detect_rapid_back_forth_window(self, txn_dicts, detector):
        """
        Flag groups of RBF_MIN_TRANSACTIONS+ transactions by the same phone
        at the same shortcode within RBF_WINDOW_MINUTES, where the group
        contains both deposits and withdrawals.
        """
        # Only deposit/withdrawal transactions
        RELEVANT_REASONS = {
            'Deposit at Agent Till',
            'Customer Withdrawal at Agent Till',
            'Customer Withdrawal at Agent Till with OD',
        }

        relevant = [
            t for t in txn_dicts
            if t.get('reason_type') in RELEVANT_REASONS and t.get('phone_number')
        ]
        logger.info(f"[RBF] {len(relevant)}/{len(txn_dicts)} txns eligible (relevant reason + phone)")

        groups = defaultdict(list)
        for txn in relevant:
            key = (txn['phone_number'], txn.get('business_shortcode') or '')
            groups[key].append(txn)

        eligible_groups = {k: v for k, v in groups.items() if len(v) >= RBF_MIN_TRANSACTIONS}
        logger.info(f"[RBF] {len(eligible_groups)}/{len(groups)} groups have >= {RBF_MIN_TRANSACTIONS} txns")

        results = []
        used_receipts = set()

        for (phone, shortcode), txns in groups.items():
            if len(txns) < RBF_MIN_TRANSACTIONS:
                continue

            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])

            for i in range(len(sorted_txns)):
                window = [sorted_txns[i]]
                for j in range(i + 1, len(sorted_txns)):
                    elapsed = (sorted_txns[j]['completion_time'] - sorted_txns[i]['completion_time']).total_seconds() / 60
                    if elapsed <= RBF_WINDOW_MINUTES:
                        window.append(sorted_txns[j])
                    else:
                        break

                if len(window) < RBF_MIN_TRANSACTIONS:
                    continue

                # Must have both deposits and withdrawals
                has_deposit = any(t.get('paid_in', 0) > 0 for t in window)
                has_withdrawal = any(abs(t.get('withdrawn', 0)) > 0 for t in window)
                if not (has_deposit and has_withdrawal):
                    logger.debug(f"[RBF] ({phone}) window of {len(window)} txns skipped — missing {'deposit' if not has_deposit else 'withdrawal'}")
                    continue

                candidate_receipts = {t['receipt_no'] for t in window}
                if candidate_receipts & used_receipts:
                    continue
                used_receipts |= candidate_receipts

                elapsed_total = (window[-1]['completion_time'] - window[0]['completion_time']).total_seconds() / 60
                total_amount = sum(
                    t.get('paid_in', 0) + abs(t.get('withdrawn', 0)) for t in window
                )
                deposit_total = sum(t.get('paid_in', 0) for t in window)
                withdrawal_total = sum(abs(t.get('withdrawn', 0)) for t in window)
                net_flow = deposit_total - withdrawal_total

                txn_details = [
                    {
                        'receipt_no': t['receipt_no'],
                        'amount': t.get('paid_in', 0) if t.get('paid_in', 0) > 0 else abs(t.get('withdrawn', 0)),
                        'type': 'Deposit' if t.get('paid_in', 0) > 0 else 'Withdrawal',
                        'time': t['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(t['completion_time'], 'strftime') else str(t['completion_time']),
                        'party_phone': phone,
                        'party_name': t.get('name'),
                        'other_party_info': t.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'agent_id': t.get('agent_id'),
                    }
                    for t in window
                ]

                explanation = (
                    f"RAPID BACK-AND-FORTH: {window[0].get('name') or phone} made {len(window)} transactions "
                    f"(deposits + withdrawals) at shortcode {shortcode} within {elapsed_total:.1f} minute(s). "
                    f"Total deposits: KES {deposit_total:,.2f}, total withdrawals: KES {withdrawal_total:,.2f}, "
                    f"net flow: KES {net_flow:,.2f}. "
                    f"This rapid alternating pattern is consistent with commission farming or float manipulation."
                )

                fraud_score = min(50 + len(window) * 8, 100)
                agent_info = detector._extract_agent_info_from_transactions(window)

                results.append({
                    'fraud_type': 'rapid_back_forth',
                    'account_phone': phone,
                    'account_name': window[0].get('name'),
                    'transaction_count': len(window),
                    'total_amount': total_amount,
                    'net_flow': net_flow,
                    'time_window': elapsed_total,
                    'receipt_nos': list(candidate_receipts),
                    'transaction_details': txn_details,
                    'explanation': explanation,
                    'detection_time': datetime.now(),
                    'fraud_score': fraud_score,
                    'agent_info': agent_info,
                    'business_shortcode': shortcode,
                })

        return results

    # ------------------------------------------------------------------
    # High-Frequency Daily Activity
    # ------------------------------------------------------------------
    def _detect_high_frequency_daily(self, txn_dicts, detector=None):
        """
        Flag any party (phone) that has HF_MIN_TRANSACTIONS or more transactions
        on the same calendar day at the same shortcode.
        No fraud-type label or description — just list the party, transactions,
        amounts, and times.
        """
        # Group by (phone, shortcode, date)
        groups = defaultdict(list)
        for txn in txn_dicts:
            phone = txn.get('phone_number')
            if not phone:
                continue
            shortcode = txn.get('business_shortcode') or ''
            day = txn['completion_time'].date() if hasattr(txn['completion_time'], 'date') else txn['completion_time']
            groups[(phone, shortcode, day)].append(txn)

        eligible = {k: v for k, v in groups.items() if len(v) >= HF_MIN_TRANSACTIONS}
        logger.info(f"[HF] {len(groups)} (phone, shortcode, day) groups — {len(eligible)} have >= {HF_MIN_TRANSACTIONS} txns")

        results = []
        used_receipts = set()

        for (phone, shortcode, day), txns in groups.items():
            if len(txns) < HF_MIN_TRANSACTIONS:
                continue

            candidate_receipts = {t['receipt_no'] for t in txns}
            if candidate_receipts & used_receipts:
                continue
            used_receipts |= candidate_receipts

            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])
            total_amount = sum(
                t.get('paid_in', 0) + abs(t.get('withdrawn', 0)) for t in sorted_txns
            )

            txn_details = [
                {
                    'receipt_no': t['receipt_no'],
                    'amount': t.get('paid_in', 0) if t.get('paid_in', 0) > 0 else abs(t.get('withdrawn', 0)),
                    'type': 'Deposit' if t.get('paid_in', 0) > 0 else 'Withdrawal',
                    'time': t['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                        if hasattr(t['completion_time'], 'strftime') else str(t['completion_time']),
                    'party_phone': phone,
                    'party_name': t.get('name'),
                    'other_party_info': t.get('other_party_info', ''),
                    'business_shortcode': shortcode,
                    'agent_id': t.get('agent_id'),
                }
                for t in sorted_txns
            ]

            results.append({
                'fraud_type': 'high_frequency_daily',
                'account_phone': phone,
                'account_name': sorted_txns[0].get('name'),
                'transaction_count': len(sorted_txns),
                'total_amount': total_amount,
                'day': str(day),
                'business_shortcode': shortcode,
                'receipt_nos': list(candidate_receipts),
                'transaction_details': txn_details,
                'explanation': None,
                'detection_time': datetime.now(),
                'fraud_score': min(20 + len(sorted_txns) * 5, 70),
                'agent_info': detector._extract_agent_info_from_transactions(sorted_txns) if detector else {'agent_companies': [], 'user_agents': [], 'shortcodes': [shortcode] if shortcode else []},
            })

        return results

    # ------------------------------------------------------------------
    # Structuring: same phone, same direction, rapid burst
    # Catches e.g. KIPKIRUI making 4 deposits of ~149K each in 3.4 minutes.
    # The existing split/RBF detectors require MIXED directions — this one
    # flags purely same-direction bursts that indicate structured layering.
    # ------------------------------------------------------------------
    def _detect_same_phone_rapid_same_direction(self, txn_dicts, detector):
        CUSTOMER_REASONS = {
            'Deposit at Agent Till',
            'Customer Withdrawal at Agent Till',
            'Customer Withdrawal at Agent Till with OD',
        }

        relevant = [
            t for t in txn_dicts
            if t.get('reason_type') in CUSTOMER_REASONS and t.get('phone_number')
        ]
        logger.info(f"[STRUCT] {len(relevant)} eligible txns")

        groups = defaultdict(list)
        for txn in relevant:
            key = (txn['phone_number'], txn.get('business_shortcode') or '')
            groups[key].append(txn)

        results = []
        used_receipts = set()

        for (phone, shortcode), txns in groups.items():
            if len(txns) < STRUCT_MIN_TRANSACTIONS:
                continue

            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])

            for i in range(len(sorted_txns)):
                anchor = sorted_txns[i]
                anchor_is_deposit = anchor.get('paid_in', 0) > 0
                direction = 'deposit' if anchor_is_deposit else 'withdrawal'

                # Collect same-direction transactions within the window
                window = [anchor]
                for j in range(i + 1, len(sorted_txns)):
                    elapsed = (sorted_txns[j]['completion_time'] - anchor['completion_time']).total_seconds() / 60
                    if elapsed > STRUCT_WINDOW_MINUTES:
                        break
                    txn_is_deposit = sorted_txns[j].get('paid_in', 0) > 0
                    if txn_is_deposit == anchor_is_deposit:
                        window.append(sorted_txns[j])

                if len(window) < STRUCT_MIN_TRANSACTIONS:
                    continue

                total = sum(
                    t.get('paid_in', 0) if anchor_is_deposit else abs(t.get('withdrawn', 0))
                    for t in window
                )
                if total < STRUCT_MIN_TOTAL:
                    continue

                candidate_receipts = {t['receipt_no'] for t in window}
                if candidate_receipts & used_receipts:
                    continue
                used_receipts |= candidate_receipts

                span_mins = (window[-1]['completion_time'] - window[0]['completion_time']).total_seconds() / 60
                amounts = [
                    t.get('paid_in', 0) if anchor_is_deposit else abs(t.get('withdrawn', 0))
                    for t in window
                ]
                max_amount = max(amounts)

                # Structuring indicator: transactions clustered just below a round threshold
                structuring_flag = any(
                    round_threshold - amt < round_threshold * 0.05 and amt < round_threshold
                    for amt in amounts
                    for round_threshold in (70000, 100000, 150000, 200000, 300000, 500000)
                )

                fraud_score = min(55 + len(window) * 7, 100)
                if structuring_flag:
                    fraud_score = min(fraud_score + 15, 100)

                name = anchor.get('name')
                explanation = (
                    f"STRUCTURING — SAME-DIRECTION BURST: {name or phone} made {len(window)} "
                    f"{direction}s totalling KES {total:,.2f} at shortcode {shortcode} "
                    f"within {span_mins:.1f} minute(s). "
                    f"Largest single transaction: KES {max_amount:,.2f}. "
                    + (
                        "Amounts are clustered just below common reporting thresholds — "
                        "consistent with deliberate structuring to avoid detection. "
                        if structuring_flag else ""
                    ) +
                    "This pattern suggests layering or cash placement via structured same-direction transactions."
                )

                txn_details = [
                    {
                        'receipt_no': t['receipt_no'],
                        'amount': t.get('paid_in', 0) if anchor_is_deposit else abs(t.get('withdrawn', 0)),
                        'type': 'Deposit' if anchor_is_deposit else 'Withdrawal',
                        'time': t['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(t['completion_time'], 'strftime') else str(t['completion_time']),
                        'party_phone': phone,
                        'party_name': t.get('name'),
                        'other_party_info': t.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'agent_id': t.get('agent_id'),
                    }
                    for t in window
                ]

                agent_info = detector._extract_agent_info_from_transactions(window)

                results.append({
                    'fraud_type': 'structuring',
                    'account_phone': phone,
                    'account_name': name,
                    'transaction_count': len(window),
                    'total_amount': total,
                    'direction': direction,
                    'span_minutes': round(span_mins, 1),
                    'structuring_flag': structuring_flag,
                    'receipt_nos': list(candidate_receipts),
                    'transaction_details': txn_details,
                    'explanation': explanation,
                    'detection_time': datetime.now(),
                    'fraud_score': fraud_score,
                    'agent_info': agent_info,
                    'business_shortcode': shortcode,
                })

        logger.info(f"[STRUCT] {len(results)} findings")
        return results

    # ------------------------------------------------------------------
    # Float Cycling: large till top-up immediately drained via API/B2B
    # Catches the pass-through pattern: MMF/merchant loads float,
    # then Business Deposit via API or similar drains >= 50 % within 2 hrs.
    # ------------------------------------------------------------------
    def _detect_float_cycling(self, txn_dicts, detector):
        # Group ALL float transactions by shortcode
        by_shortcode = defaultdict(list)
        for txn in txn_dicts:
            if txn.get('transaction_type') == 'float':
                sc = txn.get('business_shortcode') or ''
                if sc:
                    by_shortcode[sc].append(txn)

        logger.info(f"[CYCLING] {len(by_shortcode)} shortcodes with float transactions")

        results = []
        used_receipts = set()

        for shortcode, txns in by_shortcode.items():
            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])

            top_ups = [
                t for t in sorted_txns
                if t.get('reason_type') in FLOAT_TOP_UP_REASONS
                and t.get('paid_in', 0) >= CYCLING_MIN_TOP_UP
            ]
            drains = [
                t for t in sorted_txns
                if t.get('reason_type') in FLOAT_DRAIN_REASONS
                and abs(t.get('withdrawn', 0)) > 0
            ]

            if not top_ups or not drains:
                continue

            for top_up in top_ups:
                top_up_amount = top_up.get('paid_in', 0)
                top_up_time = top_up['completion_time']

                # Find drain events within CYCLING_WINDOW_MINUTES
                matching_drains = [
                    d for d in drains
                    if d['receipt_no'] not in used_receipts
                    and abs((d['completion_time'] - top_up_time).total_seconds() / 60) <= CYCLING_WINDOW_MINUTES
                ]
                if not matching_drains:
                    continue

                drain_total = sum(abs(d.get('withdrawn', 0)) for d in matching_drains)
                drain_pct = drain_total / top_up_amount if top_up_amount > 0 else 0

                if drain_pct < CYCLING_DRAIN_PCT:
                    continue

                candidate_receipts = {top_up['receipt_no']} | {d['receipt_no'] for d in matching_drains}
                if candidate_receipts & used_receipts:
                    continue
                used_receipts |= candidate_receipts

                span_mins = max(
                    abs((d['completion_time'] - top_up_time).total_seconds() / 60)
                    for d in matching_drains
                )
                overdrain = drain_pct > 1.0

                fraud_score = min(65 + len(matching_drains) * 5, 100)
                if span_mins <= 30:
                    fraud_score = min(fraud_score + 15, 100)

                explanation = (
                    f"FLOAT CYCLING — PASS-THROUGH: Till {shortcode} received a float top-up of "
                    f"KES {top_up_amount:,.2f} ({top_up['reason_type']}, receipt {top_up['receipt_no']}) "
                    f"at {top_up_time.strftime('%Y-%m-%d %H:%M')}. "
                    f"Within {span_mins:.0f} minute(s), {len(matching_drains)} outbound "
                    f"transaction(s) drained KES {drain_total:,.2f} "
                    f"({drain_pct * 100:.0f}% of the top-up)"
                    + (" — exceeding the top-up amount, indicating pre-existing float was also swept." if overdrain else "") +
                    ". This rapid load-then-drain cycle is consistent with float being used as a "
                    "pass-through channel for funds laundering or unauthorized transfers."
                )

                all_txns = [top_up] + matching_drains
                txn_details = [
                    {
                        'receipt_no': t['receipt_no'],
                        'amount': t.get('paid_in', 0) if t.get('paid_in', 0) > 0 else abs(t.get('withdrawn', 0)),
                        'type': 'Top-up' if t['receipt_no'] == top_up['receipt_no'] else 'Drain',
                        'reason_type': t.get('reason_type', ''),
                        'time': t['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(t['completion_time'], 'strftime') else str(t['completion_time']),
                        'party_phone': t.get('phone_number'),
                        'party_name': t.get('name'),
                        'other_party_info': t.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'agent_id': t.get('agent_id'),
                    }
                    for t in all_txns
                ]

                agent_info = detector._extract_agent_info_from_transactions(all_txns)

                results.append({
                    'fraud_type': 'float_cycling',
                    'account_phone': None,
                    'account_name': None,
                    'transaction_count': len(all_txns),
                    'total_amount': top_up_amount + drain_total,
                    'top_up_amount': top_up_amount,
                    'drain_total': drain_total,
                    'drain_pct': round(drain_pct * 100, 1),
                    'span_minutes': round(span_mins, 1),
                    'overdrain': overdrain,
                    'receipt_nos': list(candidate_receipts),
                    'transaction_details': txn_details,
                    'explanation': explanation,
                    'detection_time': datetime.now(),
                    'fraud_score': fraud_score,
                    'agent_info': agent_info,
                    'business_shortcode': shortcode,
                })

        logger.info(f"[CYCLING] {len(results)} findings")
        return results

    # ------------------------------------------------------------------
    # Split Deposit: one person's deposit split into several deposits
    # Catches e.g. a KES 50,000 deposit arriving as 20,000 + 20,000 + 10,000
    # from the same party in quick succession. Deposits at or above the
    # single-deposit cap (SINGLE_DEPOSIT_CAP) are excluded up front — moving
    # more than the cap requires multiple deposits by construction, so a
    # full-cap deposit is never itself evidence of splitting. A 2-deposit
    # chain (both members already sub-cap) only qualifies when their combined
    # amount reaches the cap (e.g. 200,000 + 150,000 within a minute —
    # structuring to stay under the cap on each individual deposit).
    # ------------------------------------------------------------------
    def _detect_split_deposits(self, txn_dicts, detector):
        deposits = [
            t for t in txn_dicts
            if t.get('reason_type') == 'Deposit at Agent Till' and t.get('phone_number')
        ]

        # Deposits at a till record the amount as float leaving the till
        # (withdrawn); fall back to paid_in for statement variants.
        def _amount(t):
            return abs(t.get('withdrawn', 0)) or t.get('paid_in', 0)

        # A deposit at or above the single-transaction cap is a legitimate
        # max-out, not evidence of splitting — moving more than the cap
        # requires multiple deposits by construction (the platform won't allow
        # a single deposit above it), so e.g. 250,000 followed by another
        # deposit must never itself be flagged. Only amounts strictly below
        # the cap are eligible to form a split chain.
        pre_filter_count = len(deposits)
        deposits = [t for t in deposits if _amount(t) < SINGLE_DEPOSIT_CAP]
        logger.info(
            f"[SPLITDEP] {len(deposits)} sub-cap deposit(s) with a parsed phone "
            f"({pre_filter_count - len(deposits)} at/above the {SINGLE_DEPOSIT_CAP:,.0f} cap excluded)"
        )

        groups = defaultdict(list)
        for txn in deposits:
            key = (txn['phone_number'], txn.get('business_shortcode') or '')
            groups[key].append(txn)

        results = []
        used_receipts = set()

        for (phone, shortcode), txns in groups.items():
            if len(txns) < 2:
                continue

            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])

            # Build chains: consecutive deposits <= SPLITDEP_MAX_GAP_MINUTES apart
            chain = [sorted_txns[0]]
            chains = []
            for txn in sorted_txns[1:]:
                gap = (txn['completion_time'] - chain[-1]['completion_time']).total_seconds() / 60
                if gap <= SPLITDEP_MAX_GAP_MINUTES:
                    chain.append(txn)
                else:
                    chains.append(chain)
                    chain = [txn]
            chains.append(chain)

            for chain in chains:
                total = sum(_amount(t) for t in chain)
                qualifies = (
                    (len(chain) >= SPLITDEP_MIN_COUNT and total >= SPLITDEP_MIN_TOTAL)
                    or (len(chain) == 2 and total >= SPLITDEP_PAIR_MIN_TOTAL)
                )
                if not qualifies:
                    continue

                candidate_receipts = {t['receipt_no'] for t in chain}
                if candidate_receipts & used_receipts:
                    continue
                used_receipts |= candidate_receipts

                span_mins = (chain[-1]['completion_time'] - chain[0]['completion_time']).total_seconds() / 60
                amounts = [_amount(t) for t in chain]
                cap_structuring = total >= SPLITDEP_PAIR_MIN_TOTAL

                fraud_score = min(40 + len(chain) * 8 + (20 if cap_structuring else 0), 100)

                name = chain[0].get('name')
                amounts_str = ' + '.join(f"{a:,.0f}" for a in amounts)
                explanation = (
                    f"SPLIT DEPOSIT: {name or phone} made {len(chain)} separate deposits "
                    f"({amounts_str} = KES {total:,.2f}) at shortcode {shortcode} "
                    f"within {span_mins:.1f} minute(s). "
                    + (
                        "The combined amount exceeds the single-deposit limit — the deposit was "
                        "split to stay under the cap and avoid the scrutiny a single large "
                        "deposit would attract. "
                        if cap_structuring else
                        "One deposit broken into several smaller ones in quick succession "
                        "suggests deliberate splitting to stay below review thresholds. "
                    )
                )

                txn_details = [
                    {
                        'receipt_no': t['receipt_no'],
                        'amount': _amount(t),
                        'type': 'Deposit',
                        'time': t['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(t['completion_time'], 'strftime') else str(t['completion_time']),
                        'party_phone': phone,
                        'party_name': t.get('name'),
                        'other_party_info': t.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'agent_id': t.get('agent_id'),
                    }
                    for t in chain
                ]

                agent_info = detector._extract_agent_info_from_transactions(chain)

                results.append({
                    'fraud_type': 'split_deposit',
                    'account_phone': phone,
                    'account_name': name,
                    'transaction_count': len(chain),
                    'total_amount': total,
                    'span_minutes': round(span_mins, 1),
                    'cap_structuring': cap_structuring,
                    'receipt_nos': list(candidate_receipts),
                    'transaction_details': txn_details,
                    'explanation': explanation,
                    'detection_time': datetime.now(),
                    'fraud_score': fraud_score,
                    'agent_info': agent_info,
                    'business_shortcode': shortcode,
                })

        logger.info(f"[SPLITDEP] {len(results)} findings")
        return results

    # ------------------------------------------------------------------
    # Continuous Rapid Activity: a till transacting non-stop
    # Flags a chain of customer transactions (deposits, withdrawals or both)
    # at one till where every gap between consecutive transactions is
    # <= CRA_MAX_GAP_MINUTES and the chain runs for CRA_MIN_DURATION_MINUTES+.
    # ------------------------------------------------------------------
    def _detect_continuous_rapid_activity(self, txn_dicts, detector):
        RELEVANT_REASONS = {
            'Deposit at Agent Till',
            'Customer Withdrawal at Agent Till',
            'Customer Withdrawal at Agent Till with OD',
        }

        by_shortcode = defaultdict(list)
        for txn in txn_dicts:
            if txn.get('reason_type') in RELEVANT_REASONS:
                sc = txn.get('business_shortcode') or ''
                if sc:
                    by_shortcode[sc].append(txn)

        results = []

        for shortcode, txns in by_shortcode.items():
            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])

            chain = [sorted_txns[0]]
            chains = []
            for txn in sorted_txns[1:]:
                gap = (txn['completion_time'] - chain[-1]['completion_time']).total_seconds() / 60
                if gap <= CRA_MAX_GAP_MINUTES:
                    chain.append(txn)
                else:
                    chains.append(chain)
                    chain = [txn]
            chains.append(chain)

            for chain in chains:
                if len(chain) < 2:
                    continue
                span_mins = (chain[-1]['completion_time'] - chain[0]['completion_time']).total_seconds() / 60
                if span_mins < CRA_MIN_DURATION_MINUTES:
                    continue

                deposit_total = sum(abs(t.get('withdrawn', 0)) for t in chain if t.get('reason_type') == 'Deposit at Agent Till')
                withdrawal_total = sum(t.get('paid_in', 0) for t in chain if t.get('reason_type') != 'Deposit at Agent Till')
                total = deposit_total + withdrawal_total
                unique_parties = len({t.get('phone_number') for t in chain if t.get('phone_number')})
                deposits = sum(1 for t in chain if t.get('reason_type') == 'Deposit at Agent Till')
                withdrawals = len(chain) - deposits

                fraud_score = min(55 + int(span_mins - CRA_MIN_DURATION_MINUTES) // 15 * 5 + len(chain) // 25 * 5, 100)

                explanation = (
                    f"CONTINUOUS RAPID ACTIVITY: shortcode {shortcode} processed {len(chain)} "
                    f"customer transactions ({deposits} deposit(s), {withdrawals} withdrawal(s)) "
                    f"non-stop for {span_mins:.0f} minute(s) — no gap between consecutive "
                    f"transactions exceeded {CRA_MAX_GAP_MINUTES} minute(s). "
                    f"Total volume: KES {total:,.2f} across {unique_parties} distinct part(y/ies). "
                    f"Sustained machine-gun activity at a till for an hour or more is far above "
                    f"normal walk-in traffic and indicates coordinated cash movement."
                )

                txn_details = [
                    {
                        'receipt_no': t['receipt_no'],
                        'amount': abs(t.get('withdrawn', 0)) if t.get('reason_type') == 'Deposit at Agent Till' else t.get('paid_in', 0),
                        'type': 'Deposit' if t.get('reason_type') == 'Deposit at Agent Till' else 'Withdrawal',
                        'time': t['completion_time'].strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(t['completion_time'], 'strftime') else str(t['completion_time']),
                        'party_phone': t.get('phone_number'),
                        'party_name': t.get('name'),
                        'other_party_info': t.get('other_party_info', ''),
                        'business_shortcode': shortcode,
                        'agent_id': t.get('agent_id'),
                    }
                    for t in chain
                ]

                agent_info = detector._extract_agent_info_from_transactions(chain)

                results.append({
                    'fraud_type': 'continuous_rapid_activity',
                    'account_phone': None,
                    'account_name': None,
                    'transaction_count': len(chain),
                    'total_amount': total,
                    'deposit_count': deposits,
                    'withdrawal_count': withdrawals,
                    'unique_parties': unique_parties,
                    'span_minutes': round(span_mins, 1),
                    'receipt_nos': [t['receipt_no'] for t in chain],
                    'transaction_details': txn_details,
                    'explanation': explanation,
                    'detection_time': datetime.now(),
                    'fraud_score': fraud_score,
                    'agent_info': agent_info,
                    'business_shortcode': shortcode,
                })

        logger.info(f"[CRA] {len(results)} findings")
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _fetch_transactions(self, start_dt, end_dt, company_id, company_ids=None):
        query = Transaction.query.filter(
            Transaction.completion_time >= start_dt,
            Transaction.completion_time <= end_dt,
            Transaction.transaction_status == 'Completed',
        )
        if company_id:
            query = query.filter(Transaction.company_id == company_id)
        elif company_ids is not None:
            query = query.filter(Transaction.company_id.in_(company_ids))
        return query.order_by(Transaction.completion_time).all()

    def _to_dicts(self, transactions):
        result = []
        for t in transactions:
            result.append({
                'id': t.id,
                'receipt_no': t.receipt_no,
                'completion_time': t.completion_time,
                'paid_in': float(t.paid_in or 0),
                'withdrawn': float(t.withdrawn or 0),
                'balance': float(t.balance or 0),
                'other_party_info': t.other_party_info or '',
                'reason_type': t.reason_type,
                'transaction_type': t.transaction_type,
                'business_shortcode': t.business_shortcode,
                'agent_id': t.agent_id,
                'company_id': t.company_id,
            })
        return result

    def _serialize_result(self, r):
        def _fix(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, (set, frozenset)):
                return list(obj)
            return obj

        def _deep(obj):
            if isinstance(obj, dict):
                return {k: _deep(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_deep(i) for i in obj]
            return _fix(obj)

        return _deep(r)

    def _empty_report(self, start_dt, end_dt):
        return {
            'period': f"{start_dt.strftime('%d %b %Y')} - {end_dt.strftime('%d %b %Y')}",
            'summary': {
                'total_transactions_analyzed': 0,
                'total_findings': 0,
                'split_transactions': 0,
                'rollover_fraud': 0,
                'rapid_back_forth': 0,
                'deposit_withdrawal_recovery': 0,
                'high_frequency_daily': 0,
                'structuring': 0,
                'float_cycling': 0,
                'split_deposit': 0,
                'continuous_rapid_activity': 0,
                'high_risk': 0,
                'medium_risk': 0,
                'low_risk': 0,
            },
            'findings': [],
        }
