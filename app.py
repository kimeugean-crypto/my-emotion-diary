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
# 1. 데이터베이스(DB) 파일 및 테이블 자동 초기화
# ==========================================
DB_FILE = "local_emotion_diary_v1.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 감정 성찰 기록 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotion_logs (
            date TEXT, time_slot TEXT, emotion_word TEXT,
            depression INTEGER, anxiety INTEGER, anger INTEGER,
            joy INTEGER, fear INTEGER, dread INTEGER,
            custom_emotions TEXT, q1_moment TEXT, q2_thought TEXT,
            sentence_reason TEXT, sentence_result TEXT, affirmation TEXT,
            PRIMARY KEY (date, time_slot)
        )
    ''')
    # 24시간 일과 기록 테이블 (기존 오늘 일과 + 내일 예상/희망 일과 통합 관리)
    # plan_type: 'actual'(오늘 실제), 'expected'(내일 예상), 'wanted'(내일 희망)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_activities (
            date TEXT, hour INTEGER, activity_type TEXT, memo TEXT, plan_type TEXT DEFAULT 'actual',
            PRIMARY KEY (date, hour, plan_type)
        )
    ''')
    # 하루 종합 회고 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_reviews (
            date TEXT PRIMARY KEY,
            reflection TEXT, improvement TEXT, praise TEXT, repr_emoji TEXT
        )
    ''')
    # 목표 및 습관 관리 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_goals (
            date TEXT PRIMARY KEY,
            today_goal_1 TEXT, today_goal_1_done INTEGER,
            today_goal_2 TEXT, today_goal_2_done INTEGER,
            week_habit_1 TEXT, week_habit_1_done INTEGER,
            week_habit_2 TEXT, week_habit_2_done INTEGER
        )
    ''')
    # 감정 극복 처방전 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coping_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, strategy_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

# 앱 실행 시 DB 세팅
init_db()

# ==========================================
# 2. 공통 에셋 및 화면 레이아웃
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기 (로컬 영구 저장형)", layout="centered")
st.title("🧠 내 마음과 하루 기록기")
st.caption("🔒 본 기기 내부 하드디스크에 데이터가 안전하게 영구 보관되는 로컬 전용 모드입니다.")

menu = st.sidebar.radio("메뉴 선택", [
    "오늘의 감정 기록", 
    "24시간 일과 기록", 
    "집중 및 휴식 타이머 ⏱️",
    "일일/주간 분석 리포트", 
    "나만의 감정 극복법"
])

EMOJI_LIST = ["😊", "🥳", "😎", "🥱", "😑", "😤", "😥", "😰", "😨", "🤔"]
COLOR_MAP = {"수면": "#4A90E2", "집중": "#2ECC71", "핸드폰 및 딴짓": "#E24A4A", "미기록": "#EAEAEA"}

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

# 시계 그래프를 그려주는 공통 함수
def draw_clock_chart(df, title_label):
    def make_display_text(row):
        time_range = f"{int(row['hour']):02d}:00~{int(row['hour'])+1:02d}:00"
        if row['memo'] and row['memo'].strip() != "":
            return f"{time_range}<br><b>📝 {row['memo']}</b>"
        return f"{time_range}"
        
    df['display_text'] = df.apply(make_display_text, axis=1)
    df['color'] = df['activity_type'].map(COLOR_MAP)

    fig = go.Figure(data=[go.Pie(
        labels=df['display_text'], values=df['size'],
        marker=dict(colors=df['color'], line=dict(color='#FFFFFF', width=2)),
        hole=0.45, sort=False, direction='clockwise', rotation=90,
        textinfo='text', text=df['display_text'], textposition='inside',
        insidetextorientation='radial', hovertemplate="<b>%{label}</b><br>유형: %{customdata}<extra></extra>",
        customdata=df['activity_type']
    )])
    fig.update_layout(
        title=dict(text=title_label, x=0.5, font=dict(size=16,面="bold")),
        showlegend=False, 
        margin=dict(t=50, b=20, l=20, r=20), 
        height=450
    )
    return fig

