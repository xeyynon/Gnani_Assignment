"""
loan_calculator.py

The arithmetic behind Udyami loan guidance (DEC-027, from SIH 2026
PS 26091). Pure functions, no I/O: the language model never does this
math, it only speaks what quote() returns.

The rules, as the problem statement gives them:
  - The caller's margin money is 10% of the project cost, so
    project cost = margin money / 0.10 and the loan is up to 90% of it.
  - Project cost up to Rs 1.40 lakh: Micro Finance Scheme, 6.5% a year,
    repaid over 3 years including a 3-month moratorium, loan capped at
    Rs 1.25 lakh.
  - Project cost above Rs 1.40 lakh, up to Rs 50 lakh: Term Loan Scheme,
    8% a year, repaid over 7 years including a 6-month moratorium, loan
    capped at Rs 45 lakh.
  - Above Rs 50 lakh: not covered.

The problem statement does NOT say how the instalment is worked out, so
these are ASSUMPTIONS (DEC-028), and every figure is indicative:
  - monthly reducing-balance instalments (an EMI), rate / 12 a month;
  - interest accrues during the moratorium and is added to the loan
    (capitalised), and repayment runs over the remaining months;
  - the instalment is rounded to the nearest rupee.
Replace them with the real scheme terms if those differ.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

LAKH = Decimal(100_000)
MARGIN_SHARE = Decimal("0.10")   # caller's share of the project cost
LOAN_SHARE = Decimal("0.90")     # most the agency lends
_RUPEE = Decimal(1)


@dataclass(frozen=True)
class Scheme:
    key: str
    name: str
    max_project_cost: Decimal   # inclusive upper bound of this scheme
    loan_cap: Decimal
    annual_rate_pct: Decimal
    tenure_months: int          # total, including the moratorium
    moratorium_months: int


MICRO_FINANCE = Scheme(
    key="micro", name="Micro Finance Scheme",
    max_project_cost=Decimal("1.40") * LAKH, loan_cap=Decimal("1.25") * LAKH,
    annual_rate_pct=Decimal("6.5"), tenure_months=36, moratorium_months=3,
)
TERM_LOAN = Scheme(
    key="term", name="Term Loan Scheme",
    max_project_cost=Decimal(50) * LAKH, loan_cap=Decimal(45) * LAKH,
    annual_rate_pct=Decimal(8), tenure_months=84, moratorium_months=6,
)
SCHEMES = (MICRO_FINANCE, TERM_LOAN)   # in ascending order of project cost


@dataclass(frozen=True)
class LoanQuote:
    margin_money: int
    project_cost: int
    scheme: Scheme | None          # None: above the Term Loan limit
    loan_amount: int | None
    own_contribution: int | None   # project cost - loan (>= margin money when a cap binds)
    monthly_instalment: int | None
    repayment_months: int | None   # months after the moratorium
    moratorium_months: int | None
    total_repayment: int | None
    total_interest: int | None

    @property
    def covered(self) -> bool:
        return self.scheme is not None

    def to_dict(self) -> dict:
        return {
            "margin_money": self.margin_money,
            "project_cost": self.project_cost,
            "covered": self.covered,
            "scheme": self.scheme.name if self.scheme else None,
            "annual_rate_pct": float(self.scheme.annual_rate_pct) if self.scheme else None,
            "loan_amount": self.loan_amount,
            "own_contribution": self.own_contribution,
            "monthly_instalment": self.monthly_instalment,
            "repayment_months": self.repayment_months,
            "moratorium_months": self.moratorium_months,
            "total_repayment": self.total_repayment,
            "total_interest": self.total_interest,
            "indicative": True,
        }


def _to_decimal(value) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("margin money must be a number")
    try:
        d = Decimal(str(value))
    except Exception as e:
        raise ValueError(f"margin money must be a number, got {value!r}") from e
    if not d.is_finite():   # "nan" and "inf" parse as Decimals but are not amounts
        raise ValueError(f"margin money must be a number, got {value!r}")
    return d


def _round_rupee(x: Decimal) -> int:
    return int(x.quantize(_RUPEE, rounding=ROUND_HALF_UP))


def scheme_for(project_cost: Decimal) -> Scheme | None:
    for scheme in SCHEMES:
        if project_cost <= scheme.max_project_cost:
            return scheme
    return None


def monthly_instalment(loan: Decimal, scheme: Scheme) -> Decimal:
    """
    EMI under the assumptions in the module docstring: capitalise the
    interest over the moratorium, then amortise over what's left.
    """
    r = scheme.annual_rate_pct / Decimal(100) / Decimal(12)
    n = scheme.tenure_months - scheme.moratorium_months
    grown = loan * (1 + r) ** scheme.moratorium_months
    return grown * r / (1 - (1 + r) ** -n)


def quote(margin_money) -> LoanQuote:
    """
    Quote for a caller who can put in `margin_money` rupees. Raises
    ValueError for a missing, non-numeric or non-positive amount, so the
    caller of this function can ask again instead of speaking nonsense.
    """
    margin = _to_decimal(margin_money)
    if margin <= 0:
        raise ValueError("margin money must be more than zero")

    cost = margin / MARGIN_SHARE
    scheme = scheme_for(cost)
    if scheme is None:
        return LoanQuote(
            margin_money=_round_rupee(margin), project_cost=_round_rupee(cost),
            scheme=None, loan_amount=None, own_contribution=None,
            monthly_instalment=None, repayment_months=None, moratorium_months=None,
            total_repayment=None, total_interest=None,
        )

    loan = min(cost * LOAN_SHARE, scheme.loan_cap)
    emi = _round_rupee(monthly_instalment(loan, scheme))
    months = scheme.tenure_months - scheme.moratorium_months
    loan_int = _round_rupee(loan)
    total = emi * months
    return LoanQuote(
        margin_money=_round_rupee(margin), project_cost=_round_rupee(cost),
        scheme=scheme, loan_amount=loan_int,
        own_contribution=_round_rupee(cost) - loan_int,
        monthly_instalment=emi, repayment_months=months,
        moratorium_months=scheme.moratorium_months,
        total_repayment=total, total_interest=total - loan_int,
    )


def format_inr(amount: int) -> str:
    """Rs 9,00,000 style (lakh grouping), e.g. 900000 -> '₹9,00,000'."""
    n = int(amount)
    sign = "-" if n < 0 else ""
    digits = str(abs(n))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return f"{sign}₹{digits}"
