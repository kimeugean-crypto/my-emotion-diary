import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import json
import calendar
import time
from datetime import datetime, timedelta

# ==========================================
# 0. 데이터베이스(DB) 구조 업데이트 및 초기화
# ==========================================
DB_FILE = "emotion_diary_v11.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, time_slot TEXT, emotion_word TEXT,
            depression INTEGER, anxiety INTEGER, anger INTEGER,
            joy INTEGER, fear INTEGER, dread INTEGER,
            custom_emotions TEXT,
            q1_moment TEXT, q2_thought TEXT,
            sentence_reason TEXT, sentence_result TEXT,
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_reviews (
            date TEXT PRIMARY KEY,
            reflection TEXT, improvement TEXT, praise TEXT, repr_emoji TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coping_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, strategy_text TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_goals (
            date TEXT PRIMARY KEY,
            today_goal_1 TEXT, today_goal_1_done INTEGER,
            today_goal_2 TEXT, today_goal_2_done INTEGER,
            week_habit_1 TEXT, week_habit_1_done INTEGER,
            week_habit_2 TEXT, week_habit_2_done INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 1. 공통 에셋 및 설정
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기", layout="centered")
st.title("🧠 내 마음과 하루 기록기")

menu = st.sidebar.radio("메뉴 선택", [
    "오늘의 감정 기록", 
    "24시간 일과 기록", 
    "집중 및 휴식 타이머 ⏱️",
    "일일/주간 분석 리포트", 
    "나만의 감정 극복법"
])

EMOJI_LIST = ["😊", "🥳", "😎", "🥱", "😑", "😤", "😥", "😰", "😨", "🤔"]

def render_custom_battery(label, score):
    is_positive = "기쁨" in label or "joy" in label.lower()
    if is_positive:
        if score >= 80: status = "🔋 가득 참 (최상)"
        elif score >= 40: status = "🪫 중간 (유지 필요)"
        else: status = "🔌 방전 임박 (충전 필요!)"
    else:
        if score >= 70: status = "🪫 방전 임박 (스트레스 과부하!)"
        elif score >= 35: status = "⚠️ 주의 (감정 소모 중)"
        else: status = "🔋 안정 (완만함)"
    st.write(f"**{label}** : {score}% — *{status}*")
    st.progress(score / 100.0)

# ==========================================
# 2. 오늘의 감정 기록 화면
# ==========================================
if menu == "오늘의 감정 기록":
    st.header("📝 오늘의 감정 성찰 기록")
    
    col1, col2 = st.columns(2)
    with col1: 
        log_date = st.date_input("기록 날짜", datetime.today())
    with col2: 
        hours_options = [f"{h:02d}:00" for h in range(24)]
        time_slot = st.selectbox("기록 시간대 선택", hours_options)
        
    st.markdown("---")
    st.subheader("1. 마음 들여다보기")
    q1_moment = st.text_area("❓ 내가 구실을 만들기 시작한 순간은 언제인가요?", placeholder="예: 해야 할 공부를 미루고 다른 것을 보려 할 때", height=70)
    q2_thought = st.text_area("❓ 그때 내 머릿속을 스쳤던 생각은 무엇인가요?", placeholder="예: '조금만 이따 해도 시간 충분해'", height=70)
    
    st.markdown("---")
    st.subheader("2. 현재 내 표정 고르기")
    chosen_emoji = st.radio("지금 상태와 가장 어울리는 얼굴 이모티콘을 터치하세요", EMOJI_LIST, horizontal=True)
    st.markdown(f"<h1 style='text-align: center; font-size: 80px; margin: 0;'>{chosen_emoji}</h1>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("3. 감정 배터리 잔량 입력 (% 직접 기입)")
    c1, c2 = st.columns(2)
    with c1:
        joy = st.number_input("기쁨 (Joy) %", 0, 100, 50, 5)
        depression = st.number_input("우울 (Depression) %", 0, 100, 10, 5)
        anxiety = st.number_input("불안 (Anxiety) %", 0, 100, 10, 5)
    with c2:
        anger = st.number_input("분노 (Anger) %", 0, 100, 0, 5)
        fear = st.number_input("공포 (Fear) %", 0, 100, 0, 5)
        dread = st.number_input("무서움 (Dread) %", 0, 100, 0, 5)
        
    if "custom_emotion_count" not in st.session_state:
        st.session_state.custom_emotion_count = 0
    if st.button("✨ 기본 외 나만의 감정 단어 추가하기"):
        st.session_state.custom_emotion_count += 1

    custom_emotions_data = {}
    if st.session_state.custom_emotion_count > 0:
        for i in range(st.session_state.custom_emotion_count):
            cc1, cc2 = st.columns(2)
            with cc1: c_name = st.text_input(f"감정 이름 (#_{i+1})", key=f"c_name_{i}")
            with cc2: c_score = st.number_input(f"수치 (#_{i+1}) %", 0, 100, 50, 5, key=f"c_score_{i}")
            if c_name.strip():
                custom_emotions_data[c_name.strip()] = c_score

    st.markdown("#### 📊 실시간 내 감정 배터리 계산기")
    v_col1, v_col2 = st.columns(2)
    with v_col1:
        render_custom_battery("기쁨", joy)
        render_custom_battery("우울", depression)
        render_custom_battery("불안", anxiety)
    with v_col2:
        render_custom_battery("분노", anger)
        render_custom_battery("공포", fear)
        render_custom_battery("무서움", dread)
        
    if custom_emotions_data:
        for name, score in custom_emotions_data.items():
            render_custom_battery(name, score)

    st.markdown("---")
    st.subheader("4. 구실과 결과 마주하기")
    sc1, sc2 = st.columns(2)
    with sc1: sentence_reason = st.text_input("그때 내가 구실을 만든 이유는 [ ______ ] 때문이다.", placeholder="예: 귀찮고 에너지가 부족했기")
    with sc2: sentence_result = st.text_input("하지만 그 결과 나는 [ ______ ]를 느꼈다.", placeholder="예: 약간의 후회와 스트레스")

    st.markdown("---")
    st.subheader("🌱 5. 나를 다독이는 확언 한 줄")
    target_affirmation = "완벽하지 않아도 괜찮아. 나는 시도하고 있다."
    st.info(f"따라 쓰실 문장: **{target_affirmation}**")
    user_affirmation = st.text_input("위 문장을 자유롭게 적거나 다짐을 입력해 보세요.", placeholder="편하게 적어보세요.")

    if st.button("🔓 모든 성찰 일기 저장하기", use_container_width=True):
        if not q1_moment.strip() or not q2_thought.strip():
            st.error("❌ 마음 성찰 질문(STEP 1)을 작성해 주세요!")
        elif not sentence_reason.strip() or not sentence_result.strip():
            st.error("❌ 문장 빈칸 채우기(STEP 4)를 완료해 주세요!")
        else:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            custom_emotions_json = json.dumps(custom_emotions_data, ensure_ascii=False)
            
            cursor.execute('''
                INSERT OR REPLACE INTO emotion_logs 
                (date, time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread, custom_emotions, q1_moment, q2_thought, sentence_reason, sentence_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (str(log_date), time_slot, chosen_emoji, depression, anxiety, anger, joy, fear, dread, custom_emotions_json, q1_moment, q2_thought, sentence_reason, sentence_result))
            conn.commit()
            conn.close()
            
            st.success(f"❤️ 대견합니다. {time_slot} 기준의 마음 성찰 기록이 안전하게 저장되었습니다.")
            st.session_state.custom_emotion_count = 0

# ==========================================
# 3. 24시간 일과 기록 화면 (★집중 유형 초록색 세팅★)
# ==========================================
elif menu == "24시간 일과 기록":
    st.header("🕒 24시간 타임 루프 기록")
    activity_date = st.date_input("일과 기록 날짜 선택", datetime.today())
    
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
    df_act['size'] = 1  
    
    def make_display_text(row):
        time_range = f"{int(row['hour']):02d}:00~{int(row['hour'])+1:02d}:00"
        if row['memo'] and row['memo'].strip() != "":
            return f"{time_range}<br><b>📝 {row['memo']}</b>"
        return f"{time_range}"
        
    df_act['display_text'] = df_act.apply(make_display_text, axis=1)

    # 💡 [집중 컬러 변경]: "집중" 유형의 고유 색상을 주황색에서 선명하고 밝은 초록색(#2ECC71)으로 수정
    color_map = {"수면": "#4A90E2", "집중": "#2ECC71", "핸드폰 및 딴짓": "#E24A4A", "미기록": "#EAEAEA"}
    df_act['color'] = df_act['activity_type'].map(color_map)

    st.subheader("📊 오늘의 시간 시계 원그래프")
    
    fig_clock = go.Figure(data=[go.Pie(
        labels=df_act['display_text'],
        values=df_act['size'],
        marker=dict(colors=df_act['color'], line=dict(color='#FFFFFF', width=2)),
        hole=0.45,
        sort=False,                      
        direction='clockwise',           
        rotation=90,                     
        textinfo='text',                 
        text=df_act['display_text'],      
        textposition='inside',           
        insidetextorientation='radial',  
        hovertemplate="<b>%{label}</b><br>유형: %{customdata}<extra></extra>",
        customdata=df_act['activity_type']
    )])
    
    fig_clock.update_layout(
        showlegend=False,                
        margin=dict(t=20, b=20, l=20, r=20),
        height=520
    )
    
    selected_points = st.plotly_chart(fig_clock, use_container_width=True, on_select="rerun")
    target_hour = None

    if selected_points and "selection" in selected_points and "points" in selected_points["selection"] and len(selected_points["selection"]["points"]) > 0:
        point_index = selected_points["selection"]["points"][0]["point_number"]
        target_hour = int(df_act.iloc[point_index]['hour'])
        st.success(f"🎯 선택된 블럭: **[{target_hour:02d}:00 ~ {target_hour+1:02d}:00]**")

    st.markdown("---")
    
    if target_hour is None:
        st.info("💡 위의 시계 조각을 직접 터치하거나 아래 메뉴를 통해 편집할 시간 범위를 정해주세요.")
        with st.expander("🔍 직접 시간 범위 선택해서 편집창 열기"):
            range_options = [f"{h:02d}:00~{h+1:02d}:00" for h in range(24)]
            select_range = st.selectbox("편집할 시간 범위 선택", range_options, index=0)
            if st.button("🔓 선택한 시간 편집창 열기"):
                st.session_state["mobile_target_hour"] = int(select_range.split(":")[0])
        
        if "mobile_target_hour" in st.session_state:
            target_hour = st.session_state["mobile_target_hour"]

    if target_hour is not None:
        current_status = df_act[df_act['hour'] == target_hour].iloc[0]
        st.markdown(f"### ✍️ {target_hour:02d}:00 ~ {target_hour+1:02d}:00 내용 기록 편집")
        
        type_options = ["수면", "집중", "핸드폰 및 딴짓", "미기록"]
        try: default_idx = type_options.index(current_status['activity_type'])
        except: default_idx = 3
            
        act_type = st.radio("행동 유형 설정(색상 변경)", type_options, index=default_idx)
        memo_text = st.text_input("💡 이 시간대에 내가 한 일 기록하기 (그래프 위에 바로 나타납니다)", value=current_status['memo'])
        
        if st.button("💾 이 시간 조각 저장하고 그래프 반영하기", use_container_width=True):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_activities (date, hour, activity_type, memo)
                VALUES (?, ?, ?, ?)
            ''', (str(activity_date), target_hour, act_type, memo_text))
            conn.commit()
            conn.close()
            st.success("그래프에 즉시 반영되었습니다!")
            if "mobile_target_hour" in st.session_state:
                del st.session_state["mobile_target_hour"]
            st.rerun()

    st.markdown("---")
    
    st.subheader("🎯 오늘의 목표 및 이번 주 습관 관리")
    conn = sqlite3.connect(DB_FILE)
    df_goals = pd.read_sql_query("SELECT * FROM daily_goals WHERE date = ?", conn, params=(str(activity_date),))
    conn.close()
    
    if not df_goals.empty:
        g_data = df_goals.iloc[0]
    else:
        g_data = {"today_goal_1":"", "today_goal_1_done":0, "today_goal_2":"", "today_goal_2_done":0,
                  "week_habit_1":"", "week_habit_1_done":0, "week_habit_2":"", "week_habit_2_done":0}
                  
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("##### 📌 오늘의 목표")
        g1_text = st.text_input("목표 1", value=g_data["today_goal_1"], placeholder="예: 책 20페이지 읽기")
        g1_done = st.checkbox("목표 1 완료 여부", value=bool(g_data["today_goal_1_done"]), key="g1")
        
        g2_text = st.text_input("목표 2", value=g_data["today_goal_2"], placeholder="예: 홈트레이닝 30분")
        g2_done = st.checkbox("목표 2 완료 여부", value=bool(g_data["today_goal_2_done"]), key="g2")
        
    with col_g2:
        st.markdown("##### 🌱 이번 주 습관으로 만들 목표")
        h1_text = st.text_input("주간 습관 1", value=g_data["week_habit_1"], placeholder="예: 아침 물 한 잔 마시기")
        h1_done = st.checkbox("습관 1 오늘 실천 여부", value=bool(g_data["week_habit_1_done"]), key="h1")
        
        h2_text = st.text_input("주간 습관 2", value=g_data["week_habit_2"], placeholder="예: 외국어 단어 5개 암기")
        h2_done = st.checkbox("습관 2 오늘 실천 여부", value=bool(g_data["week_habit_2_done"]), key="h2")

    total_goals_count = sum([1 for x in [g1_text, g2_text, h1_text, h2_text] if x.strip() != ""])
    done_goals_count = sum([1 for text, checked in [(g1_text, g1_done), (g2_text, g2_done), (h1_text, h1_done), (h2_text, h2_done)] if text.strip() != "" and checked])
    current_achievement_rate = int((done_goals_count / total_goals_count) * 100) if total_goals_count > 0 else 0
    st.write(f"📊 현재 선택된 날짜의 실시간 목표 달성률: **{current_achievement_rate}%**")

    if st.button("💾 목표 및 습관 진행 상황 저장", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_goals 
            (date, today_goal_1, today_goal_1_done, today_goal_2, today_goal_2_done, week_habit_1, week_habit_1_done, week_habit_2, week_habit_2_done)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(activity_date), g1_text, int(g1_done), g2_text, int(g2_done), h1_text, int(h1_done), h2_text, int(h2_done)))
        conn.commit()
        conn.close()
        st.success("🎯 목표 및 습관 데이터가 저장되었습니다!")

    st.markdown("---")
    st.subheader("🏁 오늘의 종합 하루 회고")
    conn = sqlite3.connect(DB_FILE)
    df_rev = pd.read_sql_query("SELECT * FROM daily_reviews WHERE date = ?", conn, params=(str(activity_date),))
    conn.close()
    
    exist_review = df_rev.iloc[0] if not df_rev.empty else {"reflection":"", "improvement":"", "praise":"", "repr_emoji":"😊"}
    
    rev_reflection = st.text_area("1. 🤔 오늘의 반성", value=exist_review["reflection"], placeholder="오늘 아쉬웠던 점을 적어주세요.")
    rev_improvement = st.text_area("2. 🚀 내일 더 나아지기 위해 할 것", value=exist_review["improvement"], placeholder="내일 시도해 볼 계획을 적어주세요.")
    rev_praise = st.text_area("3. 🎉 오늘의 칭찬", value=exist_review["praise"], placeholder="나 자신에게 건네는 따뜻한 칭찬 한마디를 적어주세요.")
    
    try: emoji_idx = EMOJI_LIST.index(exist_review["repr_emoji"])
    except: emoji_idx = 0
    repr_emoji = st.selectbox("🎯 오늘 하루 나의 전체적인 상태 이모티콘 고르기", EMOJI_LIST, index=emoji_idx)
    
    if st.button("🔔 오늘의 종합 회고 저장 완료", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_reviews (date, reflection, improvement, praise, repr_emoji)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(activity_date), rev_reflection, rev_improvement, rev_praise, repr_emoji))
        conn.commit()
        conn.close()
        st.success("📝 하루의 회고가 안전하게 마감되었습니다!")

# ==========================================
# 4. 집중 및 휴식 타이머 화면
# ==========================================
elif menu == "집중 및 휴식 타이머 ⏱️":
    st.header("⏱️ 몰입과 휴식을 위한 마인드 타이머")
    st.write("의도적인 집중과 확실한 휴식을 분리하여 시간을 지배해 보세요.")

    timer_mode = st.radio("⏰ 타이머 모드 선택", ["🔥 집중/공부 모드", "🌴 휴식/놀이 모드"], horizontal=True)

    if timer_mode == "🔥 집중/공부 모드":
        st.info("💡 추천 집중 시간: **25분** (뽀모도로 기법)")
        default_minutes = 25
    else:
        st.info("💡 추천 휴식 시간: **5분** 또는 **15분**")
        default_minutes = 5

    duration_min = st.slider("⏱️ 타이머 설정 시간 (분 단위)", min_value=1, max_value=60, value=default_minutes)
    total_seconds = duration_min * 60

    if st.button("🎬 타이머 시작하기", use_container_width=True):
        st.warning(f"⏳ **{duration_min}분** 동안 {timer_mode} 타이머가 작동 중입니다.")
        countdown_text = st.empty()
        progress_bar = st.progress(0.0)
        
        for remaining in range(total_seconds, -1, -1):
            mins, secs = divmod(remaining, 60)
            countdown_text.markdown(f"<h1 style='text-align: center; font-size: 60px;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            progress_ratio = (total_seconds - remaining) / total_seconds
            progress_bar.progress(progress_ratio)
            time.sleep(1)
            
        st.balloons()
        if timer_mode == "🔥 집중/공부 모드":
            st.success("🎉 고생하셨습니다! 집중 시간이 끝났습니다. 이제 달콤한 휴식을 즐기세요!")
        else:
            st.success("📢 휴식 시간이 끝났습니다! 이제 다시 멋지게 집중 모드로 복귀해 볼까요?")

# ==========================================
# 5. 일일/주간 분석 리포트 (★기록 조회 아카이브 보강★)
# ==========================================
elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 및 목표 분석 대시보드")
    
    # 탭 기능 분리: 차트 대시보드 / 과거 기록 조회
    tab1, tab2 = st.tabs(["📉 감정 통계 & 캘린더", "📜 과거 성찰 일기 & 하루 회고 모아보기"])
    
    with tab1:
        st.subheader("📅 나의 하루 감정 & 목표 달성률 달력")
        now = datetime.now()
        col_y, col_m = st.columns(2)
        with col_y: select_year = st.selectbox("연도 선택", [2026, 2027], index=0)
        with col_m: select_month = st.selectbox("월 선택", list(range(1, 13)), index=now.month - 1)
        
        conn = sqlite3.connect(DB_FILE)
        df_all_rev = pd.read_sql_query("SELECT date, repr_emoji FROM daily_reviews", conn)
        df_all_goals = pd.read_sql_query("SELECT * FROM daily_goals", conn)
        conn.close()
        
        calendar_data_map = {}
        for _, r in df_all_rev.iterrows():
            try:
                d_obj = datetime.strptime(r['date'], "%Y-%m-%d")
                if d_obj.year == select_year and d_obj.month == select_month:
                    if d_obj.day not in calendar_data_map:
                        calendar_data_map[d_obj.day] = {"emoji": "⠀", "rate": None}
                    calendar_data_map[d_obj.day]["emoji"] = r['repr_emoji']
            except: pass
            
        for _, g in df_all_goals.iterrows():
            try:
                d_obj = datetime.strptime(g['date'], "%Y-%m-%d")
                if d_obj.year == select_year and d_obj.month == select_month:
                    if d_obj.day not in calendar_data_map:
                        calendar_data_map[d_obj.day] = {"emoji": "⠀", "rate": None}
                    total = sum([1 for x in [g["today_goal_1"], g["today_goal_2"], g["week_habit_1"], g["week_habit_2"]] if x and x.strip() != ""])
                    done = sum([1 for t, d in [(g["today_goal_1"], g["today_goal_1_done"]), (g["today_goal_2"], g["today_goal_2_done"]), (g["week_habit_1"], g["week_habit_1_done"]), (g["week_habit_2"], g["week_habit_2_done"])] if t and t.strip() != "" and d == 1])
                    rate_percent = int((done / total) * 100) if total > 0 else 0
                    calendar_data_map[d_obj.day]["rate"] = rate_percent
            except: pass
            
        cal = calendar.monthcalendar(select_year, select_month)
        days_headers = ["월", "화", "수", "목", "금", "토", "일"]
        
        cal_html = "<table style='width:100%; border-collapse: collapse; text-align:center; font-size:14px;'>"
        cal_html += "<tr style='background-color:#f0f2f6; font-weight:bold;'>" + "".join([f"<th style='padding:8px; border:1px solid #ddd;'>{d}</th>" for d in days_headers]) + "</tr>"
        
        for week in cal:
            cal_html += "<tr>"
            for day in week:
                if day == 0:
                    cal_html += "<td style='padding:15px; border:1px solid #ddd; background-color:#fafafa;'></td>"
                else:
                    day_data = calendar_data_map.get(day, {"emoji": "⠀", "rate": None})
                    sticker = day_data["emoji"]
                    rate_str = f"<span style='font-size:11px; color:#2E7D32; font-weight:normal;'><br>🎯달성:{day_data['rate']}%</span>" if day_data["rate"] is not None else ""
                    
                    cal_html += f"<td style='padding:8px; border:1px solid #ddd; font-weight:bold; height:75px; vertical-align:top;'>"
                    cal_html += f"{day}<br><span style='font-size:20px;'>{sticker}</span>{rate_str}"
                    cal_html += f"</td>"
            cal_html += "</tr>"
        cal_html += "</table>"
        
        st.markdown(cal_html, unsafe_allow_html=True)
        st.markdown("---")
        
        search_date = st.date_input("상세 타임라인 조회 날짜 선택", datetime.today())
        conn = sqlite3.connect(DB_FILE)
        df_emotion = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ?", conn, params=(str(search_date),))
        conn.close()
        
        if not df_emotion.empty:
            st.subheader(f"📅 {search_date} 시간대별 실시간 감정 스펙트럼")
            rename_dict = {}
            for old, new in [('depression','우울'),('anxiety','불안'),('anger','분노'),('joy','기쁨'),('fear','공포'),('dread','무서움')]:
                if old in df_emotion.columns:
                    rename_dict[old] = new
            df_emotion = df_emotion.rename(columns=rename_dict)
            df_emotion = df_emotion.sort_values('time_slot')
            
            present_emotions = [c for c in ['우울', '불안', '분노', '기쁨', '공포', '무서움'] if c in df_emotion.columns]
            df_melted = df_emotion.melt(id_vars=['time_slot'], value_vars=present_emotions, var_name='감정 종류', value_name='점수(%)')
            
            fig_line = px.line(df_melted, x='time_slot', y='점수(%)', color='감정 종류', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

    # 💡 [과거 기록 아카이브 보강]: 작성한 감정 성찰일지와 종합 회고를 날짜별로 항시 로드해 볼 수 있는 아카이브 뷰어 구현
    with tab2:
        st.subheader("📜 날짜별 전체 일지 아카이브 히스토리")
        archive_date = st.date_input("조회할 날짜 선택", datetime.today(), key="archive_date_picker")
        
        conn = sqlite3.connect(DB_FILE)
        df_emo_history = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ? ORDER BY time_slot ASC", conn, params=(str(archive_date),))
        df_rev_history = pd.read_sql_query("SELECT * FROM daily_reviews WHERE date = ?", conn, params=(str(archive_date),))
        conn.close()
        
        st.markdown(f"### 📅 {archive_date} 기록 열람결과")
        
        # 1. 감정 성찰 일지 히스토리 출력
        st.markdown("#### 🪵 시간대별 감정 성찰 일지")
        if df_emo_history.empty:
            st.info("해당 날짜에 작성된 시간대별 감정 성찰 기록이 없습니다.")
        else:
            for idx, row in df_emo_history.iterrows():
                with st.expander(f"⏰ {row['time_slot']} | 표정 상태: {row['emotion_word']}"):
                    st.write(f"**❓ 구실을 만들기 시작한 순간:**\n> {row['q1_moment']}")
                    st.write(f"**❓ 내 머릿속을 스쳤던 생각:**\n> {row['q2_thought']}")
                    st.write(f"**📊 감정 수치 상태:**\n- 기쁨: {row['joy']}% | 우울: {row['depression']}% | 불안: {row['anxiety']}% | 분노: {row['anger']}%")
                    st.write(f"**🌱 인과 마주하기 문장:**\n- 그때 내가 구실을 만든 이유는 **[{row['sentence_reason']}]** 때문이다.\n- 하지만 그 결과 나는 **[{row['sentence_result']}]**를 느꼈다.")
        
        st.markdown("---")
        
        # 2. 종합 하루 회고 히스토리 출력
        st.markdown("#### 🏁 마감 하루 종합 회고")
        if df_rev_history.empty:
            st.info("해당 날짜에 작성된 하루 마감 종합 회고가 없습니다. 일과 기록 메뉴 하단에서 작성할 수 있습니다.")
        else:
            rev_data = df_rev_history.iloc[0]
            st.success(f"🎯 오늘 하루 전체적인 대표 이모티콘 상태: {rev_data['repr_emoji']}")
            st.info(f"**🤔 1. 오늘의 반성**\n\n{rev_data['reflection']}")
            st.warning(f"**🚀 2. 내일 더 나아지기 위해 할 것**\n\n{rev_data['improvement']}")
            st.help(f"**🎉 3. 오늘의 칭찬**\n\n{rev_data['praise']}")

# ==========================================
# 6. 나만의 감정 극복법
# ==========================================
elif menu == "나만의 감정 극복법":
    st.header("🩹 나만의 감정 극복 치트키 아카이브")
    st.write("불안, 우울, 혹은 권태(지루함)가 찾아오는 위기 순간에 나를 구해줄 행동 강령을 축적해 두세요.")
    
    with st.form("strategy_form", clear_on_submit=True):
        category = st.selectbox("어떤 감정을 물리칠 방법인가요?", ["불안 극복법 😰", "우울 극복법 😥", "지루함 극복법 😑"])
        strategy_text = st.text_input("나에게 효과적인 나만의 구체적인 액션 지침은?", placeholder="예: 무작정 유튜브를 끄고 5분간 숨쉬기 운동하기")
        submitted = st.form_submit_button("🚀 나만의 처방전에 등록하기")
        
        if submitted and strategy_text.strip():
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO coping_strategies (category, strategy_text) VALUES (?, ?)", (category, strategy_text.strip()))
            conn.commit()
            conn.close()
            st.success("🎯 나만의 멘탈 관리 처방전 데이터 리스트에 정상 추가되었습니다!")

    st.markdown("---")
    st.subheader("📜 누적된 나만의 멘탈 치트키 리스트")
    conn = sqlite3.connect(DB_FILE)
    df_strat = pd.read_sql_query("SELECT * FROM coping_strategies", conn)
    conn.close()
    
    if df_strat.empty:
        st.info("아직 등록된 극복 팁이 없습니다. 힘이 되는 행동 수칙을 먼저 적어보세요!")
    else:
        for cat in ["불안 극복법 😰", "우울 극복법 😥", "지루함 극복법 😑"]:
            sub_df = df_strat[df_strat['category'] == cat]
            if not sub_df.empty:
                st.markdown(f"#### **{cat}**")
                for idx, row in sub_df.iterrows():
                    st.info(f"✔️ {row['strategy_text']}")