# ==========================================
# 3. 오늘의 감정 기록 화면
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
    sentence_reason = st.text_input("그때 내가 구실을 만든 이유는 [ ______ ] 때문이다.", placeholder="예: 귀찮고 에너지가 부족했기")
    sentence_result = st.text_input("하지만 그 결과 나는 [ ______ ]를 느꼈다.", placeholder="예: 약간의 후회와 스트레스")

    st.markdown("---")
    st.subheader("🌱 5. 나를 다독이는 확언 한 줄")
    target_affirmation = "완벽하지 않아도 괜찮아. 나는 시도하고 있다."
    st.info(f"따라 쓰실 문장: **{target_affirmation}**")
    user_affirmation = st.text_input("위 문장을 자유롭게 적거나 다짐을 입력해 보세요.", placeholder="나를 다독이는 따뜻한 말을 남겨주세요.")

    if st.button("💾 기기에 성찰 일지 저장하기", use_container_width=True):
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
                (date, time_slot, emotion_word, depression, anxiety, anger, joy, fear, dread, custom_emotions, q1_moment, q2_thought, sentence_reason, sentence_result, affirmation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (str(log_date), time_slot, chosen_emoji, depression, anxiety, anger, joy, fear, dread, custom_emotions_json, q1_moment, q2_thought, sentence_reason, sentence_result, user_affirmation.strip()))
            conn.commit()
            conn.close()
            
            st.success(f"💾 기기 저장 완료! {time_slot} 기준의 감정 기록과 확언이 보관되었습니다.")
            st.session_state.custom_emotion_count = 0

