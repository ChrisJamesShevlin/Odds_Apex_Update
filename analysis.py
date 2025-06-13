import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import re

# Liability caps per signal (as fraction of bankroll)
CAP_FACTORS = {
    "Strong": 0.10,   # 10%
    "Medium": 0.05,   #  5%
    "Weak":   0.025   # 2.5%
}

# Delta→signal thresholds
DELTA_THRESHOLDS = {
    "Strong": 5,
    "Medium": 3,
    "Weak":   1
}

def classify_delta(delta):
    """Map rank‐delta to a signal strength."""
    if delta >= DELTA_THRESHOLDS["Strong"]:
        return "Strong"
    if delta >= DELTA_THRESHOLDS["Medium"]:
        return "Medium"
    if delta >= DELTA_THRESHOLDS["Weak"]:
        return "Weak"
    return None

def calculate_lays():
    output_txt.delete("1.0", tk.END)
    lines = input_txt.get("1.0", tk.END).strip().splitlines()

    # Read bankroll
    try:
        bank = float(balance_entry.get())
        if bank <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Input Error", "Enter a positive bankroll.")
        return

    players = []
    for line in lines:
        if "|" not in line:
            continue
        name, stats = line.split("|", 1)
        name = name.strip()

        # Loosened Score regex: will match with or without a '%' suffix
        m_score  = re.search(r"Score[:%]?\s*([+-]?\d+(?:\.\d+)?)", stats)
        m_model  = re.search(r"Model[:%]?\s*([\d.]+)%",   stats)
        m_market = re.search(r"Market[:%]?\s*([\d.]+)%",  stats)
        m_live   = re.search(r"LiveOdds[:]?\s*([\d.]+(?:\.\d+)?)", stats)
        m_ev     = re.search(r"EV[:]?\s*([+-]?[0-9]+(?:\.[0-9]+)?)", stats)

        if not (m_score and m_model and m_market and m_live and m_ev):
            continue

        score    = float(m_score.group(1))
        model_p  = float(m_model.group(1))
        market_p = float(m_market.group(1))
        odds     = float(m_live.group(1))
        ev       = float(m_ev.group(1))

        players.append({
            "name":     name,
            "score":    score,
            "model_p":  model_p,
            "market_p": market_p,
            "odds":     odds,
            "ev":       ev,
            "edge":     model_p - market_p
        })

    if not players:
        output_txt.insert(tk.END, "No valid player data.\n")
        return

    # Rank by market odds (low→fav) and by model% (high→fav)
    by_mkt = sorted(players, key=lambda x: x["odds"])
    by_mod = sorted(players, key=lambda x: x["model_p"], reverse=True)

    # Assign ranks, compute delta & signal, then stakes
    for p in players:
        p["mkt_rank"] = by_mkt.index(p) + 1
        p["mod_rank"] = by_mod.index(p) + 1
        p["delta"]    = p["mod_rank"] - p["mkt_rank"]
        p["signal"]   = classify_delta(p["delta"]) if p["delta"] > 0 else None

        if p["signal"]:
            cap_liab       = CAP_FACTORS[p["signal"]] * bank
            p["liability"] = cap_liab
            p["stake"]     = cap_liab / (p["odds"] - 1)
        else:
            p["liability"] = None
            p["stake"]     = None

    # Build and print the table (EV column instead of AbsEV)
    header = "{:<12}{:>5}{:>5}{:>5}{:>5}{:>5}{:>7}{:>7}{:>7}{:>7}{:>8}{:>8}{:>8}\n".format(
        "Player", "Sc", "Md%", "Mk%", "MPos", "MkPos",
        "Δ", "Signal", "Odds", "Edge", "EV", "Stake", "Liab"
    )
    output_txt.insert(tk.END, header)
    output_txt.insert(tk.END, "-" * (len(header)-1) + "\n")

    for p in sorted(players, key=lambda x: x["delta"], reverse=True):
        stk = f"{p['stake']:.2f}"     if p["stake"]     is not None else ""
        lia = f"{p['liability']:.2f}" if p["liability"] is not None else ""
        line = "{:<12}{:>5.0f}{:>5.0f}{:>5.0f}{:>5d}{:>7d}{:>5d}{:>7}{:>7.2f}{:>7.2f}{:>8.2f}{:>8}{:>8}\n".format(
            p["name"],
            p["score"],
            p["model_p"],
            p["market_p"],
            p["mod_rank"],
            p["mkt_rank"],
            p["delta"],
            p["signal"] or "",
            p["odds"],
            p["edge"],
            p["ev"],     # signed EV
            stk,
            lia
        )
        output_txt.insert(tk.END, line)

# --- GUI Setup ---
root = tk.Tk()
root.title("Odds Apex - Golf Analysis")

FONT = ("Courier New", 11)

tk.Label(root, text="Paste model output below:", font=FONT)\
    .grid(row=0, column=0, padx=5, pady=5)
input_txt = ScrolledText(root, width=135, height=8, font=FONT)
input_txt.grid(row=1, column=0, columnspan=2)

tk.Label(root, text="Bankroll £:", font=FONT)\
    .grid(row=2, column=0, sticky="e", padx=5)
balance_entry = tk.Entry(root, width=10, font=FONT)
balance_entry.grid(row=2, column=1, sticky="w")

tk.Button(root, text="Calculate", command=calculate_lays, font=FONT)\
    .grid(row=3, column=0, columnspan=2, pady=8)

output_txt = ScrolledText(root, width=135, height=15, font=FONT)
output_txt.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

root.mainloop()
