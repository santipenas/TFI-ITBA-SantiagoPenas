---
name: technical-setup-strategy
description: Procedimiento operativo estándar (SOP) para el análisis técnico de activos bursátiles, identificación de tendencia, momentum y cálculo de niveles de soporte, resistencia y stop-loss sugeridos.
version: 1.0.0
---

# Procedimiento Operativo Estándar: Estrategia de Configuración Técnica (Technical Setup Strategy)

Este documento define las reglas de dominio financiero para el **Analista de Mercado** al evaluar gráficos y formular hipótesis comerciales.

## 1. Identificación de Tendencia y Régimen de Mercado
Para determinar el sesgo direccional de un activo (Long, Short o Neutral), se evalúa la alineación de medias móviles simples (SMA):
- **Tendencia Alcista Fuerte (Bullish Bias)**:
  - Precio actual > SMA(20) > SMA(50) > SMA(200).
  - Solo se buscan oportunidades de compra (Long).
- **Tendencia Bajista Fuerte (Bearish Bias)**:
  - Precio actual < SMA(20) < SMA(50) < SMA(200).
  - Solo se buscan oportunidades de venta corta (Short) o abstenerse de operar.
- **Régimen Lateral / Rango (Neutral / Chop)**:
  - Medias móviles cruzadas o planas. El analista debe recomendar cautela o abstenerse si no hay catalizadores claros.

## 2. Filtro de Momentum (RSI 14 periodos)
- **Sobrecompra Extrema (RSI > 70)**: Prohibido abrir posiciones Long a mercado. Se requiere esperar un retroceso o confirmar ruptura sostenida.
- **Sobreventa Extrema (RSI < 30)**: Prohibido abrir posiciones Short a mercado.
- **Zona Óptima de Entrada en Tendencia**:
  - Para Long: RSI entre 40 y 60 rebotando al alza.
  - Para Short: RSI entre 40 y 60 girando a la baja.

## 3. Determinación de Niveles Técnicos de Stop-Loss y Take-Profit
El analista no inventa números aleatorios; debe utilizar volatilidad técnica real:
- **Distancia de Stop-Loss**:
  - Basada en el Indicador de Rango Verdadero Promedio: $\text{Distancia SL} = 1.5 \times \text{ATR}(14)$.
  - Para Long: $\text{Stop-Loss} = \text{Precio Entrada} - (1.5 \times \text{ATR})$.
  - Para Short: $\text{Stop-Loss} = \text{Precio Entrada} + (1.5 \times \text{ATR})$.
- **Nivel de Take-Profit (Objetivo Mínimo)**:
  - La distancia mínima al Take-Profit debe garantizar una relación Riesgo-Beneficio de al menos $1.5 : 1$:
  - $\text{Distancia TP} \ge 1.5 \times \text{Distancia SL}$.
  - Para Long: $\text{Take-Profit} = \text{Precio Entrada} + (1.5 \times \text{Distancia SL})$.
  - Para Short: $\text{Take-Profit} = \text{Precio Entrada} - (1.5 \times \text{Distancia SL})$.
