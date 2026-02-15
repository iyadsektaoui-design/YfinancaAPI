import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from pandas import MultiIndex
from datetime import datetime, timedelta, timezone

app = FastAPI()

import requests

def _build_candles(yf_symbol: str, days: int):
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be > 0")

    # 1. إنشاء جلسة وهمية تظهر كأنها متصفح Chrome عادي
    # هذا السطر ضروري جداً لبورصة المغرب
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    })

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days + 15) # زيادة الهامش لتجنب العطلات

    # 2. نمرر الجلسة (session) إلى yfinance
    ticker_obj = yf.Ticker(yf_symbol, session=session)
    
    # 3. نستخدم history بدلاً من download لأنها أكثر توافقاً مع الجلسات
    df = ticker_obj.history(
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        interval="1d"
    )

    # تسطيح الأعمدة (Flattening)
    if isinstance(df.columns, MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 4. محاولة بديلة إذا كانت البيانات فارغة (خاص بالمازي)
    if df.empty:
        df = ticker_obj.history(period="1mo")
        if isinstance(df.columns, MultiIndex):
            df.columns = df.columns.get_level_values(0)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {yf_symbol}")

    # ترتيب البيانات وتحويلها لـ JSON
    df = df.sort_index()
    candles = []
    for ts, row in df.iterrows():
        candles.append({
            "time": ts.strftime('%Y-%m-%d'),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row.get("Volume", 0) or 0),
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