# ==========================================
# 4. 24시간 일과 기록 화면
# ==========================================
elif menu == "24시간 일과 기록":
    st.header("🕒 24시간 타임 루프 기록")
    activity_date = st.date_input("일과 기록 날짜 선택", datetime.today())
    date_str = str(activity_date)
    
    # ----------------------------------------------------
    # [그래프 1] 오늘의 실제 시간 시계 원그래프 로드 및 시각화
    # ----------------------------------------------------
    conn = sqlite3.connect(DB_FILE)
    df_db_act = pd.read_sql_query("SELECT hour, activity_type, memo FROM daily_activities WHERE date = ? AND plan_type = 'actual'", conn, params=(date_str,))
    conn.close()
    
    db_acts = {row['hour']: {"activity_type": row['activity_type'], "memo": row['memo']} for _, row in df_db_act.iterrows()}
    rows = []
    for h in range(24):
        act_info = db_acts.get(h, {"activity_type": "미기록", "memo": ""})
        rows.append({"hour": h, "activity_type": act_info["activity_type"], "memo": act_info["memo"], "size": 1})
    df_act = pd.DataFrame(rows)
    
    st.subheader("📊 오늘의 실제 시간 시계 원그래프")
    fig_clock = draw_clock_chart(df_act, "오늘의 실제 행동 조각")
    selected_points = st.plotly_chart(fig_clock, use_container_width=True, on_select="rerun", key="today_clock_chart")
    
    target_hour = None
    target_plan_type = "actual"

    if selected_points and "selection" in selected_points and "points" in selected_points["selection"] and len(selected_points["selection"]["points"]) > 0:
        point_index = selected_points["selection"]["points"][0]["point_number"]
        target_hour = int(df_act.iloc[point_index]['hour'])
        target_plan_type = "actual"
        st.success(f"🎯 [오늘 실제 일과] 선택된 블럭: **[{target_hour:02d}:00 ~ {target_hour+1:02d}:00]**")

    # 오늘 일과 직접 편집 확장 창
    if target_hour is None:
        with st.expander("🔍 [오늘 실제 일과] 시간 직접 선택해서 편집하기"):
            range_options = [f"{h:02d}:00~{h+1:02d}:00" for h in range(24)]
            select_range = st.selectbox("편집할 시간 범위 선택", range_options, index=0, key="today_select_box")
            if st.button("🔓 선택한 시간 편집창 열기", key="today_open_btn"):
                st.session_state["mobile_target_hour"] = int(select_range.split(":")[0])
                st.session_state["mobile_target_type"] = "actual"
        if st.session_state.get("mobile_target_type") == "actual":
            target_hour = st.session_state.get("mobile_target_hour")
            target_plan_type = "actual"

    # 오늘 일과 저장 세션
    if target_hour is not None and target_plan_type == "actual":
        current_status = df_act[df_act['hour'] == target_hour].iloc[0]
        st.markdown(f"### ✍️ 오늘 실제 일과 [{target_hour:02d}:00 ~ {target_hour+1:02d}:00] 편집")
        type_options = ["수면", "집중", "핸드폰 및 딴짓", "미기록"]
        default_idx = type_options.index(current_status['activity_type']) if current_status['activity_type'] in type_options else 3
        act_type = st.radio("행동 유형 설정", type_options, index=default_idx, key="today_radio_act")
        memo_text = st.text_input("💡 내가 실제 한 일 기록 (비우면 삭제)", value=current_status['memo'], key="today_memo_act")
        
        if st.button("💾 이 시간 조각 오늘 일과에 반영", use_container_width=True, key="today_save_btn"):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_activities (date, hour, activity_type, memo, plan_type)
                VALUES (?, ?, ?, ?, 'actual')
            ''', (date_str, target_hour, act_type, memo_text))
            conn.commit()
            conn.close()
            st.success("✅ 오늘의 실제 시간 조각이 저장되었습니다!")
            if "mobile_target_hour" in st.session_state: del st.session_state["mobile_target_hour"]
            if "mobile_target_type" in st.session_state: del st.session_state["mobile_target_type"]
            st.rerun()

    # ----------------------------------------------------
    # 기존 기능: 목표 설정 및 주간 습관 / 오늘의 종합 하루 회고
    # ----------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 오늘의 목표 및 이번 주 습관 관리")
    conn = sqlite3.connect(DB_FILE)
    df_goals = pd.read_sql_query("SELECT * FROM daily_goals WHERE date = ?", conn, params=(date_str,))
    conn.close()
    g_data = df_goals.iloc[0].to_dict() if not df_goals.empty else {"today_goal_1":"","today_goal_1_done":0,"today_goal_2":"","today_goal_2_done":0,"week_habit_1":"","week_habit_1_done":0,"week_habit_2":"","week_habit_2_done":0}
                  
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("##### 📌 오늘의 목표")
        g1_text = st.text_input("목표 1", value=g_data.get("today_goal_1", ""), placeholder="예: 책 20페이지 읽기")
        g1_done = st.checkbox("목표 1 완료 여부", value=bool(g_data.get("today_goal_1_done", 0)), key="g1")
        g2_text = st.text_input("목표 2", value=g_data.get("today_goal_2", ""), placeholder="예: 홈트레이닝 30분")
        g2_done = st.checkbox("목표 2 완료 여부", value=bool(g_data.get("today_goal_2_done", 0)), key="g2")
    with col_g2:
        st.markdown("##### 🌱 이번 주 습관으로 만들 목표")
        h1_text = st.text_input("주간 습관 1", value=g_data.get("week_habit_1", ""), placeholder="예: 아침 물 한 잔 마시기")
        h1_done = st.checkbox("습관 1 오늘 실천 여부", value=bool(g_data.get("week_habit_1_done", 0)), key="h1")
        h2_text = st.text_input("주간 습관 2", value=g_data.get("week_habit_2", ""), placeholder="예: 외국어 단어 5개 암기")
        h2_done = st.checkbox("습관 2 오늘 실천 여부", value=bool(g_data.get("week_habit_2_done", 0)), key="h2")

    if st.button("💾 목표 및 습관 진행 상황 저장", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_goals (date, today_goal_1, today_goal_1_done, today_goal_2, today_goal_2_done, week_habit_1, week_habit_1_done, week_habit_2, week_habit_2_done)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date_str, g1_text, int(g1_done), g2_text, int(g2_done), h1_text, int(h1_done), h2_text, int(h2_done)))
        conn.commit()
        conn.close()
        st.success("🎯 목표 데이터가 성공적으로 저장되었습니다!")

    st.markdown("---")
    st.subheader("🏁 오늘의 종합 하루 회고")
    conn = sqlite3.connect(DB_FILE)
    df_rev = pd.read_sql_query("SELECT * FROM daily_reviews WHERE date = ?", conn, params=(date_str,))
    conn.close()
    exist_review = df_rev.iloc[0].to_dict() if not df_rev.empty else {"reflection":"", "improvement":"", "praise":"", "repr_emoji":"😊"}
    
    rev_reflection = st.text_area("1. 🤔 오늘의 반성", value=exist_review.get("reflection", ""), placeholder="오늘 아쉬웠던 점을 적어주세요.")
    rev_improvement = st.text_area("2. 🚀 내일 더 나아지기 위해 할 것", value=exist_review.get("improvement", ""), placeholder="내일 시도해 볼 계획을 적어주세요.")
    rev_praise = st.text_area("3. 🎉 오늘의 칭찬", value=exist_review.get("praise", ""), placeholder="나 자신에게 건네는 따뜻한 칭찬 한마디를 적어주세요.")
    try: emoji_idx = EMOJI_LIST.index(exist_review.get("repr_emoji", "😊"))
    except: emoji_idx = 0
    repr_emoji = st.selectbox("🎯 오늘 하루 나의 전체적인 상태 이모티콘 고르기", EMOJI_LIST, index=emoji_idx)
    
    if st.button("🔔 오늘의 종합 회고 저장 완료", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_reviews (date, reflection, improvement, praise, repr_emoji)
            VALUES (?, ?, ?, ?, ?)
        ''', (date_str, rev_reflection, rev_improvement, rev_praise, repr_emoji))
        conn.commit()
        conn.close()
        st.success("📝 하루 마감 데이터가 안전하게 저장되었습니다!")

    # ----------------------------------------------------
    # 🔥 [새로운 추가 기능] 내일의 하루 설계 시뮬레이션 원그래프 2개
    # ----------------------------------------------------
    st.markdown("---")
    st.header("🔮 내일의 하루 미리 그려보기 (시뮬레이션)")
    st.caption("회고를 마친 후, 내일의 타임라인을 두 가지 시선으로 미리 디자인해보세요.")
    
    # 데이터 로드 (예상 하루 / 보내고 싶은 하루)
    conn = sqlite3.connect(DB_FILE)
    df_db_expected = pd.read_sql_query("SELECT hour, activity_type, memo FROM daily_activities WHERE date = ? AND plan_type = 'expected'", conn, params=(date_str,))
    df_db_wanted = pd.read_sql_query("SELECT hour, activity_type, memo FROM daily_activities WHERE date = ? AND plan_type = 'wanted'", conn, params=(date_str,))
    conn.close()
    
    db_expected = {row['hour']: {"activity_type": row['activity_type'], "memo": row['memo']} for _, row in df_db_expected.iterrows()}
    db_wanted = {row['hour']: {"activity_type": row['activity_type'], "memo": row['memo']} for _, row in df_db_wanted.iterrows()}
    
    rows_expected, rows_wanted = [], []
    for h in range(24):
        exp_info = db_expected.get(h, {"activity_type": "미기록", "memo": ""})
        wnt_info = db_wanted.get(h, {"activity_type": "미기록", "memo": ""})
        rows_expected.append({"hour": h, "activity_type": exp_info["activity_type"], "memo": exp_info["memo"], "size": 1})
        rows_wanted.append({"hour": h, "activity_type": wnt_info["activity_type"], "memo": wnt_info["memo"], "size": 1})
        
    df_expected = pd.DataFrame(rows_expected)
    df_wanted = pd.DataFrame(rows_wanted)
    
    # 2개의 그래프를 나란히 배치하기 위해 컬럼 분할
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_exp = draw_clock_chart(df_expected, "💭 내일의 예상 하루<br>(현재 흐름대로 보낼 하루)")
        selected_exp = st.plotly_chart(fig_exp, use_container_width=True, on_select="rerun", key="expected_clock_chart")
        
    with col_chart2:
        fig_wnt = draw_clock_chart(df_wanted, "🌟 내일 보내고 싶은 하루<br>(이상적으로 바라는 하루)")
        selected_wnt = st.plotly_chart(fig_wnt, use_container_width=True, on_select="rerun", key="wanted_clock_chart")
        
    # 선택 반응 탐지 인터페이스
    target_tomorrow_hour = None
    tomorrow_mode = None
    
    if selected_exp and "selection" in selected_exp and "points" in selected_exp["selection"] and len(selected_exp["selection"]["points"]) > 0:
        point_idx = selected_exp["selection"]["points"][0]["point_number"]
        target_tomorrow_hour = int(df_expected.iloc[point_idx]['hour'])
        tomorrow_mode = "expected"
        st.info(f"🔮 **[내일의 예상 하루]** 의 {target_tomorrow_hour:02d}:00 블럭이 선택되었습니다.")
        
    elif selected_wnt and "selection" in selected_wnt and "points" in selected_wnt["selection"] and len(selected_wnt["selection"]["points"]) > 0:
        point_idx = selected_wnt["selection"]["points"][0]["point_number"]
        target_tomorrow_hour = int(df_wanted.iloc[point_idx]['hour'])
        tomorrow_mode = "wanted"
        st.info(f"🔮 **[내일 보내고 싶은 하루]** 의 {target_tomorrow_hour:02d}:00  블럭이 선택되었습니다.")

    # 직접 선택 편집기 (모바일 환경 보완용)
    with st.expander("🔍 내일 계획 시간 조각 직접 선택해서 편집하기"):
        c_sel1, c_sel2 = st.columns(2)
        with c_sel1:
            select_tomorrow_type = st.selectbox("어떤 계획을 편집할까요?", ["💭 내일의 예상 하루", "🌟 내일 보내고 싶은 하루"])
        with c_sel2:
            range_opts_tomorrow = [f"{h:02d}:00~{h+1:02d}:00" for h in range(24)]
            select_tomorrow_range = st.selectbox("시간 범위", range_opts_tomorrow, key="tomorrow_hour_sel")
        if st.button("🔓 선택한 내일 시간 편집창 열기", use_container_width=True):
            st.session_state["mobile_tomorrow_hour"] = int(select_tomorrow_range.split(":")[0])
            st.session_state["mobile_tomorrow_type"] = "expected" if "예상" in select_tomorrow_type else "wanted"

    if st.session_state.get("mobile_tomorrow_type") in ["expected", "wanted"]:
        target_tomorrow_hour = st.session_state.get("mobile_tomorrow_hour")
        tomorrow_mode = st.session_state.get("mobile_tomorrow_type")

    # 내일 계획 데이터 편집기 출력 및 DB 반영
    if target_tomorrow_hour is not None and tomorrow_mode is not None:
        title_tag = "💭 내일의 예상 하루" if tomorrow_mode == "expected" else "🌟 내일 보내고 싶은 하루"
        current_df = df_expected if tomorrow_mode == "expected" else df_wanted
        current_status = current_df[current_df['hour'] == target_tomorrow_hour].iloc[0]
        
        st.markdown(f"### ✍️ {title_tag} [{target_tomorrow_hour:02d}:00 ~ {target_tomorrow_hour+1:02d}:00] 조각 편집")
        type_options = ["수면", "집중", "핸드폰 및 딴짓", "미기록"]
        default_idx = type_options.index(current_status['activity_type']) if current_status['activity_type'] in type_options else 3
        
        act_type_tom = st.radio("행동 유형 설정", type_options, index=default_idx, key="tom_radio_act")
        memo_text_tom = st.text_input("💡 예정된 활동 메모 기입", value=current_status['memo'], key="tom_memo_act")
        
        if st.button(f"💾 {title_tag} 데이터 보관", use_container_width=True):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_activities (date, hour, activity_type, memo, plan_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (date_str, target_tomorrow_hour, act_type_tom, memo_text_tom, tomorrow_mode))
            conn.commit()
            conn.close()
            st.success(f"✅ {title_tag} 조각이 무사히 기기에 보관되었습니다.")
            if "mobile_tomorrow_hour" in st.session_state: del st.session_state["mobile_tomorrow_hour"]
            if "mobile_tomorrow_type" in st.session_state: del st.session_state["mobile_tomorrow_type"]
            st.rerun()

