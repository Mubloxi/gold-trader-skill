"""Quotes and completed candles from the user's local desktop MT5 terminal."""
from datetime import datetime, timedelta
from importlib import import_module
import re

from .core import Bar, Feed, FRAMES, MT5_GOLD, UTC, iso, num
from .providers import ProviderError

MT5_FRAMES = {"1m":"M1","5m":"M5","15m":"M15","30m":"M30","1h":"H1"}
SOURCE = "https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py"

def read_mt5(symbol, frame, count=600, terminal=None, *, api=None, clock=lambda: datetime.now(UTC)):
    if frame not in MT5_FRAMES or not 32 <= count <= 5000:
        raise ProviderError("MT5 requires a supported timeframe and 32–5000 candles")
    if not re.fullmatch(r"[A-Za-z0-9._+/#-]{1,48}", symbol):
        raise ProviderError("invalid MT5 symbol; use its exact Market Watch name")
    if terminal is not None and not terminal.is_file():
        raise ProviderError("MT5 terminal path must point to your installed terminal executable")
    if api is None:
        try:
            api = import_module("MetaTrader5")
        except ImportError:
            raise ProviderError("MT5 needs local 64-bit Windows Python: py -3 -m pip install MetaTrader5") from None
    try:
        if not api.initialize(*([str(terminal)] if terminal else []), timeout=10000):
            raise ProviderError("could not attach to MT5; open the terminal and sign in there")
        info = api.terminal_info()
        if info is None or not info.connected:
            raise ProviderError("MT5 terminal is disconnected; verify the broker connection")
        account = api.account_info()
        account_mode = ("demo" if account is not None and account.trade_mode == getattr(api,"ACCOUNT_TRADE_MODE_DEMO",0) else
                        "contest" if account is not None and account.trade_mode == getattr(api,"ACCOUNT_TRADE_MODE_CONTEST",1) else
                        "real" if account is not None and account.trade_mode == getattr(api,"ACCOUNT_TRADE_MODE_REAL",2) else "unknown")
        spec = api.symbol_info(symbol)
        if spec is None:
            raise ProviderError("symbol not found; use the exact gold symbol from Market Watch")
        if spec.currency_base.upper() != "XAU" or spec.currency_profit.upper() != "USD" or spec.expiration_time:
            raise ProviderError("symbol metadata does not describe non-expiring XAU/USD; futures are not accepted")
        basis = {0:"bid",1:"last"}.get(spec.chart_mode,"unknown")
        raw = api.copy_rates_from_pos(symbol, getattr(api,"TIMEFRAME_"+MT5_FRAMES[frame]), 1, count)
        tick = api.symbol_info_tick(symbol)
        pulled = clock()
        if raw is None or len(raw) == 0:
            raise ProviderError("no completed candles returned; show the symbol and open its chart in MT5")
        bars = []
        for row in raw:
            close = datetime.fromtimestamp(int(row["time"]), UTC) + timedelta(minutes=FRAMES[frame])
            if close > pulled:
                raise ProviderError("MT5 returned a completed bar with a future time; verify the clock and chart")
            bars.append(Bar(close, *(num(row[k]) for k in ("open","high","low","close"))))
        quote = None
        if tick is not None:
            try:
                bid, ask = num(tick.bid), num(tick.ask)
                t = datetime.fromtimestamp(tick.time_msc / 1000, UTC)
                if 0 < bid <= ask and 0 < tick.time_msc and t <= pulled:
                    quote = {"bid":bid,"ask":ask,"spread_usd_per_oz":ask-bid,"at":iso(t)}
            except (AttributeError, TypeError, ValueError, OverflowError, OSError):
                # The candle snapshot is still useful without a valid tick.
                pass
        return Feed(bars,frame,SOURCE,pulled,MT5_GOLD,basis,"broker terminal data; quote latency not guaranteed",
                    market_meta={"provider":"MetaTrader 5","account_mode":account_mode,"broker_symbol":symbol,"chart_price_basis":basis,
                                 "requested_bars":count,"returned_bars":len(bars),"last_quote":quote})
    except ProviderError:
        raise
    except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError, OverflowError):
        raise ProviderError("MT5 returned an invalid payload or an IPC error; check the terminal, symbol and clock") from None
    finally:
        api.shutdown()
