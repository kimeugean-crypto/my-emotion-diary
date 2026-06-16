import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# ==========================================
# 0. 데이터베이스(DB) 및 알람 설정
# ==========================================
DB_FILE = "emotion_diary_v4.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # custom_emotions 컬럼을 추가하여 JSON 형태로 여러 감정을 저장합니다.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, time_slot TEXT, emotion_word TEXT,
            depression INTEGER, anxiety INTEGER, anger INTEGER,
            joy INTEGER, fear INTEGER, dread INTEGER,
            custom_emotions TEXT,
            UNIQUE(date, time_slot)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, hour INTEGER, activity_type TEXT, memo TEXT,
            UNIQUE(date, hour)
        )
    ''')
    conn.commit()
    conn.close()

def send_alarm_simulation(time_slot):
    print(f"⏰ [알람] 현재 {time_slot}시 감정 기록 시간입니다!")

@st.cache_resource
def start_scheduler():
    scheduler = BackgroundScheduler()
    for h in [11, 15, 19, 0]:
        slot = '24' if h == 0 else str(h)
        scheduler.add_job(send_alarm_simulation, 'cron', hour=h, minute=0, args=[slot])
    scheduler.start()
    return scheduler

init_db()
start_scheduler()

# ==========================================
# 1. 스트림릿 UI 레이아웃 설정
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기", layout="centered")
st.title("🧠 내 마음과 하루 기록기")

menu = st.sidebar.radio("메뉴 선택", ["오늘의 감정 기록", "24시간 일과 기록", "일일/주간 분석 리포트"])

EMOJI_DICT = {
    "😊 행복·평온": "😊", "🥳 신남·설렘": "🥳", "😎 뿌듯·당당": "😎", 
    "🥱 피곤·지침": "🥱", "😑 무기력·지루": "😑", "😤 짜증·분노": "😤", 
    "😥 슬픔·우울": "😥", "😰 불안·초조": "😰", "😨 공포·무서움": "😨", "🤔 그저그러함": "🤔"
}

def render_battery_indicator(label, score):
    """배터리 칸 시각화 헬퍼 함수"""
    if score >= 80: battery_icon = "🔋 (가득 참)"
    elif score >= 40: battery_icon = "🪫 (중간)"
    else: battery_icon = "🔌 (방전 임박)"
    
    st.write(f"**{label}** : {score}% {battery_icon}")
    st.progress(score / 100.0)

# ==========================================
# 2. 오늘의 감정 기록 (다중 커스텀 감정 추가 가능)
# ==========================================
if menu == "오늘의 감정 기록":
    st.header("📝 오늘의 감정 기록")
    
    col1, col2 = st.columns(2)
    with col1: log_date = st.date_input("기록 날짜", datetime.today())
    with col2: time_slot = st.selectbox("기록 시간대", ["11시", "15시", "19시", "24시"])
        
    st.markdown("---")
    
    st.subheader("1. 현재 마음 상태를 이모티콘으로 표현해 주세요")
    selected_emoji_key = st.selectbox("내 상태와 가장 가까운 이모티콘", list(EMOJI_DICT.keys()))
    chosen_emoji = EMOJI_DICT[selected_emoji_key]
    st.markdown(f"선택된 감정: <h1 style='text-align: center; font-size: 80px; margin: 0;'>{chosen_emoji}</h1>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.subheader("2. 기본 감정 배터리 충전 (직접 % 입력)")
    
    c1, c2 = st.columns(2)
    with c1:
        joy = st.number_input("기쁨 (Joy) %", min_value=0, max_value=100, value=50, step=5)
        depression = st.number_input("우울 (Depression) %", min_value=0, max_value=100, value=10, step=5)
        anxiety = st.number_input("불안 (Anxiety) %", min_value=0, max_value=100, value=10, step=5)
    with c2:
        anger = st.number_input("분노 (Anger) %", min_value=0, max_value=100, value=0, step=5)
        fear = st.number_input("공포 (Fear) %", min_value=0, max_value=100, value=0, step=5)
        dread = st.number_input("무서움 (Dread) %", min_value=0, max_value=100, value=0, step=5)
    
    # 💡 [핵심 추가 부분] 여러 개의 커스텀 감정을 동적으로 관리하기 위한 Session State 이용
    st.markdown("---")
    st.subheader("➕ 나만의 다른 감정 단어 추가하기")
    st.caption("기본 6가지 감정 외에 지금 느끼는 다른 감정 단어들을 마음껏 추가해 보세요.")

    # 세션 상태에 커스텀 감정 개수를 저장할 리스트 초기화
    if "custom_emotion_count" not in st.session_state:
        st.session_state.custom_emotion_count = 0

    # '감정 단어 추가하기' 버튼 클릭 시 카운트 증가
    if st.button("✨ 새로운 감정 단어 추가하기"):
        st.session_state.custom_emotion_count += 1

    # 사용자가 입력한 커스텀 감정 이름과 수치를 담을 딕셔너리
    custom_emotions_data = {}

    # 늘어난 카운트만큼 입력 폼을 반복해서 생성
    if st.session_state.custom_emotion_count > 0:
        for i in range(st.session_state.custom_emotion_count):
            st.markdown(f"**추가 감정 #{i+1}**")
            cc1, cc2 = st.columns(2)
            with cc1:
                c_name = st.text_input(f"감정 이름 입력 (#{i+1})", key=f"c_name_{i}")
            with cc2:
                c_score = st.number_input(f"수치 입력 (#{i+1}) %", min_value=0, max_value=100, value=50, step=5, key=f"c_score_{i}")
            
            # 이름이 입력된 경우에만 데이터 수집
            if c_name.strip():
                custom_emotions_data[c_name.strip()] = c_score
        
        # 입력폼 초기화 버튼
        if st.button("추가한 감정 입력창 모두 비우기"):
            st.session_state.custom_emotion_count = 0
            st.rerun()

    st.markdown("---")
    st.markdown("#### 🔋 실시간 내 감정 배터리 상태")
    v_col1, v_col2 = st.columns(2)
    with v_col1:
        render_battery_indicator("기쁨", joy)
        render_battery_indicator("우울", depression)
        render_battery_indicator("불안", anxiety)
    with v_col2:
        render_battery_indicator("분노", anger)
        render_battery_indicator("공포", fear)
        render_battery_indicator("무서움", dread)
    
    # 사용자가 동적으로 추가한 배터리들도 실시간 화면에 렌더링
    if custom_emotions_data:
        st.markdown("**[내가 추가한 감정 배터리]**")
        for name, score in custom_emotions_data.items():
            render_battery_indicator(name, score)

    # 저장 로직
    if st.button("감정 배터리 전체 저장하기", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 딕셔너리 데이터를 JSON 문자열 텍스트로 변환하여 DB에 통째로 보관
        custom_emotions_json = json.dumps(custom_emotions_data, ensure_ascii=False)
        
        cursor.execute('''
            INSERT OR REPLACE INTO emotion_logs 
            (date, time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread, custom_emotions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(log_date), time_slot, chosen_emoji, depression, anxiety, anger, joy, fear, dread, custom_emotions_json))
        conn.commit()
        conn.close()
        st.success(f"🎉 {time_slot}의 모든 감정 배터리({len(custom_emotions_data) + 6}종)가 성공적으로 기록되었습니다!")
        # 저장 후 입력 카운트 초기화
        st.session_state.custom_emotion_count = 0

