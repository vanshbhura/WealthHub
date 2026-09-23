from datetime import datetime
from typing import List, Tuple, Optional
from app.domain.enums import AssetCategory, TransactionType
from app.connectors.dtos import (
    NormalizedAccount,
    NormalizedAsset,
    NormalizedHolding,
    NormalizedTransaction,
    NormalizedBalance,
    NormalizedPortfolio,
)
from app.connectors.account_aggregator.dtos import (
    SetuFinancialDataResponse,
    SetuBankAccount,
    SetuMutualFundHolding,
    SetuEquityHolding,
    SetuFixedDeposit,
    SetuNPSAccount,
)


class AAMapper:
    """
    Provider-independent mapper.
    Transforms Setu Account Aggregator DTOs into standard WealthHub NormalizedPortfolio.
    Ensures the domain layer never depends on provider-specific JSON or schemas.
    """

    @staticmethod
    def map_bank_account(
        bank: SetuBankAccount,
        data_source: str = "SANDBOX_MOCK",
    ) -> Tuple[NormalizedAccount, NormalizedHolding, List[NormalizedTransaction]]:
        """Maps a bank account, its cash holding, and transactions."""
        account_ref = bank.account_number_masked
        norm_account = NormalizedAccount(
            account_name=f"{bank.bank_name} ({bank.account_number_masked})",
            account_type=bank.account_type,
            masked_identifier=bank.account_number_masked,
            currency=bank.currency,
            current_value=bank.current_balance,
            invested_value=bank.current_balance,
            external_account_reference=account_ref,
            metadata={"fip_id": bank.fip_id, "data_source": data_source},
        )

        norm_asset = NormalizedAsset(
            name=f"{bank.bank_name} Savings Account",
            asset_type=AssetCategory.CASH.value,
            identifier=bank.account_number_masked,
            quantity=1.0,
            average_buy_price=bank.current_balance,
            invested_amount=bank.current_balance,
            current_price=bank.current_balance,
            current_value=bank.current_balance,
            currency=bank.currency,
            metadata={"fip_id": bank.fip_id, "data_source": data_source},
        )
        norm_holding = NormalizedHolding(asset=norm_asset, account_reference=account_ref)

        norm_txns = []
        for t in bank.transactions:
            txn_type = (
                TransactionType.DEPOSIT.value
                if t.type.upper() == "CREDIT"
                else TransactionType.WITHDRAWAL.value
            )
            norm_txns.append(
                NormalizedTransaction(
                    external_transaction_id=t.txn_id,
                    transaction_type=txn_type,
                    transaction_date=t.timestamp,
                    amount=t.amount,
                    asset_identifier=bank.account_number_masked,
                    transfer_id=None,
                    metadata={"narration": t.narration, "data_source": data_source},
                )
            )

        return norm_account, norm_holding, norm_txns

    @staticmethod
    def map_mutual_fund(
        mf: SetuMutualFundHolding,
        account_ref: Optional[str] = None,
        data_source: str = "SANDBOX_MOCK",
    ) -> NormalizedHolding:
        """Maps a Mutual Fund holding from CAS/AA into NormalizedHolding."""
        avg_price = (
            round(mf.invested_value / mf.units, 4)
            if mf.units > 0
            else 0.0
        )
        asset = NormalizedAsset(
            name=mf.scheme_name,
            asset_type=AssetCategory.MUTUAL_FUND.value,
            identifier=mf.isin,
            quantity=mf.units,
            average_buy_price=avg_price,
            invested_amount=mf.invested_value,
            current_price=mf.nav,
            current_value=mf.current_value,
            currency="INR",
            metadata={
                "amc": mf.amc,
                "folio_number": mf.folio_number,
                "nav_date": mf.nav_date.isoformat() if mf.nav_date else None,
                "data_source": data_source,
            },
        )
        return NormalizedHolding(asset=asset, account_reference=account_ref)

    @staticmethod
    def map_equity(
        eq: SetuEquityHolding,
        account_ref: Optional[str] = None,
        data_source: str = "SANDBOX_MOCK",
    ) -> NormalizedHolding:
        """Maps an Equity/Stock holding from CDSL/NSDL into NormalizedHolding."""
        invested = round(eq.quantity * eq.average_buy_price, 2)
        asset = NormalizedAsset(
            name=eq.company_name,
            asset_type=AssetCategory.STOCK.value,
            symbol=eq.symbol,
            identifier=eq.isin,
            quantity=eq.quantity,
            average_buy_price=eq.average_buy_price,
            invested_amount=invested,
            current_price=eq.current_price,
            current_value=eq.current_value,
            currency="INR",
            metadata={
                "depository": eq.depository,
                "demat_account": eq.demat_account,
                "data_source": data_source,
            },
        )
        return NormalizedHolding(asset=asset, account_reference=account_ref)

    @staticmethod
    def map_fixed_deposit(
        fd: SetuFixedDeposit,
        account_ref: Optional[str] = None,
        data_source: str = "SANDBOX_MOCK",
    ) -> NormalizedHolding:
        """Maps a Fixed Deposit into NormalizedHolding."""
        asset = NormalizedAsset(
            name=f"{fd.bank_name} Fixed Deposit ({fd.deposit_number_masked})",
            asset_type=AssetCategory.FD.value,
            identifier=fd.deposit_number_masked,
            quantity=1.0,
            average_buy_price=fd.principal_amount,
            invested_amount=fd.principal_amount,
            current_price=fd.current_value,
            current_value=fd.current_value,
            currency="INR",
            metadata={
                "interest_rate": fd.interest_rate,
                "tenure_months": fd.tenure_months,
                "maturity_date": fd.maturity_date.isoformat() if fd.maturity_date else None,
                "data_source": data_source,
            },
        )
        return NormalizedHolding(asset=asset, account_reference=account_ref)

    @staticmethod
    def map_nps(
        nps: SetuNPSAccount,
        account_ref: Optional[str] = None,
        data_source: str = "SANDBOX_MOCK",
    ) -> NormalizedHolding:
        """Maps an NPS account into NormalizedHolding."""
        asset = NormalizedAsset(
            name=f"NPS Tier-1 ({nps.pran_masked})",
            asset_type=AssetCategory.NPS.value,
            identifier=nps.pran_masked,
            quantity=1.0,
            average_buy_price=nps.total_contribution,
            invested_amount=nps.total_contribution,
            current_price=nps.current_value,
            current_value=nps.current_value,
            currency="INR",
            metadata={"tier": nps.tier, "data_source": data_source},
        )
        return NormalizedHolding(asset=asset, account_reference=account_ref)

    @classmethod
    def to_normalized_portfolio(cls, fi_data: SetuFinancialDataResponse) -> NormalizedPortfolio:
        """Transforms full Setu financial data into unified NormalizedPortfolio."""
        accounts: List[NormalizedAccount] = []
        holdings: List[NormalizedHolding] = []
        transactions: List[NormalizedTransaction] = []
        ds = fi_data.data_source or "SANDBOX_MOCK"

        # 1. Bank Accounts
        for bank in fi_data.bank_accounts:
            acc, holding, txns = cls.map_bank_account(bank, data_source=ds)
            accounts.append(acc)
            holdings.append(holding)
            transactions.extend(txns)

        # 2. Demat account container if equities exist
        demat_ref = None
        if fi_data.equities:
            demat_acc_num = fi_data.equities[0].demat_account
            depository = fi_data.equities[0].depository
            demat_ref = f"{depository}-{demat_acc_num}"
            total_eq_val = sum(eq.current_value for eq in fi_data.equities)
            total_eq_inv = sum(round(eq.quantity * eq.average_buy_price, 2) for eq in fi_data.equities)
            accounts.append(
                NormalizedAccount(
                    account_name=f"{depository} Demat ({demat_acc_num[-4:]})",
                    account_type="DEMAT",
                    masked_identifier=f"****{demat_acc_num[-4:]}",
                    currency="INR",
                    current_value=total_eq_val,
                    invested_value=total_eq_inv,
                    external_account_reference=demat_ref,
                    metadata={"depository": depository, "data_source": ds},
                )
            )

        # 3. Equities
        for eq in fi_data.equities:
            holdings.append(cls.map_equity(eq, account_ref=demat_ref, data_source=ds))

        # 4. Mutual Funds
        for mf in fi_data.mutual_funds:
            holdings.append(cls.map_mutual_fund(mf, data_source=ds))

        # 5. Fixed Deposits
        for fd in fi_data.fixed_deposits:
            holdings.append(cls.map_fixed_deposit(fd, data_source=ds))

        # 6. NPS Accounts
        for nps in fi_data.nps_accounts:
            holdings.append(cls.map_nps(nps, data_source=ds))

        # 7. Balances summary
        total_balance = sum(b.current_balance for b in fi_data.bank_accounts)
        balances = [
            NormalizedBalance(
                currency="INR",
                available_cash=total_balance,
                invested_amount=sum(h.asset.invested_amount for h in holdings if h.asset.asset_type != AssetCategory.CASH.value),
                total_balance=sum(h.asset.current_value for h in holdings),
                as_of=datetime.utcnow(),
            )
        ]

        return NormalizedPortfolio(
            accounts=accounts,
            holdings=holdings,
            transactions=transactions,
            balances=balances,
        )
