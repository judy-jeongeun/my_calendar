import os
import calendar
from datetime import date, timedelta

import pandas as pd
import streamlit as st


st.set_page_config(page_title="일정 캘린더 앱", page_icon="📅", layout="wide")

CSV_FILE = "schedule.csv"
COLUMNS = ["날짜", "거래처명", "업무내용", "금액"]
WEEKDAYS_KR = ["월", "화", "수", "목", "금", "토", "일"]
EVENT_COLORS = ["#dbeafe", "#dcfce7", "#fef3c7", "#fce7f3", "#ede9fe", "#fee2e2"]
CLIENT_COLOR_MAP = {
    "신일초등학교": "#e9d5ff",  # 보라 계열
    "LH": "#fbcfe8",  # 분홍 계열
}


def load_data_from_csv(file_path: str) -> pd.DataFrame:
    """CSV 파일에서 데이터를 읽어와 표준 컬럼 형식으로 반환."""
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=COLUMNS)

    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    except Exception:
        # 인코딩/형식 문제가 있을 때도 앱이 죽지 않게 기본 형태 반환
        return pd.DataFrame(columns=COLUMNS)

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS].copy()
    df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce").dt.date
    return df


def save_data_to_csv(df: pd.DataFrame, file_path: str) -> None:
    """DataFrame을 CSV로 저장."""
    export_df = df.copy()
    export_df["날짜"] = export_df["날짜"].astype(str)
    export_df.to_csv(file_path, index=False, encoding="utf-8-sig")


def persist_current_data() -> None:
    """현재 세션 데이터를 schedule.csv에 자동 저장."""
    save_data_to_csv(st.session_state.data, CSV_FILE)


def color_for_client(client_name: str) -> str:
    """거래처명 기준으로 일정 박스 색상을 고정 배정."""
    if not client_name:
        return EVENT_COLORS[0]
    if client_name in CLIENT_COLOR_MAP:
        return CLIENT_COLOR_MAP[client_name]
    return EVENT_COLORS[hash(client_name) % len(EVENT_COLORS)]


def ensure_date(value) -> date:
    """입력값을 date 타입으로 안전하게 변환."""
    if isinstance(value, date):
        return value
    return pd.to_datetime(value, errors="coerce").date()


