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
DB_FILE = "emotion_diary.db"

def init_db():
    """앱 시작 시 가상의 로컬 DB 테이블을 생성합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time_slot TEXT,
            emotion_word TEXT,
            depression INTEGER,
            anxiety INTEGER,
            anger INTEGER,
            joy INTEGER,
            fear INTEGER,
            dread INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def send_alarm_simulation(time_slot):
    """기능 2: 정해진 시간에 작동할 알람 시스템 (콘솔 시뮬레이션)"""
    # 실제 서비스에서는 이 부분에 Web Push 알림이나 카카오톡 API를 연동합니다.
    print(f"⏰ [알람 발생] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 현재 {time_slot}시 감정 기록 시간입니다!")

# 앱이 실행될 때 백그라운드 스케줄러 등록 (하루 4번)
@st.cache_resource
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_alarm_simulation, 'cron', hour=11, minute=0, args=['11'])
    scheduler.add_job(send_alarm_simulation, 'cron', hour=15, minute=0, args=['15'])
    scheduler.add_job(send_alarm_simulation, 'cron', hour=19, minute=0, args=['19'])
    scheduler.add_job(send_alarm_simulation, 'cron', hour=0, minute=0, args=['24'])
    scheduler.start()
    return scheduler

# 초기화 실행
init_db()
start_scheduler()

# ==========================================
# 1. 스트림릿 UI 레이아웃 설정
# ==========================================
st.set_page_config(page_title="마음 기록기", layout="centered")
st.title("🧠 나의 감정 기록 & 그래프 다시보기")
st.caption("하루 4번(11시, 15시, 19시, 24시) 나의 마음 상태를 추적합니다.")

# 사이드바 메뉴 구성
menu = st.sidebar.radio("메뉴 선택", ["감정 기록하기", "일일 감정 그래프", "주간 감정 분석"])

# ==========================================
# 2. [기능] 감정 기록하기 화면
# ==========================================
if menu == "감정 기록하기":
    st.header("📝 오늘의 감정 기록")
    
    # 시간대 및 날짜 선택
    col1, col2 = st.columns(2)
    with col1:
        log_date = st.date_input("기록 날짜", datetime.today())
    with col2:
        time_slot = st.selectbox("기록 시간대", ["11시", "15시", "19시", "24시"])
        
    st.markdown("---")
    
    # 감정 단어 선택 (칩 형태 대용)
    emotion_word = st.selectbox(
        "지금 내 감정을 가장 잘 표현하는 단어는?",
        ["평온함", "뿌듯함", "설렘", "무기력", "지침", "답답함", "짜증남", "불안함", "무서움", "기타"]
    )
    
    st.write("📊 **6가지 감정 수치를 입력해 주세요 (0 ~ 100)**")
    
    # 6대 감정 슬라이더 입력
    joy = st.slider("기쁨 (Joy)", 0, 100, 50)
    depression = st.slider("우울 (Depression)", 0, 100, 10)
    anxiety = st.slider("불안 (Anxiety)", 0, 100, 10)
    anger = st.slider("분노 (Anger)", 0, 100, 0)
    fear = st.slider("공포 (Fear)", 0, 100, 0)
    dread = st.slider("무서움 (Dread)", 0, 100, 0)
    
    if st.button("감정 저장하기"):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 기존에 같은 날짜, 같은 시간대 기록이 있다면 덮어쓰기(Upsert) 형태로 처리
        cursor.execute('''
            INSERT OR REPLACE INTO emotion_logs (date, time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(log_date), time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread))
        
        conn.commit()
        conn.close()
        st.success(f"🎉 {log_date} {time_slot} 감정이 성공적으로 기록되었습니다!")

# ==========================================
# 3. [기능 1] 일일 감정 그래프 화면
# ==========================================
elif menu == "일일 감정 그래프":
    st.header("📅 일일 감정 변화 추이")
    search_date = st.date_input("조회할 날짜를 선택하세요", datetime.today())
    
    # DB에서 해당 날짜 데이터 가져오기
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ?", conn, params=(str(search_date),))
    conn.close()
    
    if df.empty:
        st.warning("선택하신 날짜에 기록된 감정 데이터가 없습니다. 먼저 감정을 기록해 주세요!")
    else:
        # 시간대 정렬을 위한 카테고리 지정
        df['time_slot'] = pd.Categorical(df['time_slot'], categories=["11시", "15시", "19시", "24시"], ordered=True)
        df = df.sort_values('time_slot')
        
        # 라인 차트 그리기 위해 데이터 재구성(Melt)
        emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        df.columns = ['id', 'date', 'time_slot', '감정단어', '우울', '불안', '분노', '기쁨', '공포', '무서움']
        
        df_melted = df.melt(id_vars=['time_slot', '감정단어'], value_vars=emotions, var_name='감정 종류', value_name='수치')
        
        # Plotly 선 그래프 생성
        fig = px.line(
            df_melted, 
            x='time_slot', 
            y='수치', 
            color='감정 종류', 
            markers=True,
            title=f"{search_date} 감정 흐름 타임라인",
            labels={'time_slot': '기록 시간대', '수치': '점수'}
        )
        fig.update_layout(yaxis=dict(range=[-5, 105])) # 0~100 고정
        st.plotly_chart(fig, use_container_width=True)
        
        # 선택한 감정 단어 리스트 피드백
        st.subheader("💡 시간대별 한 줄 요약 단어")
        for idx, row in df.iterrows():
            st.write(f"- **{row['time_slot']}**: 오늘의 대표 감정은 **[{row['감정단어']}]** 이었습니다.")

# ==========================================
# 4. [기능 3] 주간 감정 그래프 화면
# ==========================================
elif menu == "주간 감정 분석":
    st.header("📊 주간 감정 통계 피드백")
    st.write("최근 일주일간의 데이터를 종합하여 분석합니다.")
    
    today = datetime.today().date()
    one_week_ago = today - timedelta(days=7)
    
    # DB에서 최근 일주일 데이터 가져오기
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date >= ?", conn, params=(str(one_week_ago),))
    conn.close()
    
    if df.empty or len(df['date'].unique()) < 1:
        st.warning("주간 분석을 위한 데이터가 부족합니다. 최소 1일 이상의 기록이 필요합니다.")
    else:
        df.columns = ['id', 'date', 'time_slot', '감정단어', '우울', '불안', '분노', '기쁨', '공포', '무서움']
        emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        
        # 1. 주간 평균 감정 (레이더 차트)
        st.subheader("🕸️ 주간 평균 감정 밸런스")
        mean_scores = df[emotions].mean()
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=mean_scores.values,
            theta=mean_scores.index,
            fill='toself',
            name='주간 평균'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # 2. 날짜별 감정 변화 추이 (일일 평균 기준 선 그래프)
        st.subheader("📈 일주일간의 감정 흐름 현황")
        df_daily_mean = df.groupby('date')[emotions].mean().reset_index()
        df_daily_melted = df_daily_mean.melt(id_vars=['date'], value_vars=emotions, var_name='감정 종류', value_name='평균 수치')
        
        fig_weekly_line = px.line(
            df_daily_melted,
            x='date',
            y='평균 수치',
            color='감정 종류',
            markers=True,
            title="일자별 감정 평균 추이"
        )
        st.plotly_chart(fig_weekly_line, use_container_width=True)