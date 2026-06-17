import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 구글 시트 클라우드 DB 연결
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# 에러 방지용 안전 데이터 로드 함수
def load_data(worksheet_name, columns):
    try:
        df = conn.read(worksheet=worksheet_name, ttl="0")
        if df is None or df.empty:
            return pd.DataFrame(columns=columns)
        # 구글 시트에서 간혹 컬럼이 다르게 읽히거나 빠지는 경우 방지
        for col in columns:
            if col not in df.columns:
                df[col] = None
        return df[columns]
    except Exception:
        return pd.DataFrame(columns=columns)

# 구글 시트에 데이터 추가 함수
def append_data(worksheet_name, new_row_dict, columns):
    df = load_data(worksheet_name, columns)
    new_df = pd.DataFrame([new_row_dict])
    df = pd.concat([df, new_df], ignore_index=True)
    conn.update(worksheet=worksheet_name, data=df)
    st.success("☁️ 구글 시트와 안전하게 동기화되었습니다!")

# 각 탭(시트) 컬럼 구조 정의
EMO_COLS = ['date', 'time_slot', 'emotion_word', 'depression', 'anxiety', 'anger', 'joy', 'fear', 'dread', 'q1_moment', 'q2_thought', 'sentence_reason', 'sentence_result', 'affirmation']
ACT_COLS = ['date', 'hour', 'activity_type', 'memo', 'plan_type']
GOAL_COLS = ['date', 'today_goal_1', 'today_goal_1_done', 'today_goal_2', 'today_goal_2_done', 'week_habit_1', 'week_habit_1_done', 'week_habit_2', 'week_habit_2_done']
REV_COLS = ['date', 'reflection', 'improvement', 'praise', 'repr_emoji']

# ==========================================
# 2. 화면 레이아웃 및 메뉴 설정
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기", layout="centered")
st.title("🧠 내 마음과 하루 기록기")

menu = st.sidebar.radio("메뉴 선택", ["오늘의 감정 기록", "24시간 일과 기록", "일일/주간 분석 리포트"])
EMOJI_LIST = ["😊", "🥳", "😎", "🥱", "😑", "😤", "😥", "😰", "😨", "🤔"]
COLOR_MAP = {"수면": "#4A90E2", "집중": "#2ECC71", "핸드폰 및 딴짓": "#E24A4A", "미기록": "#EAEAEA"}

# 🔥 오타(classification)를 완전히 청소한 시계 차트 함수
def draw_clock_chart(df, title_label):
    display_texts = []
    for _, r in df.iterrows():
        h = int(r['hour']) if 'hour' in r else 0
        memo = str(r['memo']) if ('memo' in r and pd.notna(r['memo'])) else ""
        if memo.strip():
            display_texts.append(f"{h:02d}:00<br><b>📝 {memo}</b>")
        else:
            display_texts.append(f"{h:02d}:00")
            
    df['display_text'] = display_texts
    df['color'] = df['activity_type'].map(COLOR_MAP).fillna("#EAEAEA")
    
    fig = go.Figure(data=[go.Pie(
        labels=df['display_text'], values=[1] * len(df),
        marker=dict(colors=df['color'], line=dict(color='#FFFFFF', width=2)),
        hole=0.45, sort=False, direction='clockwise', rotation=90,
        textinfo='text', text=df['display_text'], textposition='inside'
    )])
    fig.update_layout(title=dict(text=title_label, x=0.5), showlegend=False, height=400, margin=dict(t=40,b=20,l=20,r=20))
    return fig

