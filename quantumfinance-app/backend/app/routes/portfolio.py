"""Paper trading: portfolios, positions, orders."""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yfinance as yf
import pandas as pd

from app.db.base import SessionLocal
from app.db.models import Portfolio, Position, Order


router = APIRouter(prefix="/api/portfolios", tags=["portfolio"])


class OrderRequest(BaseModel):
    ticker: str
    side: str  # BUY / SELL
    quantity: int


def _quote(ticker: str) -> float | None:
    try:
        df = yf.download(f"{ticker}.SA", period="5d", progress=False, auto_adjust=True)
        c = df["Close"]
        if isinstance(c, pd.DataFrame): c = c.iloc[:, 0]
        return float(c.iloc[-1])
    except Exception:
        return None


@router.get("")
def list_portfolios():
    db = SessionLocal()
    try:
        result = []
        for p in db.query(Portfolio).all():
            positions = db.query(Position).filter_by(portfolio_id=p.id).all()
            equity = p.cash_balance
            pos_data = []
            for pos in positions:
                price = _quote(pos.ticker) or pos.avg_price
                market_value = price * pos.quantity
                pnl = (price - pos.avg_price) * pos.quantity
                pnl_pct = ((price / pos.avg_price) - 1) * 100 if pos.avg_price else 0
                equity += market_value
                pos_data.append({
                    "ticker": pos.ticker, "quantity": pos.quantity,
                    "avg_price": pos.avg_price, "last_price": price,
                    "market_value": market_value, "pnl": pnl, "pnl_pct": pnl_pct,
                })
            total_pnl = equity - p.initial_balance
            total_pnl_pct = (total_pnl / p.initial_balance) * 100 if p.initial_balance else 0
            result.append({
                "id": p.id, "name": p.name,
                "cash": p.cash_balance, "equity": equity,
                "initial": p.initial_balance,
                "total_pnl": total_pnl, "total_pnl_pct": total_pnl_pct,
                "positions": pos_data,
            })
        return result
    finally:
        db.close()


@router.post("/{portfolio_id}/orders")
def place_order(portfolio_id: int, req: OrderRequest):
    db = SessionLocal()
    try:
        portfolio = db.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(404, "Portfolio not found")
        price = _quote(req.ticker)
        if price is None:
            raise HTTPException(400, f"No quote for {req.ticker}")
        side = req.side.upper()
        if side not in ("BUY", "SELL"):
            raise HTTPException(400, "side must be BUY or SELL")
        cost = price * req.quantity

        position = (db.query(Position)
                    .filter_by(portfolio_id=portfolio_id, ticker=req.ticker.upper())
                    .first())

        if side == "BUY":
            if portfolio.cash_balance < cost:
                raise HTTPException(400, f"Insufficient cash (need R${cost:.2f}, have R${portfolio.cash_balance:.2f})")
            portfolio.cash_balance -= cost
            if position:
                total_qty = position.quantity + req.quantity
                position.avg_price = (position.avg_price * position.quantity + cost) / total_qty
                position.quantity = total_qty
            else:
                db.add(Position(portfolio_id=portfolio_id, ticker=req.ticker.upper(),
                                quantity=req.quantity, avg_price=price))
        else:  # SELL
            if not position or position.quantity < req.quantity:
                raise HTTPException(400, "Insufficient position")
            position.quantity -= req.quantity
            portfolio.cash_balance += cost
            if position.quantity == 0:
                db.delete(position)

        order = Order(portfolio_id=portfolio_id, ticker=req.ticker.upper(),
                      side=side, quantity=req.quantity, price=price, status="executed")
        db.add(order); db.commit(); db.refresh(order)
        return {"id": order.id, "ticker": order.ticker, "side": order.side,
                "quantity": order.quantity, "price": order.price,
                "executed_at": order.executed_at.isoformat()}
    finally:
        db.close()


@router.get("/{portfolio_id}/orders")
def list_orders(portfolio_id: int):
    db = SessionLocal()
    try:
        orders = (db.query(Order).filter_by(portfolio_id=portfolio_id)
                    .order_by(Order.executed_at.desc()).limit(100).all())
        return [
            {"id": o.id, "ticker": o.ticker, "side": o.side,
             "quantity": o.quantity, "price": o.price,
             "executed_at": o.executed_at.isoformat()}
            for o in orders
        ]
    finally:
        db.close()
