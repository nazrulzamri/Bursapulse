"""BursaPulse OSINT - Streamlit edition.
Run:  pip install -r requirements.txt  &&  streamlit run app.py
Prices/volume (and Brent, USD/MYR) are live from Yahoo Finance when available; everything else
(29B filings, forum chatter, announcements, CPO, vessel index) is simulated. Replace the sim_* /
fetch_* functions in the DATA LAYER with real collectors when you have them."""
import hashlib, random
import numpy as np, pandas as pd, plotly.graph_objects as go, streamlit as st
try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config("BursaPulse OSINT", "📡", layout="wide")
N = 60
K = ("c", "name", "tier", "g", "sec", "price", "v", "sc", "dr", "tx", "sp")  # price = placeholder latest close, v = avg vol ('000)
UNIV = [dict(zip(K, t)) for t in [
    ("1155", "Maybank", "Large", "fin", "Financial", 10.1, 6000, "", .0006, (3, .6), (.3, .2)),
    ("5141", "Dayang Enterprise", "Large", "og", "O&G Services", 2.9, 2500, "contra", -.004, (5, 1), (.1, .65)),
    ("0166", "Inari Amertron", "Large", "fx", "Tech / Semicon", 2.7, 9000, "pump", .001, (0, 0), (.3, .1)),
    ("1961", "IOI Corporation", "Large", "cpo", "Plantation", 4.0, 2200, "", .0012, (2, .5), (.35, .2)),
    ("7113", "Top Glove", "Large", "fx", "Healthcare / Export", .95, 12000, "", -.001, (2, .3), (.2, .35)),
    ("5199", "Hibiscus Petroleum", "Mid", "og", "O&G E&P", 2.1, 5000, "", .001, (3, .7), (.35, .2)),
    ("7160", "Pentamaster", "Mid", "fx", "Tech / Automation", 4.4, 1800, "break", .0015, (4, .9), (.5, .12)),
    ("5012", "Ta Ann Holdings", "Mid", "cpo", "Plantation / Timber", 3.9, 600, "", .001, (2, .6), (.3, .25)),
    ("7293", "Yinson Holdings", "Mid", "og", "O&G / FPSO", 3.1, 4500, "", .001, (3, .7), (.4, .2)),
    ("0151", "Kelington Group", "Mid", "fx", "Semicon Engineering", 2.3, 3500, "", .0012, (2, .6), (.4, .2)),
    ("0128", "Frontken", "Mid", "fx", "Semicon Services", 3.3, 4000, "break", .0015, (4, .9), (.5, .12)),
    ("5263", "Sunway Construction", "Mid", "fin", "Construction", 3.2, 2500, "", .0008, (2, .5), (.35, .2)),
    ("5138", "Hap Seng Plantations", "Mid", "cpo", "Plantation", 2.2, 800, "", .0012, (3, .7), (.4, .2)),
    ("2089", "United Plantations", "Mid", "cpo", "Plantation", 24, 150, "", .0008, (2, .5), (.3, .25)),
    ("5243", "Velesto Energy", "Low", "og", "O&G Services", .25, 40000, "break", .001, (4, .9), (.5, .12)),
    ("0138", "MY E.G. Services", "Low", "fx", "Tech / Services", .8, 25000, "pump", .002, (0, 0), (.3, .1)),
    ("4383", "Jaya Tiasa", "Low", "cpo", "Plantation / Timber", .905, 15000, "contra", -.004, (3, 1), (.1, .6)),
    ("5210", "Bumi Armada", "Low", "og", "O&G / FPSO", .335, 30000, "", .0008, (3, .6), (.3, .3)),
    ("5255", "Lianson Fleet Group (LFG)", "Low", "og", "O&G Services", .85, 8000, "break", .001, (4, .9), (.5, .12)),
    ("0090", "Elsoft Research", "Low", "fx", "Semicon Equipment", .6, 5000, "contra", -.004, (3, 1), (.1, .6)),
    ("9059", "TSH Resources", "Low", "cpo", "Plantation", 1.0, 3000, "", .001, (2, .5), (.3, .25)),
    ("5171", "Kimlun Corp", "Low", "fin", "Construction", 1.1, 1500, "", .0005, (1, .5), (.3, .3)),
    ("0104", "Genetec Technology", "Low", "fx", "Automation", .9, 2000, "pump", .002, (0, 0), (.3, .1)),
    ("0208", "Greatech Technology", "Mid", "fx", "Automation / Tech", 2.4, 6000, "", .0015, (2, .6), (.4, .2)),
    ("0097", "ViTrox", "Large", "fx", "Semicon / ATE", 8.0, 4500, "", .0015, (2, .6), (.4, .2)),
    ("5132", "Deleum", "Low", "og", "O&G Services", 1.09, 250, "", .0008, (2, .5), (.3, .25)),
    ("7108", "Perdana Petroleum", "Low", "og", "O&G Services (OSV)", .17, 2500, "", .0008, (2, .5), (.3, .3))]]
