"""Servicio determinista de validación de reglas de riesgo y dimensionamiento de posición."""

from math import floor
from src.contracts.trade_schemas import TradeProposalDraft, RiskCheckResult
from src.contracts.models import AccountSummary
from src.utils.logger import get_logger

logger = get_logger("services.risk_policy")


class RiskPolicyService:
    """Motor determinista de control de riesgo y cumplimiento de políticas (SOP)."""

    def __init__(
        self,
        default_max_risk_pct: float = 0.02,     # 2% máximo por trade
        max_position_equity_pct: float = 0.10,  # 10% máximo por activo (concentración)
        min_sl_distance_pct: float = 0.005,     # 0.5% distancia mínima al SL
        min_risk_reward_ratio: float = 1.5,     # Ratio 1.5:1 mínimo
    ):
        self.default_max_risk_pct = default_max_risk_pct
        self.max_position_equity_pct = max_position_equity_pct
        self.min_sl_distance_pct = min_sl_distance_pct
        self.min_risk_reward_ratio = min_risk_reward_ratio

    def evaluate_proposal(
        self,
        draft: TradeProposalDraft,
        account: AccountSummary,
        risk_profile: str = "MODERATE",
    ) -> RiskCheckResult:
        """Evalúa un borrador de propuesta contra el saldo de la cuenta y reglas duras.

        Args:
            draft: Borrador de la propuesta de trade con niveles de entrada, SL y TP.
            account: Estado actual de la cuenta en Alpaca Paper Trading.
            risk_profile: Perfil del usuario ('CONSERVATIVE', 'MODERATE', 'AGGRESSIVE').

        Returns:
            RiskCheckResult con la decisión final y la cantidad de acciones autorizada.
        """
        rejection_reasons: list[str] = []

        # 0. Verificar si la cuenta de trading está bloqueada
        if account.is_trading_blocked:
            rejection_reasons.append("La cuenta de corretaje se encuentra bloqueada para operar.")
            return RiskCheckResult(
                is_approved=False,
                rejection_reasons=rejection_reasons,
            )

        # 1. Determinar el porcentaje de riesgo según el perfil
        risk_pct = self.default_max_risk_pct
        if risk_profile.upper() == "CONSERVATIVE":
            risk_pct = 0.01
        elif risk_profile.upper() == "AGGRESSIVE":
            risk_pct = 0.03

        equity = account.equity
        cash = account.cash

        if equity <= 0:
            rejection_reasons.append("El capital total de la cuenta es insuficiente o cero.")
            return RiskCheckResult(
                is_approved=False,
                rejection_reasons=rejection_reasons,
            )

        entry_price = draft.limit_price if (draft.order_type == "limit" and draft.limit_price) else draft.suggested_entry_price
        sl_price = draft.suggested_stop_loss
        tp_price = draft.suggested_take_profit

        sl_distance = abs(entry_price - sl_price)
        tp_distance = abs(tp_price - entry_price)

        # 2. Validación de Distancia Mínima de Stop-Loss (0.5%)
        sl_pct = sl_distance / entry_price
        if sl_pct < self.min_sl_distance_pct:
            rejection_reasons.append(
                f"La distancia del Stop-Loss ({sl_pct:.2%}) es menor al mínimo de seguridad requerido ({self.min_sl_distance_pct:.2%})."
            )

        # 3. Validación de Ratio Riesgo / Beneficio (mínimo 1.5:1)
        if sl_distance > 0:
            rr_ratio = tp_distance / sl_distance
            if rr_ratio < self.min_risk_reward_ratio:
                rejection_reasons.append(
                    f"La relación Riesgo/Beneficio ({rr_ratio:.2f}) es menor al mínimo establecido ({self.min_risk_reward_ratio:.2f}:1)."
                )
        else:
            rejection_reasons.append("La distancia al Stop-Loss no puede ser cero.")

        # 4. Cálculo de Position Sizing (Fórmula del 2%)
        # Cantidad = (Equity * risk_pct) / sl_distance
        max_allowed_risk_usd = equity * risk_pct
        calculated_qty = 0
        if sl_distance > 0:
            calculated_qty = floor(max_allowed_risk_usd / sl_distance)

        if calculated_qty < 1:
            rejection_reasons.append(
                f"El capital disponible no permite comprar al menos 1 acción respetando el riesgo máximo de ${max_allowed_risk_usd:.2f} USD."
            )

        # 5. Límite de Exposición Máxima por Activo (10% del Equity)
        max_position_value_usd = equity * self.max_position_equity_pct
        nominal_value = calculated_qty * entry_price

        # Ajuste a la baja si excede el 10%
        if nominal_value > max_position_value_usd:
            adjusted_qty = floor(max_position_value_usd / entry_price)
            if adjusted_qty < calculated_qty:
                calculated_qty = adjusted_qty
                nominal_value = calculated_qty * entry_price

        if calculated_qty < 1:
            rejection_reasons.append(
                f"La exposición máxima del 10% (${max_position_value_usd:.2f} USD) no alcanza para 1 acción de ${entry_price:.2f} USD."
            )

        # 6. Validación de Poder de Compra / Liquidez en Cash (Posiciones Long)
        if draft.side == "BUY":
            required_cash = nominal_value * 1.01  # Margen de seguridad del 1% para comisiones/spread
            if required_cash > cash:
                # Intentar reducir cantidad para ajustarse al efectivo disponible
                max_affordable_qty = floor((cash * 0.95) / entry_price)
                if max_affordable_qty < calculated_qty:
                    calculated_qty = max_affordable_qty
                    nominal_value = calculated_qty * entry_price

                if calculated_qty < 1:
                    rejection_reasons.append(
                        f"Efectivo disponible insuficiente (${cash:.2f} USD) para fondear la operación."
                    )

        # 7. Decisión Final
        is_approved = len(rejection_reasons) == 0 and calculated_qty >= 1
        final_risk_usd = (calculated_qty * sl_distance) if is_approved else 0.0
        final_risk_pct = (final_risk_usd / equity * 100) if equity > 0 else 0.0
        final_position_pct = (nominal_value / equity * 100) if equity > 0 else 0.0

        return RiskCheckResult(
            is_approved=is_approved,
            adjusted_qty=calculated_qty if is_approved else 0,
            max_risk_amount_usd=round(final_risk_usd, 2),
            risk_percentage_equity=round(final_risk_pct, 2),
            position_value_usd=round(nominal_value, 2) if is_approved else 0.0,
            position_percentage_equity=round(final_position_pct, 2) if is_approved else 0.0,
            rejection_reasons=rejection_reasons,
        )
