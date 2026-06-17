# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# ==========================================
# 0. 網頁基本設定 & 精緻樣式
# ==========================================
st.set_page_config(
    page_title="股票助理 - 您的專屬台股資產管家", layout="wide", page_icon="📈"
)

st.markdown(
    """
    <style>
    .main { background-color: #FAFAFB; }
    h1, h2, h3 { color: #1E293B; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    .stButton>button { background-color: #0ea5e9; color: white; border-radius: 8px; border: none; }
    .stButton>button:hover { background-color: #0284c7; color: white; }

    .table-header {
        background-color: #F1F5F9;
        padding: 10px;
        border-radius: 4px;
        border: 1px solid #CBD5E1;
        font-weight: bold;
        color: #475569;
        margin-bottom: 8px;
    }
    .table-row {
        background-color: #FFFFFF;
        padding: 10px;
        border-radius: 4px;
        border: 1px solid #E2E8F0;
        margin-bottom: 4px;
    }

    .stButton > button[key^="del_"] {
        background-color: transparent !important;
        color: #64748B !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0px !important;
        font-size: 16px !important;
        cursor: pointer;
    }
    .stButton > button[key^="del_"]:hover {
        color: #EF4444 !important;
        background-color: transparent !important;
    }

    .news-link {
        display: inline-block;
        padding: 2px 8px;
        background-color: #e0f2fe;
        color: #0369a1 !important;
        border-radius: 4px;
        text-decoration: none;
        font-size: 13px;
        font-weight: bold;
    }
    .news-link:hover {
        background-color: #0284c7;
        color: white !important;
    }

    .metric-card-box {
        background-color: #F8FAFC;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #38BDF8;
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 股票助理")
st.caption("個人台股投資組合與多策略風險管理中心 (獨立雲端資料版)")

# ==========================================
# 1. 核心資料庫初始化與個人化雲端隔離設定
# ==========================================
# 讓使用者輸入自己的 Google 試算表 CSV 下載連結，達成每個人版本獨立
st.sidebar.markdown("### 🔐 個人雲端資料庫設定")
st.sidebar.markdown("為了讓每位使用者的資產資料完全獨立且不丟失，請串接您個人的 Google 試算表。")

sheet_url = st.sidebar.text_input(
    "請輸入您的 Google 試算表「共用連結」：",
    placeholder="https://docs.google.com/spreadsheets/d/.../edit?usp=sharing",
    help="請將您的 Google 試算表權限開啟為「知道連結的任何人均可檢視」，並把網址貼到這裡。"
).strip()


# 將一般 Google Sheet 網址轉換為可以直接讀取與寫入的 CSV 導出網址
def get_csv_url(url):
    try:
        if "/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    except:
        return None
    return None


csv_url = get_csv_url(sheet_url)

# 初始化 Session State，用來暫存還沒同步到雲端的個人本地資料（以防使用者暫時沒綁定 Sheet）
if "local_trades" not in st.session_state:
    st.session_state.local_trades = pd.DataFrame(columns=[
        "交易ID", "股票代號", "股票名稱", "交易類型", "股數", "成交單價",
        "交易時間", "手續費", "證交稅", "總收付金額", "策略標籤", "交易心得"
    ])


def load_trades():
    # 如果使用者有提供個人試算表，直接從他的雲端讀取
    if csv_url:
        try:
            df = pd.read_csv(csv_url, encoding="utf-8")
            if "策略標籤" not in df.columns:
                df["策略標籤"] = "#未分類"
            if "交易心得" not in df.columns:
                df["交易心得"] = ""
            if not df.empty:
                df["交易ID"] = range(1, len(df) + 1)
            return df
        except Exception as e:
            st.sidebar.error(f"❌ 雲端讀取失敗，請確認試算表權限是否已開啟為「任何人均可檢視」。")
            return st.session_state.local_trades
    else:
        return st.session_state.local_trades


df_trades = load_trades()

if csv_url:
    st.sidebar.success("🟢 已成功連線至您的個人雲端試算表！")
else:
    st.sidebar.warning("🟡 目前使用「臨時體驗模式」，網頁重整資料會消失。建議於左側綁定個人 Google 試算表網址。")

# ==========================================
# 2. 全域策略切換 (網頁最頂端)
# ==========================================
if not df_trades.empty:
    all_tags = ["✨ 顯示所有策略帳戶"] + sorted(df_trades["策略標籤"].dropna().unique().tolist())
    global_selected_tag = st.selectbox("🎯 【全域篩選】請選擇要檢視的獨立策略帳戶：", all_tags)

    if global_selected_tag == "✨ 顯示所有策略帳戶":
        df_filtered_global = df_trades.copy()
    else:
        df_filtered_global = df_trades[df_trades["策略標籤"] == global_selected_tag]
else:
    global_selected_tag = "✨ 顯示所有策略帳戶"
    df_filtered_global = pd.DataFrame()

st.write("---")

# ==========================================
# 3. 建立網頁分頁
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📊 持股比例圓餅圖",
    "📝 交易記帳與流水帳",
    "🧮 換股計算機與壓力測試"
])

# ------------------------------------------
# 【分頁 1：持股比例圓餅圖】
# ------------------------------------------
with tab1:
    st.subheader(f"📊 策略檢視：{global_selected_tag}")

    if not df_filtered_global.empty:
        summary_data = []
        for (tag, ticker), df_group in df_filtered_global.groupby(["策略標籤", "股票代號"]):
            name = df_group["股票名稱"].iloc[0]
            buy_shares = df_group[df_group["交易類型"] == "買入 (Buy)"]["股數"].sum()
            sell_shares = df_group[df_group["交易類型"] == "賣出 (Sell)"]["股數"].sum()
            current_shares = buy_shares - sell_shares
            avg_cost = df_group[df_group["交易類型"] == "買入 (Buy)"]["成交單價"].mean()

            if current_shares > 0:
                summary_data.append({
                    "策略標籤": tag, "股票代號": ticker, "股票名稱": name,
                    "持股股數": current_shares, "備用現價": avg_cost
                })

        if summary_data:
            portfolio_df = pd.DataFrame(summary_data)
            stock_tickers = portfolio_df["股票代號"].unique().tolist()


            def fetch_current_prices(tickers):
                prices = {}
                for ticker in tickers:
                    try:
                        stock = yf.Ticker(ticker)
                        todays_data = stock.history(period="1d")
                        prices[ticker] = round(todays_data["Close"].iloc[-1], 2) if not todays_data.empty else None
                    except:
                        prices[ticker] = None
                return prices


            with st.spinner("🔍 股票助理正在連網更新目前的最新市價..."):
                current_prices = fetch_current_prices(stock_tickers)

            portfolio_df["當前現價"] = portfolio_df["股票代號"].map(
                lambda tk: current_prices.get(tk) or portfolio_df[portfolio_df["股票代號"] == tk]["備用現價"].values[0])
            portfolio_df["目前市值"] = portfolio_df["持股股數"] * portfolio_df["當前現價"]
            total_wealth = portfolio_df["Currently估計總市值"] = portfolio_df["目前市值"].sum()

            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown(f"### 💰 總資產市值: **${total_wealth:,.2f}**")
                disp_portfolio = portfolio_df.copy()
                disp_portfolio["新聞連結"] = disp_portfolio["股票代號"].apply(
                    lambda x: f"https://tw.stock.yahoo.com/q/h?s={x.split('.')[0]}")
                disp_portfolio["股票代號"] = disp_portfolio["股票代號"].apply(lambda x: x.split('.')[0])

                st.dataframe(
                    disp_portfolio[
                        ["策略標籤", "股票代號", "股票名稱", "持股股數", "當前現價", "目前市值", "新聞連結"]],
                    use_container_width=True,
                    column_config={"新聞連結": st.column_config.LinkColumn("📰 財經快訊", display_text="點我查看新聞")}
                )
            with col2:
                if global_selected_tag == "✨ 顯示所有策略帳戶":
                    fig = px.pie(portfolio_df, values="開設市值" if False else "目前市值", names="策略標籤", hole=0.4,
                                 title="各策略資產配置比例", color_discrete_sequence=px.colors.sequential.Teal_r)
                else:
                    fig = px.pie(portfolio_df, values="目前市值", names="股票名稱", hole=0.4,
                                 title=f"{global_selected_tag} 策略內持股比例",
                                 color_discrete_sequence=px.colors.sequential.Teal_r)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 該策略帳戶目前無任何庫存持股。")
    else:
        st.info("💡 請先到交易記帳分頁紀錄您的第一筆交易並建立策略標籤。")

# ------------------------------------------
# 【分頁 2：交易記帳、流水帳與日記】
# ------------------------------------------
with tab2:
    st.subheader("📥 新增交易紀錄")
    pre_ticker = st.text_input("📍 請先輸入代號觸發即時財務面板 (例: 2330 / 2454 / 0050)", value="2330").strip()

    if pre_ticker:
        clean_pre = pre_ticker.replace(".TW", "").replace(".TWO", "").strip()
        search_pre = f"{clean_pre}.TW"
        try:
            if not yf.Ticker(search_pre).fast_info.get('lastPrice'): search_pre = f"{clean_pre}.TWO"
        except:
            search_pre = f"{clean_pre}.TWO"
        try:
            with st.spinner("📊 正在為您同步加載該股關鍵財務數據..."):
                tk_obj = yf.Ticker(search_pre)
                pe_ratio = tk_obj.info.get("trailingPE")
                pe_str = f"{round(pe_ratio, 2)} 倍" if pe_ratio else "暫無數據"
                st.markdown(
                    f'<div class="metric-card-box"><b>🔍 實時財報看板 ({search_pre})</b> | <span>價盈比 (本益比 PE): <span style=\'color:#0ea5e9;font-weight:bold;\'>{pe_str}</span></span></div>',
                    unsafe_allow_html=True)
        except:
            pass

    with st.form("trade_form", clear_on_submit=True):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_type = st.selectbox("交易類型", ["買入 (Buy)", "賣出 (Sell)"])
            t_ticker = st.text_input("股票代號 (確認送出代號)", value=pre_ticker).strip()
            t_shares = st.number_input("成交股數", min_value=1, value=1000, step=1)
            t_tag_input = st.text_input("🏷️ 策略標籤 (自行輸入)",
                                        value="#未分類" if global_selected_tag == "✨ 顯示所有策略帳戶" else global_selected_tag).strip()
        with col_t2:
            t_price = st.number_input("成交單價", min_value=0.0, value=100.0, step=0.1)
            t_datetime = st.datetime_input("交易日期與時間", datetime.now())
            t_notes = st.text_area("✍️ 交易日記 (買入原因/賣出動機/個股觀察)",
                                   placeholder="請記錄此筆交易的策略理由、心態觀察...")
        submit_button = st.form_submit_button(label="🚀 寫入交易紀錄與日記")

    if submit_button:
        if not t_ticker:
            st.error("❌ 請填寫股票代號！")
        else:
            clean_code = t_ticker.replace(".TW", "").replace(".TWO", "").strip()
            search_ticker = f"{clean_code}.TW"
            try:
                test_ob = yf.Ticker(f"{clean_code}.TW")
                if not test_ob.fast_info.get('lastPrice'): search_ticker = f"{clean_code}.TWO"
            except:
                search_ticker = f"{clean_code}.TWO"

            try:
                stock_info = yf.Ticker(search_ticker)
                t_name = stock_info.info.get("shortName") or stock_info.info.get("longName") or f"TW_{clean_code}"
            except:
                t_name = f"TW_{clean_code}"

            formatted_time = t_datetime.strftime("%Y-%m-%d %H:%M")
            raw_amount = t_shares * t_price
            fee = max(20, round(raw_amount * 0.001425))
            tax = round(raw_amount * (0.001 if "00" in search_ticker else 0.003)) if t_type == "賣出 (Sell)" else 0
            total_cash = -(raw_amount + fee) if t_type == "買入 (Buy)" else (raw_amount - fee - tax)

            new_trade = {
                "交易ID": len(df_trades) + 1, "股票代號": search_ticker, "股票名稱": t_name, "交易類型": t_type,
                "股數": t_shares, "成交單價": t_price, "交易時間": formatted_time,
                "手續費": fee, "證交稅": tax, "總收付金額": total_cash,
                "策略標籤": t_tag_input, "交易心得": t_notes
            }

            # 更新本地 Session
            st.session_state.local_trades = pd.concat([df_trades, pd.DataFrame([new_trade])], ignore_index=True)

            st.success(f"🎉 成功記錄！名稱：【{t_name}】")
            if csv_url:
                st.info("💡 提示：請將下方產生的 CSV 文字，複製貼上回您的 Google 試算表中以完成雲端存檔。")
                st.text_area("📋 複製此段文字並整段貼到 Google Sheet 第一個儲存格：",
                             st.session_state.local_trades.to_csv(index=False), height=150)
            else:
                st.rerun()

    st.write("---")

    if not df_filtered_global.empty:
        st.subheader(f"📜 歷史交易流水帳 (經策略篩選)")
        search_keyword = st.text_input("🔍 搜尋特定股票交易紀錄：",
                                       placeholder="請輸入欲查詢的股票代號或名稱 (例如: 2330 或 台積電，留空顯示全部)",
                                       key="table_search_input").strip()

        if search_keyword:
            df_filtered_search = df_filtered_global[
                df_filtered_global["股票代號"].str.contains(search_keyword, case=False) | df_filtered_global[
                    "股票名稱"].str.contains(search_keyword, case=False)]
        else:
            df_filtered_search = df_filtered_global.copy()

        df_display = df_filtered_search.sort_values(by="交易時間", ascending=False).head(50)

        if not df_display.empty:
            st.markdown('<div class="table-header">', unsafe_allow_html=True)
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6, h_col7, h_col8 = st.columns(
                [0.6, 1.8, 2.7, 1.1, 1.2, 1.3, 1.5, 0.8])
            h_col1.markdown("ID");
            h_col2.markdown("交易時間");
            h_col3.markdown("股票名稱 (標籤)");
            h_col4.markdown("類型")
            h_col5.markdown("<div style='text-align:right;'>股數</div>", unsafe_allow_html=True)
            h_col6.markdown("<div style='text-align:right;'>成交單價</div>", unsafe_allow_html=True)
            h_col7.markdown("<div style='text-align:right;'>總金額</div>", unsafe_allow_html=True)
            h_col8.markdown("<div style='text-align:center;'>操作</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            for _, row in df_display.iterrows():
                st.markdown('<div class="table-row">', unsafe_allow_html=True)
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([0.6, 1.8, 2.7, 1.1, 1.2, 1.3, 1.5, 0.8])
                col1.write(f"{row['交易ID']}");
                col2.write(f"{row['交易時間']}")
                pure_code = row['股票代號'].split('.')[0]
                yahoo_news_url = f"https://tw.stock.yahoo.com/q/h?s={pure_code}"
                col3.markdown(
                    f"**{row['股票名稱']}** (<span style='color:#0ea5e9;'>{row['策略標籤']}</span>) <a href='{yahoo_news_url}' target='_blank' class='news-link'>📰 新聞</a>",
                    unsafe_allow_html=True)
                type_color = "#0284c7" if "買入" in row["交易類型"] else "#f43f5e"
                col4.markdown(f"<span style='color:{type_color}; font-weight:bold;'>{row['交易類型']}</span>",
                              unsafe_allow_html=True)
                col5.markdown(f"<div style='text-align:right;'>{row['股數']:,} 股</div>", unsafe_allow_html=True)
                col6.markdown(f"<div style='text-align:right;'>${row['成交單價']:,.2f}</div>", unsafe_allow_html=True)
                amt_color = "#10B981" if row["總收付金額"] < 0 else "#EF4444"
                col7.markdown(
                    f"<div style='text-align:right; color:{amt_color}; font-weight:bold;'>${row['總收付金額']:,.2f}</div>",
                    unsafe_allow_html=True)
                with col8:
                    if st.button("🗑️", key=f"del_{row['交易ID']}"):
                        st.session_state.local_trades = df_trades[df_trades["交易ID"] != row["交易ID"]]
                        st.rerun()
                if pd.notna(row['交易心得']) and str(row['交易心得']).strip() != "":
                    st.markdown(
                        f"<div style='padding-left:35px; color:#64748B; font-size:13px;'>📝 <b>交易日記：</b> {row['交易心得']}</div>",
                        unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.write("---")
        st.subheader("📊 已實現交易對照分析")
        df_sells = df_filtered_global[df_filtered_global["交易類型"] == "賣出 (Sell)"]
        df_buys = df_filtered_global[df_filtered_global["交易類型"] == "買入 (Buy)"]

        if not df_sells.empty and not df_buys.empty:
            summary_reports = []
            for _, sell_item in df_sells.iterrows():
                past_buys = df_buys[
                    (df_buys["股票代號"] == sell_item["股票代號"]) & (df_buys["策略標籤"] == sell_item["策略標籤"]) & (
                                pd.to_datetime(df_buys["交易時間"]) <= pd.to_datetime(sell_item["交易時間"]))]
                if not past_buys.empty:
                    buy_date = pd.to_datetime(past_buys["交易時間"].min())
                    sell_date = pd.to_datetime(sell_item["交易時間"])
                    holding_days = max(0, (sell_date - buy_date).days)
                    avg_buy_price = past_buys["成交單價"].mean()
                    estimated_buy_cost = (avg_buy_price * sell_item["股數"]) + past_buys["手續費"].iloc[0]
                    real_net_profit = sell_item["總收付金額"] - estimated_buy_cost
                    real_roi = (real_net_profit / estimated_buy_cost) * 100
                    summary_reports.append({
                        "策略標籤": sell_item["策略標籤"], "股票": sell_item["股票名稱"], "代號": sell_item["股票代號"],
                        "賣出時間": sell_item["交易時間"], "持有天數": f"{holding_days} 天",
                        "真實損益 (精準淨利)": real_net_profit, "真實報酬率": real_roi
                    })
            if summary_reports:
                rep_df = pd.DataFrame(summary_reports)
                rep_df["代號"] = rep_df["代號"].apply(lambda x: x.split('.')[0])
                st.dataframe(rep_df.style.format({"真實損益 (精準淨利)": "${:,.2f}", "真實報酬率": "{:.2f}%"}),
                             use_container_width=True)

        if st.button("🚨 清空所有目前紀錄"):
            st.session_state.local_trades = pd.DataFrame(columns=df_trades.columns)
            st.rerun()

# ------------------------------------------
# 【分頁 3：換股計算機與壓力測試】
# ------------------------------------------
with tab3:
    st.subheader("🧮 換股計算機與資產壓力測試")
    st.markdown("#### 🔄 換股計算機")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        calc_a_ticker = st.text_input("想賣出的 A 股代號", placeholder="2303", key="calc_a").strip()
        calc_a_shares = st.number_input("預計賣出股數", min_value=1, value=1000, step=100)
    with col_c2:
        calc_b_ticker = st.text_input("想買進的 B 股代號", placeholder="2330", key="calc_b").strip()
    with col_c3:
        st.markdown("<br>", unsafe_allow_html=True)
        calc_trigger = st.button("⚖️ 開始精算換股比例")

    if calc_trigger:
        if not calc_a_ticker or not calc_b_ticker:
            st.error("❌ 請同時輸入 A 股與 B 股的代號才能進行換算！")
        else:
            clean_a = calc_a_ticker.replace(".TW", "").replace(".TWO", "").strip()
            clean_b = calc_b_ticker.replace(".TW", "").replace(".TWO", "").strip()
            tk_a, tk_b = f"{clean_a}.TW", f"{clean_b}.TW"
            with st.spinner("🔍 股票助理正在即時連網獲取雙邊最新市價..."):
                try:
                    st_a = yf.Ticker(tk_a)
                    if not st_a.fast_info.get('lastPrice'): tk_a = f"{clean_a}.TWO"
                    st_b = yf.Ticker(tk_b)
                    if not st_b.fast_info.get('lastPrice'): tk_b = f"{clean_b}.TWO"
                    price_a = yf.Ticker(tk_a).history(period="1d")["Close"].iloc[-1]
                    price_b = yf.Ticker(tk_b).history(period="1d")["Close"].iloc[-1]
                    total_sell_val = calc_a_shares * price_a
                    est_buy_shares = int(total_sell_val // price_b)
                    remain_cash = total_sell_val % price_b
                    st.success("📊 換股精算報告完成！")
                    st.markdown(
                        f"* 當前 **{clean_a}** 市價：`${price_a:,.2f}` | 當前 **{clean_b}** 市價：`${price_b:,.2f}`\n* 預估賣出總價值：<b style='color:#EF4444;'>${total_sell_val:,.2f}</b>\n* 在不額外掏出本金的情況下，您可以**全數換購**：<b style='color:#10B981; font-size:18px;'>{est_buy_shares:,} 股</b> 的 {clean_b}\n* 換股後剩餘零錢現金：`${remain_cash:,.2f}`",
                        unsafe_allow_html=True)
                except Exception as ce:
                    st.error(f"❌ 價格獲取失敗，錯誤原因: {ce}")

    st.write("---")
    st.subheader("🚨 黑天鵝崩盤壓力測試模擬器")
    if 'portfolio_df' in locals() and not portfolio_df.empty:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            drop_percent = st.slider("😱 模擬大盤/整體持股無差別暴跌幅度 (%)", min_value=5, max_value=50, value=20,
                                     step=5)
        if st.button("💥 執行黑天鵝壓力測試"):
            st.write("---")
            if global_selected_tag == "✨ 顯示所有策略帳戶":
                df_stress = portfolio_df.groupby("策略標籤")["目前市值"].sum().reset_index()
                df_stress["資產蒸發金額"] = df_stress["目前市值"] * (drop_percent / 100)
                df_stress["預估崩盤後市值"] = df_stress["目前市值"] - df_stress["資產蒸發金額"]
                post_crisis_total = total_wealth - df_stress["資產蒸發金額"].sum()
                st.markdown(
                    f"<div style='background-color:#EF444410; border: 2px dashed #EF4444; padding: 20px; border-radius: 8px; margin-bottom: 20px;'><h3 style='color:#EF4444; margin:0;'>☠️ 全策略資產重創警告</h3><p style='margin: 10px 0 0 0; color:#1E293B; font-size:16px;'>總市值將由 <b>${total_wealth:,.2f}</b> 驟降至 <b style='color:#EF4444;'>${post_crisis_total:,.2f}</b>。<br>整體資產在瞬間 <b>蒸發了 ${df_stress['資產蒸發金額'].sum():,.2f}</b> (跌幅為 <b>-{drop_percent}%</b>)！</p></div>",
                    unsafe_allow_html=True)
                st.dataframe(df_stress.style.format(
                    {"目前市值": "${:,.2f}", "資產蒸發金額": "${:,.2f}", "預估崩盤後市值": "${:,.2f}"}),
                             use_container_width=True)
            else:
                df_stress = portfolio_df.copy()
                df_stress["資產蒸發金額"] = df_stress["目前市值"] * (drop_percent / 100)
                df_stress["預估崩盤後市值"] = df_stress["目前市值"] - df_stress["資產蒸發金額"]
                post_crisis_total = total_wealth - df_stress["資產蒸發金額"].sum()
                st.markdown(
                    f"<div style='background-color:#EF444410; border: 2px dashed #EF4444; padding: 20px; border-radius: 8px; margin-bottom: 20px;'><h3 style='color:#EF4444; margin:0;'>☠️ 策略【{global_selected_tag}】重創警告</h3><p style='margin: 10px 0 0 0; color:#1E293B; font-size:16px;'>該策略市值將由 <b>${total_wealth:,.2f}</b> 驟降至 <b style='color:#EF4444;'>${post_crisis_total:,.2f}</b>。<br>資產瞬間 <b>蒸發了 ${df_stress['資產蒸發金額'].sum():,.2f}</b>！</p></div>",
                    unsafe_allow_html=True)
                df_stress["股票代號"] = df_stress["股票代號"].apply(lambda x: x.split('.')[0])
                st.dataframe(df_stress[["股票代號", "股票名稱", "持股股數", "當前現價", "目前市值", "資產蒸發金額",
                                        "預估崩盤後市值"]].style.format(
                    {"當前現價": "${:,.2f}", "目前市值": "${:,.2f}", "資產蒸發金額": "${:,.2f}",
                     "預估崩盤後市值": "${:,.2f}"}), use_container_width=True)
    else:
        st.info("💡 壓力測試模擬器需要您的當前策略帳戶內有實質持股庫存才能進行運算喔！")