SRC = ["i3investor", "Telegram", "StockBiz", "X/Twitter"]
WHO = ["Dato' Sri A. Rahman (Director)", "Tan Sri L. Kok (Director)", "KWAP (Substantial SH)", "EPF (Substantial SH)",
       "Puan N. Aminah (Director)", "Amanah Saham (Substantial SH)"]
TPL = {"bull": ["{n} breakout soon, volume mula naik, bullish", "Strong results expected, accumulate {n} on dips", "{n} undervalued, support kukuh, beli"],
       "bear": ["{n} weak, bearish chart, dah trapped", "Jual {n} sebelum turun lagi, loss makin besar", "{n} overvalued, expect selloff, dump"],
       "neu": ["Anyone following {n} this week?", "{n} AGM next month, tunggu result", "Watching {n} support level"],
       "pump": ["{n} to the moon! TP RM{tp}, buy now, jom load up", "Insider confirm {n} rocket tomorrow, don't miss, target RM{tp}", "{n} jom jom load up, confirm naik, buy now"]}
POS = ["naik", "untung", "bullish", "strong", "breakout", "accumulate", "beli", "buy", "support", "rally", "growth", "undervalued", "kukuh"]
NEG = ["turun", "rugi", "bearish", "weak", "dump", "sell", "jual", "loss", "overvalued", "trapped", "selloff"]
PW = ["moon", "rocket", "tp", "jom", "load up", "insider confirm", "buy now", "don't miss"]
FEED = [("29B", "Changes in Substantial Shareholder's Interest"), ("Corp", "Proposed Share Buy-Back"), ("Fin", "Quarterly Report - Unaudited"),
        ("UMA", "Query Regarding Unusual Market Activity"), ("Corp", "Change in Boardroom"), ("Corp", "Dividend Entitlement")]
clamp = lambda x, a=0, b=100: max(a, min(b, x))

# ===================== DATA LAYER =====================
def rng(key, seed):
    return np.random.default_rng(int(hashlib.md5(f"{key}{seed}".encode()).hexdigest()[:8], 16))

def sim_prices(u, seed):
    R = rng(u["c"], seed); p = 1.0; px, vol = [], []
    for i in range(N):
        f = bool(u["sc"]) and i > 30
        p *= 1 + (0 if f else u["dr"]) + R.uniform(-1, 1) * (.004 if f else .013); px.append(p)
        v = u["v"] * R.uniform(.7, 1.3)
        if u["sc"] == "pump" and i >= N - 2: v *= 3.4
        if u["sc"] == "contra" and i == N - 1: v *= 1.7
        if u["sc"] == "break":
            if 30 <= i < N - 12: v *= .7
            elif i >= N - 12: v *= 1 + (i - (N - 13)) * .05
        vol.append(v)
    px = np.array(px) * (u["price"] / px[-1])
    return pd.DataFrame({"px": px, "vol": vol}, index=pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=N))

