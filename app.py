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
DB_FILE = "emotion_diary_v5.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 감정 로그 테이블 고정 (에러 방지용 명시적 컬럼 정의)
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
    if score >= 80: battery_icon = "🔋 (가득 참)"
    elif score >= 40: battery_icon = "🪫 (중간)"
    else: battery_icon = "🔌 (방전 임박)"
    st.write(f"**{label}** : {score}% {battery_icon}")
    st.progress(score / 100.0)

# ==========================================
# 2. 오늘의 감정 기록
# ==========================================
if menu == "오늘의 감정 기록":
    st.header("📝 오늘의 감정 기록")
    
    col1, col2 = st.columns(2)
    with col1: log_date = st.date_input("기록 날짜", datetime.today())
    with col2: time_slot = st.selectbox("기록 시간대", ["11시", "15시", "19시", "24시"])
        
    st.markdown("---")
    st.subheader("1. 현재 마음 상태를 이모티콘")
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
    
    st.markdown("---")
    st.subheader("➕ 나만의 다른 감정 단어 추가하기")
    if "custom_emotion_count" not in st.session_state:
        st.session_state.custom_emotion_count = 0

    if st.button("✨ 새로운 감정 단어 추가하기"):
        st.session_state.custom_emotion_count += 1

    custom_emotions_data = {}
    if st.session_state.custom_emotion_count > 0:
        for i in range(st.session_state.custom_emotion_count):
            cc1, cc2 = st.columns(2)
            with cc1: c_name = st.text_input(f"감정 이름 (#{i+1})", key=f"c_name_{i}")
            with cc2: c_score = st.number_input(f"수치 (#{i+1}) %", min_value=0, max_value=100, value=50, step=5, key=f"c_score_{i}")
            if c_name.strip():
                custom_emotions_data[c_name.strip()] = c_score

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
    
    if custom_emotions_data:
        for name, score in custom_emotions_data.items():
            render_battery_indicator(name, score)

    if st.button("감정 배터리 전체 저장하기", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        custom_emotions_json = json.dumps(custom_emotions_data, ensure_ascii=False)
        cursor.execute('''
            INSERT OR REPLACE INTO emotion_logs 
            (date, time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread, custom_emotions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(log_date), time_slot, chosen_emoji, depression, anxiety, anger, joy, fear, dread, custom_emotions_json))
        conn.commit()
        conn.close()
        st.success(f"🎉 {time_slot}의 모든 감정이 저장되었습니다!")
        st.session_state.custom_emotion_count = 0

# ==========================================
# 3. 24시간 일과 기록 (원그래프 블럭 터치 방식 개편)
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
    df_act['label'] = df_act['hour'].apply(lambda x: f"{x}시~{x+1}시")

    color_map = {"수면": "blue", "집중": "yellow", "핸드폰 및 딴짓": "red", "미기록": "lightgray"}
    
    st.subheader("📊 오늘의 시간 원그래프")
    st.caption("👇 원그래프의 조각(블럭)을 터치해보세요. 해당 시간대의 상세 내용을 확인하거나 수정할 수 있습니다.")
    
    df_act['size'] = 1  # 24시간 공평하게 배분
    
    # 💡 터치 이벤트를 지원하는 파이 차트 정의
    fig_pie = px.pie(
        df_act, values='size', names='label', color='activity_type',
        color_discrete_map=color_map, hole=0.5,
        title=f"{activity_date} 일과 흐름 (24개 블럭)"
    )
    fig_pie.update_traces(textinfo='label', sort=False, hovertemplate="<b>%{label}</b><br>상태: %{customdata[0]}<br>내용: %{customdata[1]}")
    fig_pie.update_traces(customdata=df_act[['activity_type', 'memo']].values)
    
    # 💡 스트림릿 컴포넌트의 클릭 이벤트 추출 활용
    selected_points = st.plotly_chart(fig_pie, use_container_width=True, on_select="rerun")
    
    # 기본 수정 타겟 시간대 지정 (원그래프 조각 클릭 시 해당 시간으로 자동 점프)
    target_hour = 0
    if selected_points and "selection" in selected_points and "points" in selected_points["selection"] and len(selected_points["selection"]["points"]) > 0:
        point_index = selected_points["selection"]["points"][0]["point_number"]
        target_hour = int(df_act.iloc[point_index]['hour'])
        st.success(f"🎯 원그래프에서 **[{target_hour}시 ~ {target_hour+1}시]** 블럭이 터치 선택되었습니다!")
    else:
        # 클릭 안 했을 때는 셀렉트 박스로 보완
        st.markdown("---")
        select_hour = st.selectbox("원그래프 블럭 대신 아래에서 수동으로 시간대를 고르실 수도 있습니다", [f"{h}시 ~ {h+1}시" for h in range(24)], index=0)
        target_hour = int(select_hour.split("시")[0])

    current_status = df_act[df_act['hour'] == target_hour].iloc[0]
    
    st.markdown(f"### ✍️ {target_hour}시 ~ {target_hour+1}시 상태 편집")
    
    # 현재 상태 매핑 인덱스 확보
    type_options = ["수면", "집중", "핸드폰 및 딴짓", "미기록"]
    try:
        default_idx = type_options.index(current_status['activity_type'])
    except ValueError:
        default_idx = 3
        
    act_type = st.radio("유형 선택", type_options, index=default_idx)
    memo_text = st.text_input("간단히 한 일을 적어주세요", value=current_status['memo'], key=f"memo_{target_hour}")
    
    if st.button("💾 이 조각에 정보 저장하기", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_activities (date, hour, activity_type, memo)
            VALUES (?, ?, ?, ?)
        ''', (str(activity_date), target_hour, act_type, memo_text))
        conn.commit()
        conn.close()
        st.success(f"💾 {target_hour}시 일과 저장 완료!")
        st.rerun()

# ==========================================
# 4. 분석 리포트 화면 (명시적 데이터 매핑으로 에러 완벽 해결)
# ==========================================
elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 분석 대시보드")
    search_date = st.date_input("조회할 날짜 선택", datetime.today())
    
    conn = sqlite3.connect(DB_FILE)
    df_emotion = pd.read_sql_query("SELECT date, time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread, custom_emotions FROM emotion_logs WHERE date = ?", conn, params=(str(search_date),))
    conn.close()
    
    if df_emotion.empty:
        st.warning("선택한 날짜에 감정 기록이 없습니다. '오늘의 감정 기록' 탭에서 먼저 데이터를 입력해 주세요!")
    else:
        st.subheader(f"📅 {search_date} 일일 감정 그래프")
        
        # 순서 정렬
        df_emotion['time_slot'] = pd.Categorical(df_emotion['time_slot'], categories=["11시", "15시", "19시", "24시"], ordered=True)
        df_emotion = df_emotion.sort_values('time_slot')
        
        # 💡 [에러 해결 해결의 핵심] 한글 컬럼 이름 명시 매핑 및 보장
        df_emotion = df_emotion.rename(columns={
            'depression': '우울', 'anxiety': '불안', 'anger': '분노',
            'joy': '기쁨', 'fear': '공포', 'dread': '무서움'
        })
        
        base_emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        
        # melt 안전 구조 변환
        df_melted = df_emotion.melt(
            id_vars=['time_slot', 'emotion_word'], 
            value_vars=base_emotions, 
            var_name='감정 종류', 
            value_name='점수(%)'
        )
        
        fig_line = px.line(
            df_melted, x='time_slot', y='점수(%)', color='감정 종류', 
            markers=True, title="시간대별 6대 감정 변화 선그래프"
        )
        fig_line.update_layout(yaxis=dict(range=[-5, 105]))
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.subheader("✨ 내가 추가했던 특별한 감정 및 표정")
        for _, row in df_emotion.iterrows():
            st.write(f"⏱️ **{row['time_slot']} 선택 표정**: {row['emotion_word']}")
            if row['custom_emotions']:
                try:
                    custom_data = json.loads(row['custom_emotions'])
                    if custom_data:
                        items_str = ", ".join([f"[{k}: {v}%]" for k, v in custom_data.items()])
                        st.write(f" └─ 추가 커스텀 감정: {items_str}")
                except:
                    pass

    st.markdown("---")
    st.subheader("🕸️ 주간 감정 밸런스 (최근 7일 레이더 차트)")
    
    one_week_ago = search_date - timedelta(days=7)
    conn = sqlite3.connect(DB_FILE)
    df_week = pd.read_sql_query("SELECT depression, anxiety, anger, joy, fear, dread FROM emotion_logs WHERE date >= ?", conn, params=(str(one_week_ago),))
    conn.close()
    
    if df_week.empty:
        st.info("지난 7일간 저장된 감정 데이터 요약이 없습니다. 더 많은 일수의 배터리를 채워주세요!")
    else:
        df_week = df_week.rename(columns={
            'depression': '우울', 'anxiety': '불안', 'anger': '분노',
            'joy': '기쁨', 'fear': '공포', 'dread': '무서움'
        })
        base_emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        mean_scores = df_week[base_emotions].mean()
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=mean_scores.values, theta=mean_scores.index, fill='toself', name='주간 평균'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
        st.plotly_chart(fig_radar, use_container_width=True)
