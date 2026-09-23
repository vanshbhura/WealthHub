from datetime import datetime, date, timedelta
from typing import Optional
from app.connectors.account_aggregator.dtos import (
    SetuFinancialDataResponse,
    SetuBankAccount,
    SetuBankTransaction,
    SetuMutualFundHolding,
    SetuEquityHolding,
    SetuFixedDeposit,
    SetuNPSAccount,
)


class SetuSandboxDataGenerator:
    """
    Controlled sandbox data generator.
    Produces realistic, deterministic financial information simulating RBI-regulated
    Financial Information Providers (FIPs) in the Setu sandbox environment.
    All records explicitly specify data_source = 'SANDBOX'.
    """

    @staticmethod
    def generate_sandbox_portfolio(
        consent_id: str = "sandbox-consent-001",
        data_source: str = "SANDBOX_MOCK",
    ) -> SetuFinancialDataResponse:
        now = datetime.utcnow()
        today = date.today()

        # 1. Bank Account (Savings with HDFC Bank)
        bank_txns = [
            SetuBankTransaction(
                txn_id="TXN-SETU-SB-1001",
                type="CREDIT",
                amount=75000.0,
                narration="Salary Credit / TechCorp India",
                timestamp=now - timedelta(days=5),
                balance_after=82450.0,
            ),
            SetuBankTransaction(
                txn_id="TXN-SETU-SB-1002",
                type="DEBIT",
                amount=15200.0,
                narration="UPI / Groceries & Utilities",
                timestamp=now - timedelta(days=3),
                balance_after=67250.0,
            ),
            SetuBankTransaction(
                txn_id="TXN-SETU-SB-1003",
                type="DEBIT",
                amount=22000.0,
                narration="SIP Deduction / MF Investment",
                timestamp=now - timedelta(days=1),
                balance_after=45250.0,
            ),
        ]
        bank_account = SetuBankAccount(
            fip_id="FIP-HDFC-BANK",
            bank_name="HDFC Bank",
            account_number_masked="****7890",
            account_type="SAVINGS",
            current_balance=45250.0,
            currency="INR",
            transactions=bank_txns,
        )

        # 2. Mutual Funds (from CAS / Registrar FIP)
        mf_hdfc = SetuMutualFundHolding(
            amc="HDFC Mutual Fund",
            scheme_name="HDFC Top 100 Fund - Direct Plan Growth",
            isin="INF179K01BE2",
            folio_number="10482910/22",
            units=125.450,
            nav=945.20,
            nav_date=today - timedelta(days=1),
            invested_value=100000.0,
            current_value=round(125.450 * 945.20, 2),  # 118575.34
        )
        mf_ppfas = SetuMutualFundHolding(
            amc="PPFAS Mutual Fund",
            scheme_name="Parag Parikh Flexi Cap Fund - Direct Plan Growth",
            isin="INF879O01018",
            folio_number="98231045/88",
            units=310.250,
            nav=72.85,
            nav_date=today - timedelta(days=1),
            invested_value=20000.0,
            current_value=round(310.250 * 72.85, 2),  # 22601.71
        )

        # 3. Equities (from CDSL Depository Participant FIP)
        eq_reliance = SetuEquityHolding(
            isin="INE002A01018",
            company_name="Reliance Industries Limited",
            symbol="RELIANCE",
            demat_account="1208160000123456",
            depository="CDSL",
            quantity=25.0,
            average_buy_price=2750.0,
            current_price=2980.0,
            current_value=round(25.0 * 2980.0, 2),  # 74500.0
        )
        eq_tcs = SetuEquityHolding(
            isin="INE467B01029",
            company_name="Tata Consultancy Services Ltd",
            symbol="TCS",
            demat_account="1208160000123456",
            depository="CDSL",
            quantity=15.0,
            average_buy_price=3600.0,
            current_price=4120.0,
            current_value=round(15.0 * 4120.0, 2),  # 61800.0
        )

        # 4. Fixed Deposit (SBI Bank Term Deposit FIP)
        fd_sbi = SetuFixedDeposit(
            bank_name="State Bank of India",
            deposit_number_masked="****3344",
            principal_amount=100000.0,
            current_value=107200.0,
            interest_rate=7.1,
            maturity_date=today + timedelta(days=240),
            tenure_months=12,
        )

        # 5. National Pension Scheme (NPS / CRA FIP)
        nps_holding = SetuNPSAccount(
            pran_masked="****9988",
            tier="TIER_1",
            total_contribution=50000.0,
            current_value=58400.0,
        )

        return SetuFinancialDataResponse(
            consent_id=consent_id,
            data_source=data_source,
            bank_accounts=[bank_account],
            mutual_funds=[mf_hdfc, mf_ppfas],
            equities=[eq_reliance, eq_tcs],
            fixed_deposits=[fd_sbi],
            nps_accounts=[nps_holding],
        )