@st.cache_data(ttl=900, show_spinner="Fetching Bursa prices...")
def live_prices(codes):
    out = {}
    if yf is None: return out
    try:
        raw = yf.download([f"{c}.KL" for c in codes], period="6mo", interval="1d", group_by="ticker", progress=False, auto_adjust=False, threads=True)
        for c in codes:
            try:
                d = raw[f"{c}.KL"][["Close", "Volume"]].dropna().tail(N)
                if len(d) >= N: out[c] = pd.DataFrame({"px": d.Close.values.astype(float), "vol": d.Volume.values / 1000.0}, index=d.index)
            except Exception: pass
    except Exception: pass
    for c in codes:  # retry any counter the bulk download missed, one by one
        if c in out: continue
        try:
            d = yf.Ticker(f"{c}.KL").history(period="6mo", interval="1d", auto_adjust=False)[["Close", "Volume"]].dropna().tail(N)
            if len(d) >= N: out[c] = pd.DataFrame({"px": d.Close.values.astype(float), "vol": d.Volume.values / 1000.0}, index=d.index.tz_localize(None))
        except Exception: pass
    return out

def macro(live, seed):
    R = rng("macro", seed)
    def walk(s, d, v):
        a = []
        for _ in range(N): s *= 1 + d + R.uniform(-1, 1) * v; a.append(s)
        return np.array(a)
    m = {"cpo": walk(4100, .0035, .012), "brent": walk(84, -.0012, .014), "fx": walk(4.45, .0006, .003), "ves": walk(100, .003, .01)}
    src = {k: "Simulated" for k in m}
    if live and yf:  # CPO futures (FCPO) and vessel activity have no free feed: plug in your own source here
        for k, sym in (("brent", "BZ=F"), ("fx", "MYR=X")):
            try:
                s = yf.download(sym, period="6mo", progress=False, auto_adjust=False)["Close"].squeeze().dropna().tail(N).values
                if len(s) >= N: m[k] = s.astype(float); src[k] = "Live (Yahoo)"
            except Exception: pass
    return m, src

def sim_tx(u, px, vol, seed):  # TODO: replace with Bursa LINK 29B / director dealings scraper
    R = rng(u["c"] + "tx", seed); n, pb = u["tx"]; sc = min(max(vol.mean() / 6000, .3), 8); rows, fil = [], []
    for _ in range(n):
        d = N - 1 - int(R.uniform(0, 18)); buy = R.random() < pb
        rows.append(dict(d=d, who=WHO[int(R.integers(len(WHO)))], side="B" if buy else "S", vol=round(R.uniform(150, 900) * sc),
                         px=round(px[d] * R.uniform(.985, 1.01), 3), mk=px[d])); fil.append(d)
    if u["sc"] != "pump": fil += [N - 1 - int(R.uniform(0, 25)) for _ in range(3)]
    return pd.DataFrame(rows, columns=["d", "who", "side", "vol", "px", "mk"]).sort_values("d", ascending=False), fil

def score_text(t):
    t = t.lower(); p = sum(w in t for w in POS); n = sum(w in t for w in NEG)
    return (p - n) / max(1, p + n), sum(w in t for w in PW) >= 2

def sim_posts(u, seed):  # TODO: replace with compliant collectors for i3investor / Telegram / StockBiz / X
    R = rng(u["c"] + "p", seed); bull, bear = u["sp"]; rows = []
    for d in range(N - 14, N):
        for s in SRC:
            c = round(R.uniform(1, 4)); pm = u["sc"] == "pump" and d >= N - 2
            if pm: c *= 4
            for _ in range(c):
                r = R.random(); k = "pump" if pm and r < .8 else "bull" if r < bull else "bear" if r < bull + bear else "neu"
                txt = TPL[k][int(R.integers(3))].format(n=u["name"], tp=f'{u["price"] * R.uniform(1.3, 1.8):.2f}')
                sc, pw = score_text(txt); rows.append(dict(d=d, src=s, txt=txt, s=sc, pump=pw))
    return pd.DataFrame(rows)

