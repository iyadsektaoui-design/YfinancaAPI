import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from pandas import MultiIndex
from datetime import datetime, timedelta, timezone

app = FastAPI()

def _build_candles(yf_symbol: str, days: int):
    # 1. إعداد التاريخ
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days + 10)

    # 2. جلب البيانات باستخدام Ticker بدلاً من download مباشرة (أكثر استقراراً)
    ticker_obj = yf.Ticker(yf_symbol)
    
    # محاولة جلب البيانات التاريخية
    df = ticker_obj.history(
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        interval="1d"
    )

    # 3. معالجة مشكلة الـ MultiIndex (التسطيح)
    if isinstance(df.columns, MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 4. إذا كانت البيانات فارغة (مشكلة MASI الشائعة)
    if df.empty:
        # محاولة أخيرة باستخدام period بدلاً من التواريخ الصارمة
        df = ticker_obj.history(period="1mo")
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {yf_symbol} on Yahoo Finance")
        
        if isinstance(df.columns, MultiIndex):
            df.columns = df.columns.get_level_values(0)

    # 5. تنظيف وتجهيز البيانات
    df = df.sort_index()
    candles = []
    for ts, row in df.iterrows():
        candles.append({
            "time": ts.strftime('%Y-%m-%d'),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row.get("Volume", 0))
        })
    return candles

@app.get("/{ticker}")
def get_stock(ticker: str, days: int = 30):
    t = ticker.strip().upper()
    
    # تصحيح رمز المازي
    if t == "MASI":
        yf_symbol = "MASI.CAS" # جرب هذا الرمز الجديد أو ^MASI
    elif not t.endswith(".MA") and t not in ["MSFT", "AAPL"]:
        yf_symbol = f"{t}.MA"
    else:
        yf_symbol = t

    try:
        candles = _build_candles(yf_symbol, days)
        return {"ticker": t, "yf_symbol": yf_symbol, "candles": candles}
    except Exception as e:
        # إذا فشل MASI.CAS جرب ^MASI تلقائياً
        if t == "MASI":
             candles = _build_candles("^MASI", days)
             return {"ticker": t, "yf_symbol": "^MASI", "candles": candles}
        raise e
