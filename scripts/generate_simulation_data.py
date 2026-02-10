#!/usr/bin/env python3
"""
Generate simulation data from history files.
Picks stocks with '적극매수' signal and creates mock trading simulation results.
"""

import json
import os
import re
import random
from datetime import datetime, timezone, timedelta

BASE_DIR = "/Users/sonbyeongcheol/DEV/signal_analysis"
RESULTS_DIR = os.path.join(BASE_DIR, "results")
SIMULATION_DIR = os.path.join(RESULTS_DIR, "simulation")
KST = timezone(timedelta(hours=9))

random.seed(42)  # reproducible results


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return None


def parse_price(value):
    """Parse price value that could be int, float, or string like '8,720원'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    if isinstance(value, str):
        # Remove commas, '원', whitespace
        cleaned = re.sub(r'[,원\s]', '', value)
        try:
            return int(float(cleaned)) if float(cleaned) > 0 else None
        except ValueError:
            return None
    return None


def get_current_price(stock, category):
    if category == "combined":
        api_data = stock.get("api_data", {})
        price_data = api_data.get("price", {})
        return parse_price(price_data.get("current"))
    else:
        return parse_price(stock.get("current_price"))


def get_market(stock, category):
    market = stock.get("market", "")
    if "코스피" in market or "KOSPI" in market.upper():
        return "KOSPI"
    elif "코스닥" in market or "KOSDAQ" in market.upper():
        return "KOSDAQ"
    return market if market else "KOSPI"


def generate_sim_prices(current_price):
    """Generate realistic open/close prices from current_price."""
    open_factor = random.uniform(0.97, 1.03)
    open_price = int(round(current_price * open_factor, -1))
    if open_price == 0:
        open_price = current_price

    # Slightly biased upward for 적극매수 stocks
    close_factor = random.uniform(0.97, 1.05)
    close_price = int(round(open_price * close_factor, -1))
    if close_price == 0:
        close_price = open_price

    if open_price == 0:
        return_pct = 0.0
    else:
        return_pct = round((close_price - open_price) / open_price * 100, 2)

    return open_price, close_price, return_pct


def extract_vision_stocks(history_entry):
    filename = history_entry["filename"]
    path = os.path.join(RESULTS_DIR, "vision", "history", filename)
    data = load_json(path)
    if not data:
        return []

    results = data.get("results", [])
    stocks = []
    for s in results:
        if s.get("signal") == "적극매수":
            price = get_current_price(s, "vision")
            if not price:
                continue
            open_p, close_p, ret = generate_sim_prices(price)
            stocks.append({
                "code": s.get("code", ""),
                "name": s.get("name", ""),
                "market": get_market(s, "vision"),
                "open_price": open_p,
                "close_price": close_p,
                "return_pct": ret,
            })
    return stocks


def extract_kis_stocks(history_entry):
    filename = history_entry["filename"]
    path = os.path.join(RESULTS_DIR, "kis", "history", filename)
    data = load_json(path)
    if not data:
        return []

    results = data.get("results", [])
    stocks = []
    for s in results:
        if s.get("signal") == "적극매수":
            price = get_current_price(s, "kis")
            if not price:
                continue
            open_p, close_p, ret = generate_sim_prices(price)
            stocks.append({
                "code": s.get("code", ""),
                "name": s.get("name", ""),
                "market": get_market(s, "kis"),
                "open_price": open_p,
                "close_price": close_p,
                "return_pct": ret,
            })
    return stocks


def extract_combined_stocks(history_entry):
    filename = history_entry["filename"]
    path = os.path.join(RESULTS_DIR, "combined", "history", filename)
    data = load_json(path)
    if not data:
        return []

    stock_list = data.get("stocks", [])
    stocks = []
    for s in stock_list:
        if s.get("match_status") == "match" and s.get("vision_signal") == "적극매수":
            price = get_current_price(s, "combined")
            if not price:
                continue
            open_p, close_p, ret = generate_sim_prices(price)
            stocks.append({
                "code": s.get("code", ""),
                "name": s.get("name", ""),
                "market": get_market(s, "combined"),
                "open_price": open_p,
                "close_price": close_p,
                "return_pct": ret,
            })
    return stocks


def main():
    os.makedirs(SIMULATION_DIR, exist_ok=True)

    vision_index = load_json(os.path.join(RESULTS_DIR, "vision", "history_index.json"))
    kis_index = load_json(os.path.join(RESULTS_DIR, "kis", "history_index.json"))
    combined_index = load_json(os.path.join(RESULTS_DIR, "combined", "history_index.json"))

    # Build date -> { category: latest_entry } map
    date_map = {}

    if vision_index:
        for entry in vision_index.get("history", []):
            d = entry["date"]
            if entry.get("total_stocks", 0) == 0:
                continue
            signals = entry.get("signals", {})
            if signals.get("적극매수", 0) == 0:
                continue
            if d not in date_map:
                date_map[d] = {}
            if "vision" not in date_map[d]:
                date_map[d]["vision"] = entry
            else:
                if entry.get("time", "") > date_map[d]["vision"].get("time", ""):
                    date_map[d]["vision"] = entry

    if kis_index:
        for entry in kis_index.get("history", []):
            d = entry["date"]
            if entry.get("total_stocks", 0) == 0:
                continue
            signals = entry.get("signals", {})
            if signals.get("적극매수", 0) == 0:
                continue
            if d not in date_map:
                date_map[d] = {}
            if "kis" not in date_map[d]:
                date_map[d]["kis"] = entry
            else:
                if entry.get("time", "") > date_map[d]["kis"].get("time", ""):
                    date_map[d]["kis"] = entry

    if combined_index:
        for entry in combined_index.get("history", []):
            d = entry["date"]
            if entry.get("match_count", 0) == 0:
                continue
            signals = entry.get("signals", {})
            if signals.get("적극매수", 0) == 0:
                continue
            if d not in date_map:
                date_map[d] = {}
            if "combined" not in date_map[d]:
                date_map[d]["combined"] = entry
            else:
                if entry.get("time", "") > date_map[d]["combined"].get("time", ""):
                    date_map[d]["combined"] = entry

    sorted_dates = sorted(date_map.keys(), reverse=True)

    print(f"Found {len(sorted_dates)} unique dates with 적극매수 signals:")
    for d in sorted_dates:
        cats = list(date_map[d].keys())
        print(f"  {d}: categories = {cats}")

    # Generate simulation files
    simulation_history = []
    total_sim_records = 0

    for date_str in sorted_dates:
        entries = date_map[date_str]
        categories = {}

        if "vision" in entries:
            vision_stocks = extract_vision_stocks(entries["vision"])
            if vision_stocks:
                categories["vision"] = vision_stocks
                print(f"\n  [{date_str}] Vision: {len(vision_stocks)} 적극매수 stocks")
                for s in vision_stocks[:3]:
                    print(f"    - {s['name']} ({s['code']}): open={s['open_price']:,} close={s['close_price']:,} ret={s['return_pct']}%")

        if "kis" in entries:
            kis_stocks = extract_kis_stocks(entries["kis"])
            if kis_stocks:
                categories["kis"] = kis_stocks
                print(f"  [{date_str}] KIS: {len(kis_stocks)} 적극매수 stocks")
                for s in kis_stocks[:3]:
                    print(f"    - {s['name']} ({s['code']}): open={s['open_price']:,} close={s['close_price']:,} ret={s['return_pct']}%")

        if "combined" in entries:
            combined_stocks = extract_combined_stocks(entries["combined"])
            if combined_stocks:
                categories["combined"] = combined_stocks
                print(f"  [{date_str}] Combined: {len(combined_stocks)} match+적극매수 stocks")
                for s in combined_stocks[:3]:
                    print(f"    - {s['name']} ({s['code']}): open={s['open_price']:,} close={s['close_price']:,} ret={s['return_pct']}%")

        if not categories:
            print(f"  [{date_str}] No stocks found after filtering, skipping.")
            continue

        collected_at = f"{date_str}T15:40:00+09:00"
        sim_data = {
            "date": date_str,
            "collected_at": collected_at,
            "categories": categories,
        }

        sim_filename = f"simulation_{date_str}.json"
        sim_path = os.path.join(SIMULATION_DIR, sim_filename)
        with open(sim_path, "w", encoding="utf-8") as f:
            json.dump(sim_data, f, ensure_ascii=False, indent=2)

        total_stocks = sum(len(v) for v in categories.values())
        category_counts = {k: len(v) for k, v in categories.items()}

        simulation_history.append({
            "date": date_str,
            "filename": sim_filename,
            "total_stocks": total_stocks,
            "category_counts": category_counts,
        })

        total_sim_records += 1
        print(f"  => Saved {sim_filename} ({total_stocks} stocks)")

    simulation_history.sort(key=lambda x: x["date"], reverse=True)

    now_kst = datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")
    index_data = {
        "updated_at": now_kst,
        "total_records": total_sim_records,
        "history": simulation_history,
    }

    index_path = os.path.join(SIMULATION_DIR, "simulation_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Simulation data generation complete!")
    print(f"  Total dates: {total_sim_records}")
    print(f"  Total stock entries: {sum(h['total_stocks'] for h in simulation_history)}")
    print(f"  Output directory: {SIMULATION_DIR}")
    print(f"  Index file: {index_path}")
    print(f"{'='*60}")

    print(f"\n{'Date':<14} {'Vision':>7} {'KIS':>5} {'Combined':>9} {'Total':>6}")
    print("-" * 45)
    for h in simulation_history:
        cc = h["category_counts"]
        print(f"{h['date']:<14} {cc.get('vision', 0):>7} {cc.get('kis', 0):>5} {cc.get('combined', 0):>9} {h['total_stocks']:>6}")


if __name__ == "__main__":
    main()