# ===================== ANALYSIS =====================
def analyze(px, vol, tx, posts, fil, g, mac):
    r20 = px[-20:]; avgv = vol.mean()
    net = int(sum(r.vol if r.side == "B" else -r.vol for r in tx.itertuples() if r.d >= N - 20))
    rg = (r20.max() - r20.min()) / r20.min() * 100; consol = rg < 7
    base = vol[:-1]; vz = (vol[-1] - base.mean()) / (base.std() or 1)
    p7 = posts[posts.d >= N - 7]; sent = round(p7.s.mean() * 100) if len(p7) else 0
    cat = np.where(p7.pump, "pump", np.where(p7.s > .25, "bull", np.where(p7.s < -.25, "bear", "neu")))
    cnt = {k: int((cat == k).sum()) for k in ["bull", "bear", "pump", "neu"]}
    daily = np.array([(posts.d == N - 14 + i).sum() for i in range(14)]); b = daily[:12]
    pz = (max(daily[12], daily[13]) - b.mean()) / max(1, b.std())
    pump = pz > 2 and not any(d >= N - 7 for d in fil); contra = sent < -25 and net > 0; accum = net > 0 and consol
    chg = lambda a: (a[-1] / a[-21] - 1) * 100
    m = {"cpo": chg(mac["cpo"]) * 4, "og": (chg(mac["brent"]) + chg(mac["ves"])) / 2 * 3, "fx": chg(mac["fx"]) * 15, "fin": 0}[g]; macS = clamp(50 + m)
    ins = clamp(50 + net / avgv * 100); sen = 90 if contra else clamp(50 + sent * .3); vo = clamp(vz * 25 + 30)
    score = round(.35 * ins + .25 * sen + .2 * vo + .2 * macS); score = clamp(score - 20) if pump else score
    res, lo = r20.max(), r20.min(); vr = vol[-5:].mean() / vol[-25:-5].mean()
    sq, vb, prox = clamp((10 - rg) * 12), clamp((vr - .9) * 150), clamp(100 - (res - px[-1]) / res * 2000)
    mom = round(.25 * sq + .25 * vb + .2 * ins + .15 * prox + .15 * macS)
    if pump: mom = min(mom, 30)
    if sent < -40 and not contra: mom = min(mom, 50)
    prev = px[-21:-1]; rs, sp = prev.max(), prev.min(); dist = (rs - px[-1]) / rs * 100; brk = "none"
    if not pump:
        if px[-1] > rs: brk = "Breakout (volume-confirmed)" if vr >= 1.2 else "Breakout (weak volume)"
        elif dist <= 2 and vr >= 1.1: brk = "About to break"
        elif dist <= 4: brk = "Approaching"
    why = []
    if pump: vd = "Avoid"; why = ["hype spike with no filing"]
    else:
        if brk == "About to break": why.append("testing resistance on rising volume")
        if mom >= 70: why.append("tight range + rising volume")
        if contra: why.append("insiders buying into fear")
        if accum: why.append("insiders accumulating")
        if score >= 70: why.append("strong overall signal")
        vd = "Consider" if (mom >= 70 or contra or score >= 70 or brk == "About to break") else "Watch" if (score >= 50 or mom >= 55) else "Skip"
    return dict(net=net, rg=rg, consol=consol, vz=vz, sent=sent, cnt=cnt, daily=daily, pz=pz, pump=pump, contra=contra, accum=accum, score=score,
                mom=mom, res=res, lo=lo, vr=vr, rs=rs, sp=sp, rs2=px[:-1].max(), sp2=px.min(), dist=dist, brk=brk, vd=vd, why=", ".join(why) or "no clear edge")

@st.cache_data(ttl=900, show_spinner=False)
def build(live, seed):
    lp = live_prices([u["c"] for u in UNIV]) if live else {}
    mac, msrc = macro(live, seed); out = []
    for u in UNIV:
        df = lp.get(u["c"]); src = "Live" if df is not None else "Simulated"
        if df is None: df = sim_prices(u, seed)
        px, vol = df.px.values.astype(float), df.vol.values.astype(float)
        tx, fil = sim_tx(u, px, vol, seed); posts = sim_posts(u, seed)
        out.append({**u, "df": df, "px": px, "vol": vol, "tx": tx, "posts": posts, "src": src, "a": analyze(px, vol, tx, posts, fil, u["g"], mac)})
    return out, mac, msrc

# ===================== UI =====================
with st.sidebar:
    st.title("📡 BursaPulse OSINT")
    live = st.toggle("Live prices (Yahoo Finance)", True)
    seed = st.number_input("Simulation seed", 0, 999999, 2026)
    if st.button("Refresh data"): st.cache_data.clear(); st.rerun()
    tier = st.radio("Tier", ["All", "Large", "Mid", "Low"], horizontal=True)