# ==========================================
# 3. 24시간 일과 기록 (원그래프) 화면
# ==========================================
elif menu == "24시간 일과 기록":
    st.header("🕒 24시간 타임 루프 기록")
    activity_date = st.date_input("일과 기록 날짜", datetime.today())
    
    conn = sqlite3.connect(DB_FILE)
    df_act = pd.read_sql_query("SELECT * FROM daily_activities WHERE date = ?", conn, params=(str(activity_date),))
    conn.close()
    
    full_day = pd.DataFrame({'hour': range(24)})
    if not df_act.empty:
        df_act = pd.merge(full_day, df_act, on='hour', how='left')
    else:
        df_act = full_day
        df_act['activity_type'] = "미기록"
        df_act['memo'] = ""
    df_act['activity_type'] = df_act['activity_type'].fillna("미기록")
    df_act['memo'] = df_act['memo'].fillna("")

    color_map = {"수면": "blue", "집중": "yellow", "핸드폰 및 딴짓": "red", "미기록": "lightgray"}
    
    st.subheader("📊 오늘의 시간 원그래프")
    df_act['value'] = 1
    fig_pie = px.pie(
        df_act, values='value', names='activity_type',
        color='activity_type', color_discrete_map=color_map,
        hole=0.4, title=f"{activity_date} 일과 분포"
    )
    fig_pie.update_traces(textinfo='percent+label', sort=False)
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("✍️ 시간별 할 일 기록하기")
    
    select_hour = st.selectbox("기록할 시간대를 고르세요", [f"{h}시 ~ {h+1}시" for h in range(24)])
    target_hour = int(select_hour.split("시")[0])
    
    current_status = df_act[df_act['hour'] == target_hour].iloc[0]
    st.info(f"현재 상태: [{current_status['activity_type']}] {current_status['memo']}")
    
    act_type = st.radio("유형 선택", ["수면", "집중", "핸드폰 및 딴짓", "기타(미기록)"])
    db_act_type = "미기록" if act_type == "기타(미기록)" else act_type
    
    memo_text = st.text_input("간단히 한 일을 적어주세요", value=current_status['memo'])
    
    if st.button("일과 저장하기"):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_activities (date, hour, activity_type, memo)
            VALUES (?, ?, ?, ?)
        ''', (str(activity_date), target_hour, db_act_type, memo_text))
        conn.commit()
        conn.close()
        st.success(f"💾 {target_hour}시 일과가 저장되었습니다!")
        st.rerun()

# ==========================================
# 4. 분석 리포트 화면 (다중 추가 감정 불러오기 반영)
# ==========================================
elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 분석 대시보드")
    search_date = st.date_input("조회할 날짜 선택", datetime.today())
    
    conn = sqlite3.connect(DB_FILE)
    df_emotion = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ?", conn, params=(str(search_date),))
    conn.close()
    
    if df_emotion.empty:
        st.warning("선택한 날짜에 감정 기록이 없습니다.")
    else:
        st.subheader(f"📅 {search_date} 일일 감정 그래프")
        df_emotion['time_slot'] = pd.Categorical(df_emotion['time_slot'], categories=["11시", "15시", "19시", "24시"], ordered=True)
        df_emotion = df_emotion.sort_values('time_slot')
        
        base_emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        df_melted = df_emotion.melt(id_vars=['time_slot', 'emotion_word'], value_vars=base_emotions, var_name='감정', value_name='수치')
        
        fig_line = px.line(df_melted, x='time_slot', y='수치', color='감정', markers=True, title="시간대별 기본 감정 변화")
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.subheader("✨ 내가 추가한 특별한 감정 배터리 기록")
        for _, row in df_emotion.iterrows():
            st.write(f"⏱️ **{row['time_slot']} 선택한 표정**: {row['emotion_word']}")
            
            # JSON 문자열 복원 후 출력
            if row['custom_emotions']:
                custom_data = json.loads(row['custom_emotions'])
                if custom_data:
                    items_str = ", ".join([f"[{k}: {v}%]" for k, v in custom_data.items()])
                    st.write(f" └─ 함께 기록한 추가 감정: {items_str}")
                else:
                    st.write(" └─ 추가로 기록한 커스텀 감정이 없습니다.")

    st.markdown("---")
    st.subheader("🕸️ 주간 감정 밸런스 (최근 7일)")
    
    one_week_ago = search_date - timedelta(days=7)
    conn = sqlite3.connect(DB_FILE)
    df_week = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date >= ?", conn, params=(str(one_week_ago),))
    conn.close()
    
    if df_week.empty:
        st.warning("주간 분석 데이터가 부족합니다.")
    else:
        base_emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        mean_scores = df_week[base_emotions].mean()
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=mean_scores.values, theta=mean_scores.index, fill='toself'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
        st.plotly_chart(fig_radar, use_container_width=True)
