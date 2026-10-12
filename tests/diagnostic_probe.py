"""Script de diagnóstico en vivo para verificar la validez y conectividad de todas las API Keys en .env."""

import os

from dotenv import load_dotenv

load_dotenv(".env", override=True)

print("=" * 60)
print("  DIAGNÓSTICO EN VIVO DE CREDENCIALES Y APIS (.env)")
print("=" * 60)

# 1. OPENAI
openai_key = os.getenv("OPENAI_API_KEY")
print("\n[1/8] OpenAI LLM:")
if openai_key:
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key, timeout=15)
        resp = llm.invoke("Responde solo 'OK'")
        print(f"  -> Conectado exitosamente. Respuesta: {resp.content.strip()}")
    except Exception as e:
        print(f"  -> ERROR de conexión con OpenAI: {e}")
else:
    print("  -> Clave no encontrada en .env")

# 2. GOOGLE GEMINI
gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
print("\n[2/8] Google Gemini LLM:")
if gemini_key:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=gemini_key, timeout=15)
        resp = gemini.invoke("Responde solo 'OK'")
        print(f"  -> Conectado exitosamente. Respuesta: {resp.content.strip()}")
    except Exception as e:
        print(f"  -> ERROR de conexión con Gemini: {e}")
else:
    print("  -> Clave no encontrada en .env")

# 3. ALPACA PAPER TRADING
alpaca_key = os.getenv("ALPACA_API_KEY")
alpaca_secret = os.getenv("ALPACA_SECRET_KEY")
print("\n[3/8] Alpaca Paper Trading Broker:")
print(f"  -> ALPACA_API_KEY presente: {bool(alpaca_key)} ({alpaca_key[:6]}... si existe)")
print(f"  -> ALPACA_SECRET_KEY presente: {bool(alpaca_secret)}")
if alpaca_key and alpaca_secret:
    try:
        from alpaca.trading.client import TradingClient

        client = TradingClient(api_key=alpaca_key, secret_key=alpaca_secret, paper=True)
        acc = client.get_account()
        print(f"  -> Conexión exitosa. Saldo Equity: ${acc.equity} USD | Cash: ${acc.cash} USD | Estado: {acc.status}")
    except Exception as e:
        print(f"  -> ERROR de conexión con Alpaca: {e}")
else:
    print("  -> ATENCIÓN: Falta ALPACA_SECRET_KEY en .env. Alpaca requiere tanto API Key como Secret Key.")

# 4. TAVILY SEARCH
tavily_key = os.getenv("TAVILY_API_KEY") or os.getenv("TAVILI_API_KEY")
print("\n[4/8] Tavily Search API:")
if tavily_key:
    try:
        from tavily import TavilyClient

        tav = TavilyClient(api_key=tavily_key)
        res = tav.search(query="Apple earnings", max_results=1)
        titles = [r.get("title") for r in res.get("results", [])]
        print(f"  -> Conectado exitosamente. Resultado de prueba: {titles}")
    except Exception as e:
        print(f"  -> ERROR de conexión con Tavily: {e}")
else:
    print("  -> Clave no encontrada en .env")

# 5. FINANCIAL MODELING PREP (FMP)
fmp_key = os.getenv("FMP_API_KEY")
print("\n[5/8] Financial Modeling Prep (FMP):")
if fmp_key:
    try:
        import requests

        url = f"https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={fmp_key}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.json():
            data = r.json()[0]
            print(f"  -> Conectado exitosamente. Perfil AAPL: {data.get('companyName')} (Precio: ${data.get('price')})")
        else:
            print(f"  -> Status code: {r.status_code}, Respuesta: {r.text[:150]}")
    except Exception as e:
        print(f"  -> ERROR de conexión con FMP: {e}")
else:
    print("  -> Clave no encontrada en .env")

# 6. YAHOO FINANCE & PANDAS-TA (Local)
print("\n[6/8] Yahoo Finance & pandas-ta (Mercado y Análisis Técnico Local):")
try:
    import pandas_ta as ta
    import yfinance as yf

    df = yf.download("AAPL", period="30d", interval="1d", progress=False, auto_adjust=True)
    if isinstance(df.columns, type(df.columns)) and hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    rsi = ta.rsi(df["close"], length=14)
    last_rsi = round(float(rsi.iloc[-1]), 2)
    last_close = round(float(df["close"].iloc[-1]), 2)
    print(f"  -> Descarga y cálculo local exitoso. AAPL Close: ${last_close} | RSI(14): {last_rsi}")
except Exception as e:
    print(f"  -> ERROR en Yahoo Finance / pandas-ta: {e}")

# 7. FRED
fred_key = os.getenv("FRED_API_KEY")
print("\n[7/8] FRED (Federal Reserve Economic Data):")
if fred_key:
    try:
        import requests

        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={fred_key}&file_type=json"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            obs = r.json().get("observations", [])[-1]
            print(f"  -> Conectado exitosamente. Bono 10Y (DGS10): {obs.get('value')}% (Fecha: {obs.get('date')})")
        else:
            print(f"  -> Status code: {r.status_code}, Respuesta: {r.text[:150]}")
    except Exception as e:
        print(f"  -> ERROR en FRED: {e}")
else:
    print("  -> Clave no encontrada en .env")

# 8. FINNHUB
finnhub_key = os.getenv("FINNHUB_API_KEY")
print("\n[8/8] Finnhub Stock API:")
if finnhub_key:
    try:
        import requests

        url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={finnhub_key}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"  -> Conectado exitosamente. AAPL Quote Finnhub: ${data.get('c')} USD")
        else:
            print(f"  -> Status code: {r.status_code}, Respuesta: {r.text[:150]}")
    except Exception as e:
        print(f"  -> ERROR en Finnhub: {e}")
else:
    print("  -> Clave no encontrada en .env")

print("\n" + "=" * 60)
print("  FIN DEL DIAGNÓSTICO EN VIVO")
print("=" * 60)
