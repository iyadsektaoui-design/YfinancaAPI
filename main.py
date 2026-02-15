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
@app.get("/{ticker}")
@app.get("/{ticker}")
def get_stock(ticker: str, days: int = 60):
    t = ticker.strip() # نتركها كما هي للتحقق من الرموز الحساسة
    upper_t = t.upper()
    
    # 1. إذا كان الرمز يبدأ بـ ^ (مثل ^IXIC أو ^MASI) نتركه كما هو تمامًا
    if t.startswith("^"):
        yf_symbol = t
    
    # 2. إذا كان المستخدم كتب MASI صراحة (بدون علامة ^)
    elif upper_t == "MASI":
        yf_symbol = "^MASI"
        
    # 3. إذا كان الرمز يحتوي بالفعل على نقطة (مثل IAM.MA أو MSFT)
    elif "." in t:
        yf_symbol = t
        
    # 4. إذا كان رمزًا عالميًا مشهورًا (قائمة بيضاء)
    elif upper_t in ["MSFT", "AAPL", "GOOGL", "TSLA", "NVDA"]:
        yf_symbol = upper_t
        
    # 5. أي حالة أخرى نعتبرها سهمًا مغربيًا ونضيف .MA
    else:
        yf_symbol = f"{upper_t}.MA"

    try:
        # استدعاء الدالة التي تتضمن سطر الـ Flattening (تسطيح الأعمدة)
        candles = _build_candles(yf_symbol, days)
        return {
            "ticker": upper_t,
            "yf_symbol": yf_symbol,
            "count": len(candles),
            "candles": candles
        }
    except Exception as e:
        # إرجاع تفاصيل الخطأ الحقيقية للمساعدة في التشخيص
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