data, mac, msrc = build(live, int(seed)); by = {u["c"]: u for u in data}
vis = [u for u in data if tier == "All" or u["tier"] == tier]
with st.sidebar:
    sel = st.selectbox("Counter", [u["c"] for u in data], format_func=lambda c: f'{c}.KL {by[c]["name"]} ({by[c]["tier"]})')
    nl = sum(u["src"] == "Live" for u in data)
    st.caption(f"{nl}/{len(data)} counters on live prices; the rest are simulated. Insider, chatter and announcements are always simulated.")
    miss = [f'{u["c"]} {u["name"]}' for u in data if u["src"] != "Live"]
    if live and miss: st.warning("No live price for: " + ", ".join(miss) + ". Could be a delisting, code or name change, or a Yahoo limit. Check your screener.")
    if live and yf is None: st.warning("yfinance not installed: run pip install yfinance")

def flags(a):
    return " | ".join(x for x in [a["brk"] if a["brk"] in ("About to break",) else "", "Pre-breakout momentum" if a["mom"] >= 70 else "",
                                  "Contrarian Buy" if a["contra"] else "", "Insider accumulation" if a["accum"] else "", "Volume spike" if a["vz"] > 2 else "",
                                  "Suspected pump-and-dump" if a["pump"] else ""] if x) or "-"
CFG = {"Signal": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"), "Momentum": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d")}
@st.fragment(run_every=8)
def feed():
    f = st.session_state.setdefault("feed", []); u = random.choice(UNIV); k = random.choice(FEED)
    f.insert(0, (pd.Timestamp.now().strftime("%H:%M:%S"), u["c"], k)); del f[12:]
    for t, c, k in f: st.markdown(f"`{t}` **{k[0]}** {c}.KL {k[1]}")

tabs = st.tabs(["Dashboard", "Insider (29B)", "Sentiment", "Macro matrix", "Compliance"])
with tabs[0]:
    for u in vis:
        a = u["a"]
        if a["contra"]: st.success(f'**Contrarian Buy Setup: {u["name"]}**. Retail sentiment {a["sent"]}, insiders net buying {a["net"]}K shares.')
        if a["pump"]: st.error(f'**Suspected pump-and-dump: {u["name"]}**. Forum posts spiked {a["pz"]:.1f}σ with no filing in 7 days.')
    RK = {"About to break": 0, "Breakout (volume-confirmed)": 1, "Breakout (weak volume)": 2, "Approaching": 3}
    sw = sorted([u for u in vis if u["a"]["brk"] != "none"], key=lambda u: (RK[u["a"]["brk"]], u["a"]["dist"]))
    st.subheader(f"Resistance sweep: {len(vis)} counters scanned")
    st.caption("Resistance = highest close of the prior 20 sessions; support = lowest. About to break = within 2% below resistance with volume pace ≥ 1.1x. Pump-flagged counters excluded. False breakouts are common: wait for a close above and keep a stop below support.")
    st.dataframe(pd.DataFrame([{"Counter": f'{u["c"]}.KL {u["name"]}', "Tier": u["tier"], "Status": u["a"]["brk"], "Close": round(u["px"][-1], 3),
        "Resistance": round(u["a"]["rs"], 3), "To go": f'{abs(u["a"]["dist"]):.2f}% {"below" if u["a"]["dist"] > 0 else "above"}', "Vol pace": f'{u["a"]["vr"]:.2f}x',
        "Support (stop)": round(u["a"]["sp"], 3), "Verdict": u["a"]["vd"]} for u in sw]), hide_index=True, width="stretch")
    st.subheader("Momentum radar: possible breakouts before they strike")
    hot = sorted([u for u in vis if u["a"]["mom"] >= 70], key=lambda u: -u["a"]["mom"])
    for u in hot:
        a = u["a"]; st.info(f'**{u["c"]}.KL {u["name"]}** ({u["tier"]} cap) momentum **{a["mom"]}**: {a["rg"]:.1f}% 20-day range, volume {a["vr"]:.2f}x prior pace, '
                            f'{"insiders net buying, " if a["net"] > 0 else ""}near RM{a["res"]:.3f}. Trigger: close above RM{a["res"]:.3f} on rising volume. Invalidation: close below RM{a["lo"]:.3f}.')
    if not hot: st.caption("No counter is pre-breakout right now.")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("Watchlist")
        rk = lambda u: -(u["a"]["score"] + u["a"]["mom"] - (100 if u["a"]["pump"] else 0))
        st.dataframe(pd.DataFrame([{"Counter": f'{u["c"]}.KL {u["name"]}', "Tier": u["tier"], "Verdict": u["a"]["vd"], "Why": u["a"]["why"], "Price": round(u["px"][-1], 3),
            "Day %": round((u["px"][-1] / u["px"][-2] - 1) * 100, 2), "Signal": u["a"]["score"], "Momentum": u["a"]["mom"], "Vol σ": round(u["a"]["vz"], 1),
            "Flags": flags(u["a"]), "Data": u["src"]} for u in sorted(vis, key=rk)]), hide_index=True, width="stretch", column_config=CFG)
        st.caption("Signal = 35% insider flow + 25% sentiment/divergence + 20% volume anomaly + 20% macro, minus 20 on a pump-and-dump flag.")
    with c2:
        st.subheader("Announcements (simulated)"); feed()
    u = by[sel]; fig = go.Figure(go.Bar(x=u["df"].index, y=u["vol"], marker_color=["#d9822b" if i == N - 1 and u["a"]["vz"] > 2 else "#5b8fc4" for i in range(N)]))
    fig.update_layout(title=f'{u["name"]} volume (\'000 shares)', height=280, margin=dict(t=40, b=10)); st.plotly_chart(fig, width="stretch")

