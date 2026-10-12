---
name: risk-management-framework
description: Marco determinista y procedimental para la gestión de riesgo, preservación de capital, dimensionamiento de posición (position sizing) y validación de órdenes previas a la aprobación humana.
version: 1.0.0
---

# Procedimiento Operativo Estándar: Marco de Gestión de Riesgo (Risk Management Framework)

Este marco establece los límites no negociables y las fórmulas matemáticas para el **Risk Gatekeeper** y el servicio determinista `RiskPolicyService`.

## 1. La Regla de Riesgo Máximo por Operación (Regla del 2%)
El riesgo en dólares ($\text{Riesgo \$}$) es la pérdida potencial si el activo alcanza el Stop-Loss:
$$\text{Riesgo \$} = |\text{Precio Entrada} - \text{Stop-Loss}| \times \text{Cantidad}$$

- En ningún caso el $\text{Riesgo \$}$ puede exceder el porcentaje autorizado del capital neto total ($\text{Equity}$):
  - Perfil Conservador: $\le 1.0\% \text{ del Equity}$
  - Perfil Moderado (Default): $\le 2.0\% \text{ del Equity}$
  - Perfil Agresivo: $\le 3.0\% \text{ del Equity}$

## 2. Fórmula de Dimensionamiento de Posición (Position Sizing)
La cantidad máxima de acciones a operar se calcula de forma inversa según la distancia al Stop-Loss:
$$\text{Cantidad Máxima} = \left\lfloor \frac{\text{Equity} \times \text{Riesgo Máximo \%}}{|\text{Precio Entrada} - \text{Stop-Loss}|} \right\rfloor$$

Si la cantidad calculada es menor a 1 acción, la orden queda **rechazada** por falta de capital suficiente para soportar la volatilidad del activo.

## 3. Límite de Exposición Total por Activo (Concentración Máxima)
- El valor nominal total de la posición ($\text{Precio Entrada} \times \text{Cantidad}$) no puede superar el **$10\%$ del Equity total de la cuenta**, independientemente de la cercanía del Stop-Loss.
- Esto previene el riesgo de liquidez y saltos de precio (gaps de apertura).

## 4. Reglas Duras de Validación (Invariantes de Seguridad)
1. **Stop-Loss Obligatorio**: Si una propuesta no define un precio de Stop-Loss válido, se rechaza de inmediato.
2. **Distancia Mínima de Stop-Loss**: El Stop-Loss debe estar a una distancia de al menos $0.5\%$ del precio de entrada para evitar ejecuciones instantáneas por spread.
3. **Poder de Compra Real**: Para posiciones Long, el costo total de la orden ($\text{Precio} \times \text{Cantidad}$) no puede superar el $95\%$ del saldo de efectivo disponible (`cash`).
4. **Límite de Órdenes Pendientes**: No se pueden tener más de 3 órdenes simultáneas pendientes de ejecución en Alpaca.
