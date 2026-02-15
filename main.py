# main.py
from datetime import datetime, timedelta, timezone

import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CasaBourse YFinance API", version="0.1.0")

# السماح لـ Flutter بالوصول للـ API من أي دومين (يمكنك تضييقها لاحقًا)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_candles(yf_symbol: str, days: int):
    """جلب بيانات يومية من yfinance وتحويلها إلى شموع قياسية."""
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be > 0")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    df = yf.download(
        yf_symbol,
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        raise HTTPException(status_code=404, detail="No data for this ticker")

    # إزالة الصفوف الناقصة
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df.sort_index()

    candles = []
    for ts, row in df.iterrows():
        # تحويل التاريخ إلى ISO 8601 حتى يقرأه Dart بسهولة
        dt = ts.to_pydatetime().replace(tzinfo=timezone.utc)
        candles.append(
            {
                "time": dt.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row.get("Volume", 0) or 0),
            }
        )

    if not candles:
        raise HTTPException(status_code=404, detail="No candles parsed")

    return candles


@app.get("/")
def home():
    return {"message": "API بورصة الدار البيضاء تعمل بنجاح!"}


@app.get("/stock/{ticker}")
def get_stock(ticker: str, days: int = 365):
    """
    مثال:
    - /stock/MASI        → يستعمل رمز ^MASI في Yahoo
    - /stock/^GSPC      → أي رمز آخر كما هو
    - /stock/MASI?days=1095  → آخر 3 سنوات تقريبًا
    """
    t = ticker.strip()

    # تحويل MASI إلى الرمز المستعمل في Yahoo Finance إذا لزم الأمر
    if t.upper() == "MASI":
        yf_symbol = "^MASI"  # غيّره إذا استعملت رمزًا آخر في yfinance
    else:
        yf_symbol = t

    candles = _build_candles(yf_symbol, days)

    return {
        "ticker": t.upper(),
        "yf_symbol": yf_symbol,
        "source": "yfinance",
        "days": days,
        "count": len(candles),
        "candles": candles,
    }