def get_data_for_month(data: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    month_data = data.copy()
    month_data = month_data.dropna(subset=["날짜"])
    month_data["날짜"] = pd.to_datetime(month_data["날짜"], errors="coerce").dt.date
    month_data = month_data.dropna(subset=["날짜"])
    month_data = month_data[
        month_data["날짜"].apply(lambda d: d.year == year and d.month == month)
    ]
    return month_data


def get_data_for_week(data: pd.DataFrame, anchor_date: date) -> pd.DataFrame:
    """기준일이 속한 주(월~일) 데이터 반환."""
    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    week_end = week_start + timedelta(days=6)
    week_data = data.copy()
    week_data["날짜"] = pd.to_datetime(week_data["날짜"], errors="coerce").dt.date
    week_data = week_data.dropna(subset=["날짜"])
    week_data = week_data[
        week_data["날짜"].apply(lambda d: week_start <= d <= week_end)
    ]
    return week_data


def render_revenue_summary(data: pd.DataFrame) -> None:
    """수익 요약 화면 렌더링."""
    st.subheader("수익 요약")
    view = st.radio("요약 기준", options=["주별", "월별"], horizontal=True)

    data_copy = data.copy()
    data_copy["날짜"] = pd.to_datetime(data_copy["날짜"], errors="coerce").dt.date
    data_copy["금액"] = pd.to_numeric(data_copy["금액"], errors="coerce").fillna(0).astype(int)
    data_copy = data_copy.dropna(subset=["날짜"])

    today = date.today()
    this_week_df = get_data_for_week(data_copy, today)
    this_month_df = get_data_for_month(data_copy, today.year, today.month)
    week_total = int(this_week_df["금액"].sum()) if not this_week_df.empty else 0
    month_total = int(this_month_df["금액"].sum()) if not this_month_df.empty else 0

    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("이번 주 총 수익", f"{week_total:,} 원")
    metric_col2.metric("이번 달 총 수익", f"{month_total:,} 원")

    target_df = this_week_df if view == "주별" else this_month_df
    title = "주별 거래처 합산" if view == "주별" else "월별 거래처 합산"
    st.markdown(f"##### {title}")

    if target_df.empty:
        st.info("해당 기간에 등록된 수익 데이터가 없습니다.")
        return

    grouped = (
        target_df.groupby("거래처명", as_index=False)["금액"]
        .sum()
        .sort_values(by="금액", ascending=False)
    )

    chart_df = grouped.rename(columns={"거래처명": "거래처", "금액": "수익"})
    st.markdown("##### 거래처별 수익 막대차트")
    st.bar_chart(chart_df.set_index("거래처"), height=280)

    for _, row in grouped.iterrows():
        client = str(row["거래처명"]).strip() or "(거래처 미입력)"
        amount = int(row["금액"])
        color = color_for_client(client)
        st.markdown(
            (
                "<div style='padding:12px 14px;border-radius:10px;margin-bottom:8px;"
                f"background:{color};border:1px solid rgba(0,0,0,0.08);"
                "display:flex;justify-content:space-between;align-items:center;'>"
                f"<div style='font-weight:700;font-size:1rem;'>{client}</div>"
                f"<div style='font-weight:800;font-size:1.1rem;'>{amount:,} 원</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    st.markdown("##### 월별 수익 증감 추이")
    trend_df = data_copy.copy()
    trend_df["년월"] = pd.to_datetime(trend_df["날짜"], errors="coerce").dt.to_period("M").astype(str)
    monthly = trend_df.groupby("년월", as_index=False)["금액"].sum().sort_values("년월")
    if monthly.empty:
        st.info("증감 추이를 표시할 데이터가 없습니다.")
        return

    monthly["전월 대비 증감"] = monthly["금액"].diff().fillna(0).astype(int)
    if len(monthly) >= 2:
        latest = int(monthly.iloc[-1]["금액"])
        prev = int(monthly.iloc[-2]["금액"])
        delta = latest - prev
        st.metric("전월 대비 증감", f"{latest:,} 원", f"{delta:+,} 원")
    else:
        st.metric("전월 대비 증감", f"{int(monthly.iloc[-1]['금액']):,} 원", "비교 데이터 없음")

    line_df = monthly.rename(columns={"금액": "월 수익", "전월 대비 증감": "증감"})
    st.line_chart(line_df.set_index("년월")[["월 수익", "증감"]], height=300)


def apply_app_style() -> None:
    """전체 앱 스타일(밝고 모던한 카드형) 적용."""
    st.markdown(
        """
        <style>
            .stApp {
                background: linear-gradient(180deg, #f5f3ff 0%, #f8fafc 100%);
                color: #1f2937;
            }
            [data-testid="stSidebar"] {
                background: #ede9fe;
                border-right: 1px solid #ddd6fe;
            }
            [data-testid="stSidebar"] * {
                color: #312e81;
            }
            [data-testid="stMetric"] {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 14px;
            }
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }
            div[data-testid="stVerticalBlock"] > div:has(> div > div > [data-testid="stMetric"]) {
                border-radius: 14px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_month_calendar(data: pd.DataFrame, year: int, month: int, active_view: str) -> None:
    """구글 캘린더 스타일 월 뷰 렌더링."""
    cal = calendar.Calendar(firstweekday=0)  # 월요일 시작
    month_weeks = cal.monthdayscalendar(year, month)

    month_data = get_data_for_month(data, year, month)
    grouped = {}
    for row_idx, row in month_data.iterrows():
        day_num = row["날짜"].day
        grouped.setdefault(day_num, []).append((row_idx, row))

    html = """
    <style>
      .cal-grid {display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px;}
      .cal-head {font-weight:700; color:#374151; text-align:center; padding:6px 0;}
      .day-cell {border:1px solid #e5e7eb; border-radius:10px; min-height:130px; background:#fff; padding:8px;}
      .day-cell.today {background:#fffbeb; border-color:#f59e0b;}
      .day-number {font-size:16px; font-weight:800; color:#111827; margin-bottom:8px;}
      .day-link {text-decoration:none;}
      .event-link {text-decoration:none; display:block; margin-bottom:6px;}
      .event-box {padding:6px 8px; border-radius:8px; font-size:12px; color:#111827; border:1px solid rgba(0,0,0,0.08);}
      .event-client {font-weight:700;}
      .empty-day {height:130px;}
      .muted {font-size:11px; color:#9ca3af;}
    </style>
    """
    html += "<div class='cal-grid'>"
    for i, day_name in enumerate(WEEKDAYS_KR):
        color = "#2563eb" if i == 5 else "#dc2626" if i == 6 else "#374151"
        html += f"<div class='cal-head' style='color:{color};'>{day_name}</div>"
    html += "</div>"
    html += "<div class='cal-grid'>"

    for week in month_weeks:
        for day_num in week:
            if day_num == 0:
                html += "<div class='empty-day'></div>"
                continue

            current_date = date(year, month, day_num)
            is_today = current_date == date.today()
            day_cls = "day-cell today" if is_today else "day-cell"
            day_rows = grouped.get(day_num, [])
            new_link = (
                f"?view={active_view}&year={year}&month={month}&new_date={current_date.isoformat()}"
            )

            html += f"<a class='day-link' href='{new_link}'><div class='{day_cls}'>"
            html += f"<div class='day-number'>{day_num}</div>"

            if not day_rows:
                html += "<div class='muted'>일정 없음</div>"
            else:
                for row_idx, item in day_rows:
                    event_color = color_for_client(str(item["거래처명"]))
                    edit_link = (
                        f"?view={active_view}&year={year}&month={month}&edit_idx={row_idx}"
                    )
                    html += (
                        f"<a class='event-link' href='{edit_link}'>"
                        f"<div class='event-box' style='background:{event_color};'>"
                        f"<div class='event-client'>{item['거래처명']}</div>"
                        f"<div>{item['업무내용']}</div>"
                        "</div></a>"
                    )
            html += "</div></a>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_week_view(data: pd.DataFrame, anchor_date: date, active_view: str, year: int, month: int) -> None:
    """주간 뷰 렌더링."""
    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    data_copy = data.copy()
    data_copy["날짜"] = pd.to_datetime(data_copy["날짜"], errors="coerce").dt.date

    st.markdown("##### 주간 보기")
    cols = st.columns(7)
    for idx, day in enumerate(week_days):
        with cols[idx]:
            color = "#2563eb" if idx == 5 else "#dc2626" if idx == 6 else "#111827"
            st.markdown(f"**:gray[{WEEKDAYS_KR[idx]}]**")
            st.markdown(f"<div style='font-weight:800;color:{color};font-size:1.1rem;'>{day.day}</div>", unsafe_allow_html=True)
            day_rows = data_copy[data_copy["날짜"] == day]
            if day_rows.empty:
                if st.button("새 일정", key=f"new_week_{day.isoformat()}", use_container_width=True):
                    st.session_state.dialog_mode = "new"
                    st.session_state.selected_date = day
            else:
                for row_idx, item in day_rows.iterrows():
                    event_color = color_for_client(str(item["거래처명"]))
                    st.markdown(
                        (
                            f"<div style='background:{event_color};border-radius:8px;padding:6px 8px;"
                            "margin:4px 0;font-size:0.82rem;'>"
                            f"<b>{item['거래처명']}</b><br>{item['업무내용']}"
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    if st.button("수정", key=f"edit_week_{row_idx}", use_container_width=True):
                        st.session_state.dialog_mode = "edit"
                        st.session_state.selected_row_idx = int(row_idx)


def render_day_view(data: pd.DataFrame, target_date: date) -> None:
    """일간 뷰 렌더링."""
    st.markdown("##### 일간 보기")
    st.caption(f"{target_date} 일정")
    data_copy = data.copy()
    data_copy["날짜"] = pd.to_datetime(data_copy["날짜"], errors="coerce").dt.date
    day_rows = data_copy[data_copy["날짜"] == target_date]
    if day_rows.empty:
        st.info("등록된 일정이 없습니다.")
        if st.button("새 일정 추가", use_container_width=True):
            st.session_state.dialog_mode = "new"
            st.session_state.selected_date = target_date
    else:
        for row_idx, item in day_rows.iterrows():
            color = color_for_client(str(item["거래처명"]))
            st.markdown(
                (
                    f"<div style='background:{color};border-radius:10px;padding:10px 12px;margin-bottom:8px;'>"
                    f"<b>{item['거래처명']}</b> - {item['업무내용']}<br>"
                    f"{int(item['금액']):,} 원"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            if st.button("이 일정 수정", key=f"edit_day_{row_idx}"):
                st.session_state.dialog_mode = "edit"
                st.session_state.selected_row_idx = int(row_idx)


def process_query_actions() -> None:
    """HTML 링크 클릭으로 전달된 쿼리 파라미터 처리."""
    query = st.query_params
    if "new_date" in query:
        try:
            clicked_date = ensure_date(query["new_date"])
            st.session_state.selected_date = clicked_date
            st.session_state.selected_row_idx = None
            st.session_state.dialog_mode = "new"
        except Exception:
            pass
        st.query_params.clear()
    elif "edit_idx" in query:
        try:
            clicked_idx = int(query["edit_idx"])
            if clicked_idx in st.session_state.data.index:
                st.session_state.selected_row_idx = clicked_idx
                st.session_state.selected_date = st.session_state.data.at[clicked_idx, "날짜"]
                st.session_state.dialog_mode = "edit"
        except Exception:
            pass
        st.query_params.clear()


@st.dialog("새 일정 추가")
def show_new_event_dialog() -> None:
    base_date = st.session_state.selected_date or date.today()
    with st.form("new_event_form"):
        new_date = st.date_input("날짜", value=base_date)
        new_client = st.text_input("거래처명")
        new_task = st.text_input("업무내용")
        new_amount = st.number_input("금액", min_value=0, step=1000, value=0)
        create_clicked = st.form_submit_button("저장")
    if create_clicked:
        if not new_client.strip() or not new_task.strip():
            st.warning("거래처명과 업무내용은 필수 입력입니다.")
            return
        new_row = pd.DataFrame(
            [{"날짜": new_date, "거래처명": new_client.strip(), "업무내용": new_task.strip(), "금액": int(new_amount)}]
        )
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
        st.session_state.selected_date = new_date
        persist_current_data()
        st.session_state.dialog_mode = None
        st.rerun()


@st.dialog("일정 수정")
def show_edit_event_dialog() -> None:
    selected_idx = st.session_state.selected_row_idx
    if selected_idx is None or selected_idx not in st.session_state.data.index:
        st.warning("수정할 일정을 찾을 수 없습니다.")
        st.session_state.dialog_mode = None
        return
    item = st.session_state.data.loc[selected_idx]
    with st.form("edit_event_form"):
        edit_date = st.date_input("날짜", value=item["날짜"])
        edit_client = st.text_input("거래처명", value=str(item["거래처명"]))
        edit_task = st.text_input("업무내용", value=str(item["업무내용"]))
        edit_amount = st.number_input("금액", min_value=0, step=1000, value=int(item["금액"]))
        c1, c2 = st.columns(2)
        update_clicked = c1.form_submit_button("수정 저장", use_container_width=True)
        delete_clicked = c2.form_submit_button("삭제", use_container_width=True)

    if update_clicked:
        if not edit_client.strip() or not edit_task.strip():
            st.warning("거래처명과 업무내용은 필수 입력입니다.")
            return
        st.session_state.data.at[selected_idx, "날짜"] = edit_date
        st.session_state.data.at[selected_idx, "거래처명"] = edit_client.strip()
        st.session_state.data.at[selected_idx, "업무내용"] = edit_task.strip()
        st.session_state.data.at[selected_idx, "금액"] = int(edit_amount)
        st.session_state.selected_date = edit_date
        persist_current_data()
        st.session_state.dialog_mode = None
        st.rerun()

    if delete_clicked:
        st.session_state.data = st.session_state.data.drop(index=selected_idx).reset_index(drop=True)
        st.session_state.selected_row_idx = None
        persist_current_data()
        st.session_state.dialog_mode = None
        st.rerun()


if "data" not in st.session_state:
    st.session_state.data = load_data_from_csv(CSV_FILE)
if "selected_row_idx" not in st.session_state:
    st.session_state.selected_row_idx = None
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None
if "dialog_mode" not in st.session_state:
    st.session_state.dialog_mode = None

apply_app_style()

st.title("📅 일정 캘린더 앱")
st.markdown("## 안녕하세요 쭈디님! 👋")
st.caption("날짜, 거래처명, 업무내용, 금액을 입력하면 schedule.csv에 자동 저장됩니다.")

with st.sidebar:
    st.markdown("### 메뉴")
    menu = st.radio("이동", options=["홈", "캘린더", "수익요약"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown(f"저장 파일: `{CSV_FILE}`")


with st.form("schedule_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        input_date = st.date_input("날짜", value=date.today())
        input_client = st.text_input("거래처명", placeholder="예: 빙그레")
    with col2:
        input_task = st.text_input("업무내용", placeholder="예: 월간 회의")
        input_amount = st.number_input("금액", min_value=0, step=1000, value=0)

    submitted = st.form_submit_button("일정 추가")

if submitted:
    if not input_client.strip() or not input_task.strip():
        st.warning("거래처명과 업무내용은 필수 입력입니다.")
    else:
        new_row = pd.DataFrame(
            [
                {
                    "날짜": input_date,
                    "거래처명": input_client.strip(),
                    "업무내용": input_task.strip(),
                    "금액": int(input_amount),
                }
            ]
        )
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
        st.session_state.selected_row_idx = None
        st.session_state.selected_date = input_date
        persist_current_data()
        st.success("일정이 추가되었습니다.")


process_query_actions()
today = date.today()

if menu == "홈":
    st.subheader("홈")
    left, right = st.columns([2, 1])
    with left:
        st.markdown("### 빠른 일정 추가")
    with right:
        st.markdown(f"`{CSV_FILE}` 자동 저장")

    st.subheader("일정 목록")
    if st.session_state.data.empty:
        st.info("등록된 일정이 없습니다.")
    else:
        sorted_df = st.session_state.data.sort_values(by="날짜", ascending=True).reset_index(drop=True)
        st.dataframe(sorted_df, use_container_width=True)
        total_amount = int(sorted_df["금액"].sum())
        st.metric("누적 수익", f"{total_amount:,} 원")

    uploaded_file = st.file_uploader("CSV 불러오기", type=["csv"])
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            for col in COLUMNS:
                if col not in uploaded_df.columns:
                    uploaded_df[col] = ""
            uploaded_df = uploaded_df[COLUMNS].copy()
            uploaded_df["금액"] = pd.to_numeric(uploaded_df["금액"], errors="coerce").fillna(0).astype(int)
            uploaded_df["날짜"] = pd.to_datetime(uploaded_df["날짜"], errors="coerce").dt.date
            st.session_state.data = uploaded_df
            st.session_state.selected_row_idx = None
            st.session_state.selected_date = None
            st.session_state.dialog_mode = None
            persist_current_data()
            st.success(f"CSV 데이터를 불러와 `{CSV_FILE}`에 반영했습니다.")
        except Exception:
            st.error("CSV 형식을 확인해주세요. (필수 컬럼: 날짜, 거래처명, 업무내용, 금액)")

elif menu == "캘린더":
    st.subheader("캘린더")
    select_col1, select_col2, select_col3 = st.columns([1, 1, 2])
    with select_col1:
        selected_year = st.selectbox("연도 선택", options=list(range(today.year - 5, today.year + 6)), index=5)
    with select_col2:
        selected_month = st.selectbox("월 선택", options=list(range(1, 13)), index=today.month - 1)
    with select_col3:
        view_mode = st.radio("보기", options=["월", "주", "일"], horizontal=True)

    if view_mode == "월":
        render_month_calendar(st.session_state.data, selected_year, selected_month, "month")
    elif view_mode == "주":
        anchor = st.session_state.selected_date or date(selected_year, selected_month, 1)
        render_week_view(st.session_state.data, anchor, "week", selected_year, selected_month)
    else:
        target = st.session_state.selected_date or date(selected_year, selected_month, 1)
        render_day_view(st.session_state.data, target)

else:
    render_revenue_summary(st.session_state.data)

if st.session_state.dialog_mode == "new":
    show_new_event_dialog()
elif st.session_state.dialog_mode == "edit":
    show_edit_event_dialog()