u = by[sel]; a = u["a"]; df = u["df"]
with tabs[1]:
    st.subheader(f'{u["c"]}.KL {u["name"]}: director & substantial shareholder dealings')
    m1, m2, m3 = st.columns(3); m1.metric("20-day net insider flow", f'{a["net"]:+,}K'); m2.metric("20-day range", f'{a["rg"]:.1f}%', "consolidating" if a["consol"] else "trending", delta_color="off")
    m3.metric("Breakout status", "range-bound" if a["brk"] == "none" else a["brk"])
    if a["accum"]: st.info("Insider accumulation during consolidation")
    st.caption(f'Support RM{a["sp"]:.3f} (20d) / RM{a["sp2"]:.3f} (60d) · Resistance RM{a["rs"]:.3f} (20d) / RM{a["rs2"]:.3f} (60d)')
    fig = go.Figure(go.Scatter(x=df.index, y=u["px"], name="Close", line=dict(color="#1f5f99")))
    fig.add_hline(y=a["rs"], line_dash="dash", line_color="#d4442e", annotation_text="Resistance"); fig.add_hline(y=a["sp"], line_dash="dash", line_color="#0f9a5f", annotation_text="Support")
    for s, sym, colr, nm in (("B", "triangle-up", "#0f9a5f", "Insider buy"), ("S", "triangle-down", "#d4442e", "Insider sell")):
        t = u["tx"][u["tx"].side == s]
        fig.add_trace(go.Scatter(x=df.index[t.d.values], y=t.px, mode="markers", name=nm, marker=dict(symbol=sym, size=13, color=colr)))
    fig.update_layout(height=380, margin=dict(t=20)); st.plotly_chart(fig, width="stretch")
    t = u["tx"]; st.dataframe(pd.DataFrame({"Date": df.index[t.d.values].date, "Insider": t.who.values, "Side": t.side.map({"B": "Buy", "S": "Sell"}).values, "Vol (K)": t.vol.values,
        "Txn px": t.px.values, "Market px": t.mk.round(3).values, "vs market %": ((t.px / t.mk - 1) * 100).round(2).values}), hide_index=True, width="stretch")
    nf = go.Figure(go.Bar(x=[x["c"] for x in data], y=[x["a"]["net"] for x in data], marker_color=["#0f9a5f" if x["a"]["net"] >= 0 else "#d4442e" for x in data]))
    nf.update_layout(title="Net insider flow, all counters (K shares)", height=260, margin=dict(t=40)); st.plotly_chart(nf, width="stretch")