# ==========================================
# 3. 메뉴별 기능 구현
# ==========================================
if menu == "오늘의 감정 기록":
    st.header("📝 오늘의 감정 성찰 기록")
    log_date = st.date_input("기록 날짜", datetime.today())
    time_slot = st.selectbox("기록 시간대 선택", [f"{h:02d}:00" for h in range(24)])
    
    q1_moment = st.text_area("❓ 내가 구실을 만들기 시작한 순간은?")
    q2_thought = st.text_area("❓ 그때 내 머릿속을 스쳤던 생각은?")
    chosen_emoji = st.radio("지금 표정 고르기", EMOJI_LIST, horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        joy = st.slider("기쁨 %", 0, 100, 50)
        depression = st.slider("우울 %", 0, 100, 10)
        anxiety = st.slider("불안 %", 0, 100, 10)
    with col2:
        anger = st.slider("분노 %", 0, 100, 0)
        fear = st.slider("공포 %", 0, 100, 0)
        dread = st.slider("무서움 %", 0, 100, 0)
        
    sentence_reason = st.text_input("구실을 만든 이유")
    sentence_result = st.text_input("그 결과 느낀 감정")
    user_affirmation = st.text_input("나를 다독이는 확언 한 줄")

    if st.button("💾 구글 시트에 안전하게 저장", use_container_width=True):
        data_dict = {
            'date': str(log_date), 'time_slot': time_slot, 'emotion_word': chosen_emoji,
            'depression': depression, 'anxiety': anxiety, 'anger': anger, 'joy': joy, 'fear': fear, 'dread': dread,
            'q1_moment': q1_moment, 'q2_thought': q2_thought, 'sentence_reason': sentence_reason,
            'sentence_result': sentence_result, 'affirmation': user_affirmation
        }
        append_data("emotion_logs", data_dict, EMO_COLS)

elif menu == "24시간 일과 기록":
    st.header("🕒 24시간 타임 루프 기록")
    activity_date = st.date_input("일과 기록 날짜", datetime.today())
    date_str = str(activity_date)
    
    df_db_act = load_data("daily_activities", ACT_COLS)
    
    db_acts = {}
    if not df_db_act.empty:
        df_filtered = df_db_act[(df_db_act['date'] == date_str) & (df_db_act['plan_type'] == 'actual')]
        db_acts = {int(row['hour']): {"activity_type": row['activity_type'], "memo": row['memo']} for _, row in df_filtered.iterrows()}
        
    rows = []
    for h in range(24):
        info = db_acts.get(h, {"activity_type": "미기록", "memo": ""})
        rows.append({"hour": h, "activity_type": info["activity_type"], "memo": info["memo"]})
    df_act = pd.DataFrame(rows)
    
    st.plotly_chart(draw_clock_chart(df_act, "오늘의 실제 행동 조각"), use_container_width=True)
    
    with st.expander("✍️ 시간 조각 입력 및 수정하기"):
        target_hour = st.selectbox("시간 선택", list(range(24)), format_func=lambda x: f"{x:02d}:00")
        act_type = st.radio("행동 유형", ["수면", "집중", "핸드폰 및 딴짓", "미기록"], horizontal=True)
        memo_text = st.text_input("활동 메모")
        
        if st.button("💾 시간 조각 저장하기"):
            df_all = load_data("daily_activities", ACT_COLS)
            if not df_all.empty:
                df_all = df_all[~((df_all['date'] == date_str) & (df_all['hour'].astype(int) == target_hour) & (df_all['plan_type'] == 'actual'))]
            new_row = {'date': date_str, 'hour': target_hour, 'activity_type': act_type, 'memo': memo_text, 'plan_type': 'actual'}
            df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
            conn.update(worksheet="daily_activities", data=df_all)
            st.success("행동 조각이 저장되었습니다!")
            st.rerun()

    st.markdown("---")
    st.subheader("🎯 오늘의 목표")
    g1 = st.text_input("목표 1")
    g1_d = st.checkbox("목표 1 완료")
    
    if st.button("💾 목표 상태 저장"):
        append_data("daily_goals", {'date': date_str, 'today_goal_1': g1, 'today_goal_1_done': int(g1_d), 'today_goal_2': '', 'today_goal_2_done': 0, 'week_habit_1': '', 'week_habit_1_done': 0, 'week_habit_2': '', 'week_habit_2_done': 0}, GOAL_COLS)

elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 및 목표 분석 대시보드")
    
    df_goals = load_data("daily_goals", GOAL_COLS)
    df_acts = load_data("daily_activities", ACT_COLS)
    
    # 기상 시간 동적 연동 로직
    wakeup_map = {}
    if not df_acts.empty:
        actual_acts = df_acts[df_acts['plan_type'] == 'actual']
        for g_date, group in actual_acts.groupby('date'):
            act_dict = {int(row['hour']): row['activity_type'] for _, row in group.iterrows()}
            for h in range(4, 13):
                if act_dict.get(h-1) == "수면" and act_dict.get(h) in ["집중", "핸드폰 및 딴짓", "미기록"]:
                    wakeup_map[str(g_date)] = f"{h:02d}:00"
                    break

    now = datetime.now()
    select_year = st.selectbox("연도", [2026, 2027])
    select_month = st.selectbox("월", list(range(1, 13)), index=now.month - 1)
    
    calendar_data_map = {}
    if not df_goals.empty:
        for _, g in df_goals.iterrows():
            try:
                d_obj = datetime.strptime(str(g['date']), "%Y-%m-%d")
                if d_obj.year == select_year and d_obj.month == select_month:
                    calendar_data_map[d_obj.day] = {"rate": 100 if int(g.get('today_goal_1_done', 0)) == 1 else 0}
            except: pass

    cal = calendar.monthcalendar(select_year, select_month)
    cal_html = "<table style='width:100%; border-collapse: collapse; text-align:center;'>"
    cal_html += "<tr style='background-color:#F0F2F6;'><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th style='color:blue;'>토</th><th style='color:red;'>일</th></tr>"
    
    for week in cal:
        cal_html += "<tr>"
        for day in week:
            if day == 0:
                cal_html += "<td style='border:1px solid #E6E9EF; background-color:#FAFAFA;'></td>"
            else:
                date_key = f"{select_year}-{select_month:02d}-{day:02d}"
                day_data = calendar_data_map.get(day, {"rate": None})
                w_time = wakeup_map.get(date_key, "미기록")
                
                rate_str = f"<div style='font-size:11px; color:green;'>🎯달성: {day_data['rate']}%</div>" if day_data['rate'] is not None else "<div style='font-size:11px; color:#aaa;'>🎯미기록</div>"
                wakeup_str = f"<div style='font-size:11px; color:orange;'>🌅기상: {w_time}</div>"
                
                cal_html += f"<td style='border:1px solid #E6E9EF; height:80px; vertical-align:top; padding:5px;'><b>{day}</b>{rate_str}{wakeup_str}</td>"
        cal_html += "</tr>"
    st.markdown(cal_html + "</table>", unsafe_allow_html=True)
