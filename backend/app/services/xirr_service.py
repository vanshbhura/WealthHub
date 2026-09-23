from datetime import date, datetime
from typing import List, Tuple, Optional, Union


class XirrService:
    @staticmethod
    def calculate_xirr(
        cash_flows: List[Tuple[Union[date, datetime, str], float]],
        guess: float = 0.1,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Optional[float]:
        """
        Calculates the Extended Internal Rate of Return (XIRR) for irregular cash flows.
        
        Cash flows format: List of (date, amount)
        - Investments/Deposits are NEGATIVE
        - Withdrawals/Current Terminal Portfolio Value are POSITIVE

        Returns:
            Annualized percentage return (e.g. 15.4 for 15.4%), or None if non-convergent / invalid.
        """
        if not cash_flows or len(cash_flows) < 2:
            return None

        # Parse and sort cash flows by date
        parsed_flows: List[Tuple[date, float]] = []
        for d, amt in cash_flows:
            if amt is None:
                continue
            amt_flt = float(amt)
            if abs(amt_flt) < 1e-9:
                continue

            dt: date
            if isinstance(d, str):
                dt = datetime.fromisoformat(d.replace("Z", "+00:00")).date()
            elif isinstance(d, datetime):
                dt = d.date()
            elif isinstance(d, date):
                dt = d
            else:
                continue
            parsed_flows.append((dt, amt_flt))

        if len(parsed_flows) < 2:
            return None

        # Sort chronologically
        parsed_flows.sort(key=lambda x: x[0])

        # Must have at least one positive and one negative cash flow
        has_positive = any(cf[1] > 0 for cf in parsed_flows)
        has_negative = any(cf[1] < 0 for cf in parsed_flows)
        if not (has_positive and has_negative):
            return None

        d0 = parsed_flows[0][0]
        # Days from initial flow
        dated_flows = [((dt - d0).days, amt) for dt, amt in parsed_flows]

        # Total timespan must be at least 1 day
        if dated_flows[-1][0] <= 0:
            return None

        def npv(rate: float) -> float:
            if rate <= -1.0:
                return float("inf")
            total = 0.0
            for days, amt in dated_flows:
                total += amt * ((1.0 + rate) ** (-days / 365.0))
            return total

        def npv_derivative(rate: float) -> float:
            if rate <= -1.0:
                return float("inf")
            total = 0.0
            for days, amt in dated_flows:
                if days == 0:
                    continue
                exponent = -days / 365.0
                total += exponent * amt * ((1.0 + rate) ** (exponent - 1.0))
            return total

        # Attempt Newton-Raphson iteration
        r = guess
        for _ in range(max_iterations):
            f_val = npv(r)
            f_prime = npv_derivative(r)

            if abs(f_prime) < 1e-12:
                break

            r_next = r - f_val / f_prime

            # If rate steps into invalid territory, abort Newton and try Bisection
            if r_next <= -0.999 or r_next > 50.0:
                break

            if abs(r_next - r) < tolerance and abs(f_val) < 1e-4:
                return round(r_next * 100.0, 2)

            r = r_next

        # Fallback to Bisection method if Newton-Raphson did not converge
        low = -0.99
        high = 10.0  # up to 1000% return
        f_low = npv(low)
        f_high = npv(high)

        if f_low * f_high > 0:
            # Try wider bounds
            for test_high in [20.0, 50.0, 100.0]:
                f_high = npv(test_high)
                if f_low * f_high <= 0:
                    high = test_high
                    break
            else:
                return None

        for _ in range(120):
            mid = (low + high) / 2.0
            f_mid = npv(mid)

            if abs(f_mid) < 1e-4 or (high - low) / 2.0 < tolerance:
                return round(mid * 100.0, 2)

            if f_low * f_mid < 0:
                high = mid
                f_high = f_mid
            else:
                low = mid
                f_low = f_mid

        return None