# ==========================================
# 5. 집중 및 휴식 타이머 화면
# ==========================================
elif menu == "집중 및 휴식 타이머 ⏱️":
    st.header("⏱️ 몰입과 휴식을 위한 마인드 타이머")
    timer_mode = st.radio("⏰ 타이머 모드 선택", ["🔥 집중/공부 모드", "🌴 휴식/놀이 모드"], horizontal=True)
    default_minutes = 25 if timer_mode == "🔥 집중/공부 모드" else 5
    duration_min = st.slider("⏱️ 타이머 설정 시간 (분 단위)", min_value=1, max_value=60, value=default_minutes)
    total_seconds = duration_min * 60

    if st.button("🎬 타이머 시작하기", use_container_width=True):
        st.warning(f"⏳ **{duration_min}분** 동안 타이머가 작동 중입니다.")
        countdown_text = st.empty()
        progress_bar = st.progress(0.0)
        for remaining in range(total_seconds, -1, -1):
            mins, secs = divmod(remaining, 60)
            countdown_text.markdown(f"<h1 style='text-align: center; font-size: 60px;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            progress_bar.progress((total_seconds - remaining) / total_seconds)
            time.sleep(1)
        st.balloons()
        st.success("🎉 타이머가 종료되었습니다!")

# ==========================================
# 6. 일일/주간 분석 리포트
# ==========================================
elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 및 목표 분석 대시보드")
    tab1, tab2 = st.tabs(["📉 감정 통계 & 캘린더", "📜 과거 성찰 일기 & 하루 회고 모아보기"])
    
    conn = sqlite3.connect(DB_FILE)
    df_all_rev = pd.read_sql_query("SELECT date, repr_emoji FROM daily_reviews", conn)
    df_all_goals = pd.read_sql_query("SELECT * FROM daily_goals", conn)
    df_all_acts = pd.read_sql_query("SELECT date, hour, activity_type FROM daily_activities WHERE plan_type='actual' ORDER BY date, hour ASC", conn)
    conn.close()
    
    wakeup_map = {}
    if not df_all_acts.empty:
        for g_date, group in df_all_acts.groupby('date'):
            act_dict = {int(row['hour']): row['activity_type'] for _, row in group.iterrows()}
            detected_hour = None
            for h in range(4, 13):
                if act_dict.get(h-1) == "수면" and act_dict.get(h) in ["집중", "핸드폰 및 딴짓", "미기록"]:
                    detected_hour = h
                    break
            if detected_hour is not None:
                wakeup_map[g_date] = f"{detected_hour:02d}:00"

    with tab1:
        st.subheader("📅 나의 하루 감정 & 목표 달성률 달력")
        now = datetime.now()
        col_y, col_m = st.columns(2)
        select_year = col_y.selectbox("연도 선택", [2026, 2027], index=0)
        select_month = col_m.selectbox("월 선택", list(range(1, 13)), index=now.month - 1)
        
        calendar_data_map = {}
        for _, r in df_all_rev.iterrows():
            try:
                d_obj = datetime.strptime(r['date'], "%Y-%m-%d")
                if d_obj.year == select_year and d_obj.month == select_month:
                    if d_obj.day not in calendar_data_map: calendar_data_map[d_obj.day] = {"emoji": "⠀", "rate": None, "wakeup": None}
                    calendar_data_map[d_obj.day]["emoji"] = r.get('repr_emoji', '😊')
            except: pass
            
        for _, g in df_all_goals.iterrows():
            try:
                d_obj = datetime.strptime(g['date'], "%Y-%m-%d")
                if d_obj.year == select_year and d_obj.month == select_month:
                    if d_obj.day not in calendar_data_map: calendar_data_map[d_obj.day] = {"emoji": "⠀", "rate": None, "wakeup": None}
                    total = sum([1 for x in [g.get("today_goal_1"), g.get("today_goal_2"), g.get("week_habit_1"), g.get("week_habit_2")] if x and x.strip() != ""])
                    done = sum([1 for t, d in [(g.get("today_goal_1"), g.get("today_goal_1_done")), (g.get("today_goal_2"), g.get("today_goal_2_done")), (g.get("week_habit_1"), g.get("week_habit_1_done")), (g.get("week_habit_2"), g.get("week_habit_2_done"))] if t and t.strip() != "" and d == 1])
                    calendar_data_map[d_obj.day]["rate"] = int((done / total) * 100) if total > 0 else 0
            except: pass
            
        for d_str, w_time in wakeup_map.items():
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                if d_obj.year == select_year and d_obj.month == select_month:
                    if d_obj.day not in calendar_data_map: calendar_data_map[d_obj.day] = {"emoji": "⠀", "rate": None, "wakeup": None}
                    calendar_data_map[d_obj.day]["wakeup"] = w_time
            except: pass
            
        cal = calendar.monthcalendar(select_year, select_month)
        cal_html = "<table style='width:100%; border-collapse: collapse; text-align:center; font-size:14px;'><tr style='background-color:#f0f2f6; font-weight:bold;'>" + "".join([f"<th style='padding:8px; border:1px solid #ddd;'>{d}</th>" for d in ["월", "화", "수", "목", "금", "토", "일"]]) + "</tr>"
        
        for week in cal:
            cal_html += "<tr>"
            for day in week:
                if day == 0: cal_html += "<td style='padding:15px; border:1px solid #ddd; background-color:#fafafa;'></td>"
                else:
                    day_data = calendar_data_map.get(day, {"emoji": "⠀", "rate": None, "wakeup": None})
                    rate_str = f"<span style='font-size:11px; color:#2E7D32;'><br>🎯달성:{day_data['rate']}%</span>" if day_data["rate"] is not None else ""
                    wakeup_str = f"<span style='font-size:10px; color:#E67E22;'><br>🌅기상:{day_data['wakeup']}</span>" if day_data["wakeup"] is not None else ""
                    cal_html += f"<td style='padding:8px; border:1px solid #ddd; font-weight:bold; height:85px; vertical-align:top;'>{day}<br><span style='font-size:18px;'>{day_data['emoji']}</span>{rate_str}{wakeup_str}</td>"
            cal_html += "</tr>"
        st.markdown(cal_html + "</table>", unsafe_allow_html=True)
        
        st.markdown("---")
        search_date = st.date_input("상세 타임라인 조회 날짜 선택", datetime.today())
        s_date_str = str(search_date)
        
        conn = sqlite3.connect(DB_FILE)
        df_emotion = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ?", conn, params=(s_date_str,))
        conn.close()
        
        if not df_emotion.empty:
            st.subheader(f"📅 {search_date} 시간대별 실시간 감정 스펙트럼")
            emo_rows = []
            for _, row in df_emotion.iterrows():
                t_slot = row['time_slot']
                try: cust_emo = json.loads(row['custom_emotions']) if row['custom_emotions'] else {}
                except: cust_emo = {}
                for e_name in ['우울', '불안', '분노', '기쁨', '공포', '무서움']:
                    eng_name = {'우울':'depression','불안':'anxiety','분노':'anger','기쁨':'joy','공포':'fear','무서움':'dread'}[e_name]
                    emo_rows.append({"time_slot": t_slot, "감정 종류": e_name, "점수(%)": row[eng_name]})
            
            fig_line = px.line(pd.DataFrame(emo_rows).sort_values('time_slot'), x='time_slot', y='점수(%)', color='감정 종류', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        st.subheader("📜 날짜별 전체 일지 아카이브 히스토리")
        archive_date = st.date_input("조회할 날짜 선택", datetime.today(), key="archive_date_picker")
        arc_str = str(archive_date)
        
        conn = sqlite3.connect(DB_FILE)
        df_emo_history = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ? ORDER BY time_slot ASC", conn, params=(arc_str,))
        df_rev_history = pd.read_sql_query("SELECT * FROM daily_reviews WHERE date = ?", conn, params=(arc_str,))
        conn.close()
        
        st.markdown(f"### 📅 {archive_date} 기록 열람결과")
        st.markdown("#### 🪵 시간대별 감정 성찰 일지")
        if df_emo_history.empty:
            st.info("해당 날짜에 작성된 감정 성찰 기록이 없습니다.")
        else:
            for idx, row in df_emo_history.iterrows():
                t_slot = row['time_slot']
                with st.expander(f"⏰ {t_slot} | 표정 상태: {row['emotion_word']}"):
                    st.write(f"**❓ 구실을 만들기 시작한 순간:**\n> {row['q1_moment']}")
                    st.write(f"**❓ 내 머릿속을 스쳤던 생각:**\n> {row['q2_thought']}")
                    st.write(f"**📊 감정 수치 상태:**\n- 기쁨: {row['joy']}% | 우울: {row['depression']}% | 불안: {row['anxiety']}% | 분노: {row['anger']}%")
                    st.write(f"**🌱 인과 마주하기 문장:**\n- 구실 이유: **[{row['sentence_reason']}]** | 결과 감정: **[{row['sentence_result']}]**")
                    st.write(f"**💌 당시 나를 다독인 확언 한 줄:**\n> ✨ *{row['affirmation'] if row['affirmation'] else '작성된 확언이 없습니다.'}*")
                    
                    if st.button(f"🗑️ {t_slot} 감정 기록 지우기", key=f"del_emo_{t_slot}"):
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM emotion_logs WHERE date = ? AND time_slot = ?", (arc_str, t_slot))
                        conn.commit()
                        conn.close()
                        st.success(f"👌 {t_slot}의 성찰 일기가 안전하게 지워졌습니다.")
                        time.sleep(1)
                        st.rerun()
        
        st.markdown("---")
        st.markdown("#### 🏁 마감 하루 종합 회고")
        if df_rev_history.empty:
            st.info("하루 종합 회고 기록이 없습니다.")
        else:
            rev_hist = df_rev_history.iloc[0]
            st.success(f"🎯 오늘 하루 전체적인 대표 이모티콘 상태: {rev_hist['repr_emoji']}")
            st.info(f"**🤔 1. 오늘의 반성**\n\n{rev_hist['reflection']}")
            st.warning(f"**🚀 2. 내일 더 나아지기 위해 할 것**\n\n{rev_hist['improvement']}")
            st.info(f"**🎉 3. 오늘의 칭찬**\n\n{rev_hist['praise']}")

# ==========================================
# 7. 나만의 감정 극복법
# ==========================================
elif menu == "나만의 감정 극복법":
    st.header("🩹 나만의 감정 극복 치트키 아카이브")
    
    with st.form("strategy_form", clear_on_submit=True):
        category = st.selectbox("어떤 감정을 물리칠 방법인가요?", ["불안 극복법 😰", "우울 극복법 😥", "지루함 극복법 😑"])
        strategy_text = st.text_input("나에게 효과적인 구체적인 액션 지침은?")
        submitted = st.form_submit_button("🚀 나만의 처방전에 등록하기")
        
        if submitted and strategy_text.strip():
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO coping_strategies (category, strategy_text) VALUES (?, ?)", (category, strategy_text.strip()))
            conn.commit()
            conn.close()
            st.success("🎯 나만의 멘탈 치트키가 추가되었습니다!")

    st.markdown("---")
    st.subheader("📜 누적된 나만의 멘탈 치트키 리스트")
    df_strat = pd.read_sql_query("SELECT * FROM coping_strategies", sqlite3.connect(DB_FILE))
    
    if df_strat.empty:
        st.info("등록된 극복 팁이 없습니다.")
    else:
        for cat in ["불안 극복법 😰", "우울 극복법 😥", "지루함 극복법 😑"]:
            sub_items = df_strat[df_strat['category'] == cat]
            if not sub_items.empty:
                st.markdown(f"#### **{cat}**")
                for idx, item in sub_items.iterrows():
                    c1, c2 = st.columns([0.85, 0.15])
                    with c1: st.info(f"✔️ {item['strategy_text']}")
                    with c2:
                        if st.button("❌ 삭제", key=f"del_strat_{item['id']}"):
                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM coping_strategies WHERE id = ?", (int(item['id']),))
                            conn.commit()
                            conn.close()
                            st.success("삭제 완료!")
                            time.sleep(0.5)
                            st.rerun()