with tabs[2]:
    p = u["posts"]; p7 = p[p.d >= N - 7]; st.subheader(f'{u["name"]} retail sentiment (7d)')
    if a["contra"]: st.success(f'**Sentiment divergence: Contrarian Buy Setup.** Sentiment {a["sent"]} while insiders are net buyers. Watch signal only: confirm with price action and fundamentals.')
    if a["pump"]: st.error(f'**Pump-and-dump risk.** Daily posts hit {a["pz"]:.1f}σ above the 12-day norm with no 29B or announcement in 7 days.')
    k1, k2, k3 = st.columns(3); k1.metric("Score (-100..+100)", a["sent"]); k2.metric("Posts (7d)", len(p7)); k3.metric("Bull / Bear / Pump", f'{a["cnt"]["bull"]} / {a["cnt"]["bear"]} / {a["cnt"]["pump"]}')
    g1, g2 = st.columns(2)
    g1.plotly_chart(go.Figure(go.Pie(labels=["Bullish", "Bearish", "Pump risk", "Neutral"], values=[a["cnt"][k] for k in ("bull", "bear", "pump", "neu")], hole=.55,
        marker_colors=["#0f9a5f", "#d4442e", "#a86a00", "#8a8f98"])).update_layout(height=280, margin=dict(t=10)), width="stretch")
    g2.plotly_chart(go.Figure(go.Bar(x=df.index[-14:], y=a["daily"], marker_color=["#d4442e" if i >= 12 and a["pump"] else "#5b8fc4" for i in range(14)])).update_layout(
        title="Posts per day", height=280, margin=dict(t=40)), width="stretch")
    st.dataframe(p7.groupby("src").agg(Posts=("s", "size"), Avg_score=("s", lambda s: round(s.mean() * 100))).reset_index().rename(columns={"src": "Source"}), hide_index=True)
    for r in p.tail(10).iloc[::-1].itertuples():
        lab = "Pump risk" if r.pump else "Bullish" if r.s > .25 else "Bearish" if r.s < -.25 else "Neutral"
        st.markdown(f"**{lab}** · {r.src} · {df.index[r.d].strftime('%d %b')}  \n{r.txt}")
with tabs[3]:
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=N); cols = st.columns(2)
    for i, (k, nm, g) in enumerate([("cpo", "CPO spot (RM/tonne)", "cpo"), ("brent", "Brent crude (USD/bbl)", "og"), ("ves", "Offshore vessel activity index", "og"), ("fx", "USD/MYR", "fx")]):
        s = mac[k]; c = (s[-1] / s[-21] - 1) * 100
        with cols[i % 2]:
            st.metric(nm, f"{s[-1]:,.3f}", f"{c:+.1f}% 20d"); st.plotly_chart(go.Figure(go.Scatter(x=idx, y=s, line=dict(color="#a86a00"))).update_layout(height=220, margin=dict(t=10)), width="stretch")
            st.caption(f'{msrc[k]} · {"Tailwind" if c > 0 else "Headwind"}: ' + ", ".join(x["name"] for x in UNIV if x["g"] == g))
with tabs[4]:
    st.markdown("""### Public OSINT vs. insider trading
BursaPulse reads only **public** information: filed 29B notices, announcements, public forum posts and market data. Section 188 of the Capital Markets and Services Act 2007 prohibits dealing in securities while in possession of non-public, price-sensitive information from an insider. Public filings are lawful to trade on; tips, leaks and "insider confirmed" messages are not. If you receive non-public information, do not trade on it and consider legal advice.

### How pump-and-dump patterns are flagged
A counter is tagged **Suspected pump-and-dump** when daily forum posts exceed the 12-day norm by more than 2σ and no 29B or Bursa announcement appeared in the prior 7 days. Hype keywords (moon, rocket, TP, buy now) also push posts into the Pump risk class, and Signal Strength drops 20 points.

### Limits
Insider, chatter and announcement data are simulated, and live prices come from an unofficial, delayed source. Scores are research heuristics, not buy/sell advice, legal or financial advice.""")
st.caption("Not investment advice. Only trade on public information (CMSA 2007 s.188).")
