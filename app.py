import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# ==========================================
# 0. 데이터베이스(DB) 및 알람 설정
# ==========================================
DB_FILE = "emotion_diary_v2.db"

def init_db():
    """앱 시작 시 확장된 기능의 테이블들을 생성합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 감정 기록 테이블 (커스텀 감정 저장을 위해 JSON 형태나 텍스트로 보관 가능한 구조)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time_slot TEXT,
            emotion_word TEXT,
            depression INTEGER, anxiety INTEGER, anger INTEGER,
            joy INTEGER, fear INTEGER, dread INTEGER,
            custom_emotion_name TEXT,
            custom_emotion_score INTEGER,
            UNIQUE(date, time_slot)
        )
    ''')
    # 24시간 일과 기록 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            hour INTEGER,
            activity_type TEXT,
            memo TEXT,
            UNIQUE(date, hour)
        )
    ''')
    conn.commit()
    conn.close()

def send_alarm_simulation(time_slot):
    """기능 2: 알람 시스템 (시뮬레이션)"""
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

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴 선택", ["오늘의 감정 기록", "24시간 일과 기록", "일일/주간 분석 리포트"])

# 이모티콘 맵 정의 (기능 1)
EMOJI_DICT = {
    "😊 행복·평온": "😊", "🥳 신남·설렘": "🥳", "😎 뿌듯·당당": "😎", 
    "🥱 피곤·지침": "🥱", "😑 무기력·지루": "😑", "😤 짜증·분노": "😤", 
    "😥 슬픔·우울": "😥", "😰 불안·초조": "😰", "😨 공포·무서움": "😨", "🤔 그저그러함": "🤔"
}

# ==========================================
# 2. [기능 1 & 2] 감정 기록하기 화면
# ==========================================
if menu == "오늘의 감정 기록":
    st.header("📝 오늘의 감정 기록")
    
    col1, col2 = st.columns(2)
    with col1: log_date = st.date_input("기록 날짜", datetime.today())
    with col2: time_slot = st.selectbox("기록 시간대", ["11시", "15시", "19시", "24시"])
        
    st.markdown("---")
    
    # 기능 1: 얼굴 이모티콘 선택 UI
    st.subheader("1. 현재 마음 상태를 이모티콘으로 표현해 주세요")
    selected_emoji_key = st.selectbox("내 상태와 가장 가까운 이모티콘", list(EMOJI_DICT.keys()))
    chosen_emoji = EMOJI_DICT[selected_emoji_key]
    st.markdown(f"선택된 감정: <h1 style='text-align: center; font-size: 80px; margin: 0;'>{chosen_emoji}</h1>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 기능 2: 감정 수치화 및 커스텀 감정 추가
    st.subheader("2. 감정 수치화 (0 ~ 100)")
    joy = st.slider("기쁨 (Joy)", 0, 100, 50)
    depression = st.slider("우울 (Depression)", 0, 100, 10)
    anxiety = st.slider("불안 (Anxiety)", 0, 100, 10)
    anger = st.slider("분노 (Anger)", 0, 100, 0)
    fear = st.slider("공포 (Fear)", 0, 100, 0)
    dread = st.slider("무서움 (Dread)", 0, 100, 0)
    
    # 추가 감정 등록 섹션
    st.markdown("💡 **나만의 다른 감정을 추가하고 싶으신가요?**")
    custom_emotion_name = st.text_input("추가할 감정 이름 (예: 외로움, 질투, 지루함)", placeholder="없으면 비워두세요")
    custom_emotion_score = 0
    if custom_emotion_name:
        custom_emotion_score = st.slider(f"[{custom_emotion_name}] 수치", 0, 100, 50)

    if st.button("감정 저장하기", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO emotion_logs 
            (date, time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread, custom_emotion_name, custom_emotion_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(log_date), time_slot, chosen_emoji, depression, anxiety, anger, joy, fear, dread, custom_emotion_name, custom_emotion_score))
        conn.commit()
        conn.close()
        st.success(f"🎉 {time_slot} 감정이 기록되었습니다!")

# ==========================================
# 3. [기능 3] 24시간 일과 기록 (원그래프) 화면
# ==========================================
elif menu == "24시간 일과 기록":
    st.header("🕒 24시간 타임 루프 기록")
    activity_date = st.date_input("일과 기록 날짜", datetime.today())
    
    # 현재 날짜의 24시간 데이터 불러오기 혹은 빈칸 생성
    conn = sqlite3.connect(DB_FILE)
    df_act = pd.read_sql_query("SELECT * FROM daily_activities WHERE date = ?", conn, params=(str(activity_date),))
    conn.close()
    
    # 0~23시 기본 데이터 틀 만들기
    full_day = pd.DataFrame({'hour': range(24)})
    if not df_act.empty:
        df_act = pd.merge(full_day, df_act, on='hour', how='left')
    else:
        df_act = full_day
        df_act['activity_type'] = "미기록"
        df_act['memo'] = ""
    df_act['activity_type'] = df_act['activity_type'].fillna("미기록")
    df_act['memo'] = df_act['memo'].fillna("")

    # 시각화 데이터 준비 및 색상 지정
    color_map = {"수면": "blue", "집중": "yellow", "핸드폰 및 딴짓": "red", "미기록": "lightgray"}
    
    st.subheader("📊 오늘의 시간 원그래프")
    # 원그래프 그리기 (각 시간은 1씩 균등 할당)
    df_act['value'] = 1
    fig_pie = px.pie(
        df_act, 
        values='value', 
        names='activity_type',
        color='activity_type',
        color_discrete_map=color_map,
        hole=0.4,
        title=f"{activity_date} 일과 분포"
    )
    fig_pie.update_traces(textinfo='percent+label', sort=False)
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("✍️ 시간별 할 일 기록하기")
    
    # 입력 폼
    select_hour = st.selectbox("기록할 시간대를 고르세요", [f"{h}시 ~ {h+1}시" for h in range(24)])
    target_hour = int(select_hour.split("시")[0])
    
    # 현재 기록된 상태 보여주기
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
# 4. 분석 리포트 화면 (일일 / 주간 그래프 통합)
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
        
        # 기본 감정 선 그래프
        base_emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        df_melted = df_emotion.melt(id_vars=['time_slot', 'emotion_word'], value_vars=base_emotions, var_name='감정', value_name='수치')
        
        fig_line = px.line(df_melted, x='time_slot', y='수치', color='감정', markers=True, title="시간대별 감정 변화")
        st.plotly_chart(fig_line, use_container_width=True)
        
        # 사용자가 추가한 커스텀 감정 출력
        st.subheader("✨ 내가 추가한 특별한 감정들")
        for _, row in df_emotion.iterrows():
            if row['custom_emotion_name']:
                st.write(f"- **{row['time_slot']}**: 추가 감정 **[{row['custom_emotion_name']}]** 의 수치는 **{row['custom_emotion_score']}점**이었습니다.")
            st.write(f"- **{row['time_slot']} 선택한 표정**: {row['emotion_word']}")

    st.markdown("---")
    st.subheader("🕸️ 주간 감정 밸런스 (최근 7일)")
    
    # 주간 레이더 차트
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
