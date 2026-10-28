"""
Offline tests for the Udyami loan arithmetic (DEC-027, DEC-028).

    python -m pytest tests/test_loan_calculator.py
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from companies.core.loan_calculator import (  # noqa: E402
    MICRO_FINANCE, TERM_LOAN, format_inr, quote,
)


# ---- the problem statement's own worked example ---------------------------
def test_ps_worked_example_one_lakh_margin():
    q = quote(100_000)
    assert q.project_cost == 1_000_000
    assert q.loan_amount == 900_000
    assert q.scheme is TERM_LOAN
    assert q.own_contribution == 100_000   # margin money = 10% of the cost


# ---- scheme selection and its boundaries ----------------------------------
@pytest.mark.parametrize("margin, scheme", [
    (1, MICRO_FINANCE),
    (10_000, MICRO_FINANCE),
    (14_000, MICRO_FINANCE),        # cost exactly Rs 1.40 lakh: still micro
    (14_001, TERM_LOAN),            # one rupee of margin more: cost 1,40,010
    (500_000, TERM_LOAN),           # cost exactly Rs 50 lakh: still term
])
def test_scheme_boundaries(margin, scheme):
    assert quote(margin).scheme is scheme


def test_above_fifty_lakh_is_not_covered():
    q = quote(500_001)
    assert not q.covered
    assert q.scheme is None
    assert q.loan_amount is None and q.monthly_instalment is None
    assert q.project_cost == 5_000_010


# ---- loan sizing and the caps ---------------------------------------------
def test_loan_is_ninety_percent_below_the_cap():
    q = quote(10_000)               # cost 1,00,000
    assert q.loan_amount == 90_000
    assert q.own_contribution == 10_000


def test_micro_cap_binds_just_under_the_boundary():
    q = quote(14_000)               # 90% of 1,40,000 = 1,26,000, capped at 1,25,000
    assert q.loan_amount == 125_000
    assert q.own_contribution == 15_000   # more than the 10% margin: the cap shifts Rs 1,000 to the caller


def test_term_cap_equals_ninety_percent_at_fifty_lakh():
    q = quote(500_000)
    assert q.loan_amount == 4_500_000


# ---- the instalment, checked by simulating the loan ------------------------
def _residual_after_repayment(q):
    """Walk the balance month by month and return what's left after the last instalment."""
    s = q.scheme
    r = s.annual_rate_pct / 100 / 12
    balance = Decimal(q.loan_amount)
    for _ in range(s.moratorium_months):
        balance *= 1 + r
    for _ in range(q.repayment_months):
        balance = balance * (1 + r) - q.monthly_instalment
    return balance


@pytest.mark.parametrize("margin", [1_000, 10_000, 14_000, 20_000, 100_000, 250_000, 500_000])
def test_instalment_clears_the_loan(margin):
    q = quote(margin)
    # The instalment is rounded to a whole rupee, so a few rupees of drift is fine.
    assert abs(_residual_after_repayment(q)) < q.repayment_months


def test_repayment_months_exclude_the_moratorium():
    assert quote(10_000).repayment_months == 33     # 36 - 3
    assert quote(100_000).repayment_months == 78     # 84 - 6


def test_totals_add_up():
    q = quote(100_000)
    assert q.total_repayment == q.monthly_instalment * q.repayment_months
    assert q.total_interest == q.total_repayment - q.loan_amount
    assert q.total_interest > 0


def test_a_higher_rate_scheme_costs_more_per_rupee_borrowed_per_month():
    # Sanity on direction only: 8% over 78 months vs 6.5% over 33 months on the same-size loan.
    micro, term = quote(10_000), quote(100_000)
    assert 0 < micro.monthly_instalment / micro.loan_amount
    assert term.monthly_instalment / term.loan_amount < micro.monthly_instalment / micro.loan_amount


# ---- inputs ---------------------------------------------------------------
@pytest.mark.parametrize("bad", [0, -5, "abc", None, True, "", float("nan")])
def test_bad_amounts_raise(bad):
    with pytest.raises(ValueError):
        quote(bad)


def test_numeric_strings_and_floats_are_accepted():
    assert quote("100000").loan_amount == 900_000
    assert quote(100000.0).loan_amount == 900_000


def test_to_dict_is_json_ready_and_marked_indicative():
    import json
    d = quote(100_000).to_dict()
    json.dumps(d)
    assert d["indicative"] is True
    assert d["scheme"] == "Term Loan Scheme"
    assert quote(500_001).to_dict()["scheme"] is None


# ---- Indian digit grouping -------------------------------------------------
@pytest.mark.parametrize("n, text", [
    (0, "₹0"), (999, "₹999"), (1_000, "₹1,000"), (12_345, "₹12,345"),
    (100_000, "₹1,00,000"), (900_000, "₹9,00,000"),
    (4_500_000, "₹45,00,000"), (123_456_789, "₹12,34,56,789"), (-1_500, "-₹1,500"),
])
def test_format_inr(n, text):
    assert format_inr(n) == text
