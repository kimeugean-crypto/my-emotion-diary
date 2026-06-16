import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import json
import calendar
from datetime import datetime, timedelta

# ==========================================
# 0. 데이터베이스(DB) 구조 업데이트 및 초기화
# ==========================================
DB_FILE = "emotion_diary_v7.db"

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
            with cc1: c_name = st.text_input(f"감정 이름 (#{i+1})", key=f"c_name_{i}")
            with cc2: c_score = st.number_input(f"수치 (#{i+1}) %", 0, 100, 50, 5, key=f"c_score_{i}")
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
# 3. 24시간 일과 기록 화면 (★시계방향 회전 및 범위 표기 수정★)
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
    
    # 그래프 조각 레이블도 범위 형태로 통일하여 직관성 증가
    df_act['label'] = df_act['hour'].apply(lambda x: f"{x:02d}:00~{x+1:02d}:00")

    color_map = {"수면": "blue", "집중": "yellow", "핸드폰 및 딴짓": "red", "미기록": "lightgray"}
    
    st.subheader("📊 오늘의 시간 원그래프")
    df_act['size'] = 1
    
    fig_pie = px.pie(
        df_act, values='size', names='label', color='activity_type',
        color_discrete_map=color_map, hole=0.5, title=f"{activity_date} 일과 배치"
    )
    
    # 💡 [요구사항 2] 그래프 정렬: 12시 방향(90도)에서 시작해서 오른쪽 시계방향(clockwise)으로 돌도록 설정
    fig_pie.update_traces(
        textinfo='label', 
        sort=False, 
        direction='clockwise', 
        rotation=90
    )
    
    selected_points = st.plotly_chart(fig_pie, use_container_width=True, on_select="rerun")
    
    target_hour = None

    # 1단계: 원그래프 블럭 터치 감지 시
    if selected_points and "selection" in selected_points and "points" in selected_points["selection"] and len(selected_points["selection"]["points"]) > 0:
        point_index = selected_points["selection"]["points"][0]["point_number"]
        target_hour = int(df_act.iloc[point_index]['hour'])
        st.success(f"🎯 원그래프 터치 성공! **[{target_hour:02d}:00 ~ {target_hour+1:02d}:00]** 블럭이 선택되었습니다.")

    st.markdown("---")
    
    # 2단계: 터치가 안 되거나 초기 상태일 때 수동 선택 보완창
    if target_hour is None:
        st.info("💡 모바일 기기 종류에 따라 위 그래프 터치가 작동하지 않을 수 있습니다. 아래 버튼을 눌러 직접 시간대를 선택해 주세요.")
        with st.expander("🔍 터치 대신 직접 시간대 선택해서 편집창 열기"):
            # 💡 [요구사항 1] 정시 표기가 아닌 00:00~01:00 범위 형태로 옵션 제공
            range_options = [f"{h:02d}:00~{h+1:02d}:00" for h in range(24)]
            select_range = st.selectbox("편집할 시간 범위 선택", range_options, index=0)
            if st.button("🔓 선택한 시간 편집창 열기"):
                # 시작 시간 숫자만 파싱 (ex: "01:00~02:00" -> 1)
                st.session_state["mobile_target_hour"] = int(select_range.split(":")[0])
        
        if "mobile_target_hour" in st.session_state:
            target_hour = st.session_state["mobile_target_hour"]

    # 3단계: 시간대가 정해지면 편집창 등장
    if target_hour is not None:
        current_status = df_act[df_act['hour'] == target_hour].iloc[0]
        st.markdown(f"### ✍️ {target_hour:02d}:00 ~ {target_hour+1:02d}:00 내용 기록 편집")
        
        type_options = ["수면", "집중", "핸드폰 및 딴짓", "미기록"]
        try: default_idx = type_options.index(current_status['activity_type'])
        except: default_idx = 3
            
        act_type = st.radio("행동 유형 설정", type_options, index=default_idx)
        memo_text = st.text_input("한 일 요약 기술", value=current_status['memo'])
        
        if st.button("💾 해당 시간 조각 저장하기", use_container_width=True):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_activities (date, hour, activity_type, memo)
                VALUES (?, ?, ?, ?)
            ''', (str(activity_date), target_hour, act_type, memo_text))
            conn.commit()
            conn.close()
            st.success(f"💾 {target_hour:02d}:00 ~ {target_hour+1:02d}:00 정보가 반영되었습니다!")
            if "mobile_target_hour" in st.session_state:
                del st.session_state["mobile_target_hour"]
            st.rerun()

    st.markdown("---")
    
    # 오늘의 종합 하루 회고
    st.subheader("🏁 오늘의 종합 하루 회고")
    conn = sqlite3.connect(DB_FILE)
    df_rev = pd.read_sql_query("SELECT * FROM daily_reviews WHERE date = ?", conn, params=(str(activity_date),))
    conn.close()
    
    exist_review = df_rev.iloc[0] if not df_rev.empty else {"reflection":"", "improvement":"", "praise":"", "repr_emoji":"😊"}
    
    rev_reflection = st.text_area("1. 🤔 오늘의 반성", value=exist_review["reflection"], placeholder="오늘 아쉬웠던 점이나 고치고 싶은 행동을 적어주세요.")
    rev_improvement = st.text_area("2. 🚀 내일 더 나아지기 위해 할 것", value=exist_review["improvement"], placeholder="내일 시도해 볼 작은 실행 계획을 적어주세요.")
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
        st.success("📝 하루의 총평과 회고가 안전하게 마감되었습니다!")

# ==========================================
# 4. 일일/주간 분석 리포트
# ==========================================
elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 분석 대시보드")
    
    st.subheader("📅 나의 하루 감정 스티커 달력")
    now = datetime.now()
    col_y, col_m = st.columns(2)
    with col_y: select_year = st.selectbox("연도 선택", [2026, 2027], index=0)
    with col_m: select_month = st.selectbox("월 선택", list(range(1, 13)), index=now.month - 1)
    
    conn = sqlite3.connect(DB_FILE)
    df_all_rev = pd.read_sql_query("SELECT date, repr_emoji FROM daily_reviews", conn)
    conn.close()
    
    emoji_calendar_map = {}
    for _, r in df_all_rev.iterrows():
        try:
            d_obj = datetime.strptime(r['date'], "%Y-%m-%d")
            if d_obj.year == select_year and d_obj.month == select_month:
                emoji_calendar_map[d_obj.day] = r['repr_emoji']
        except: pass
        
    cal = calendar.monthcalendar(select_year, select_month)
    days_headers = ["월", "화", "수", "목", "금", "토", "일"]
    
    cal_html = "<table style='width:100%; border-collapse: collapse; text-align:center; font-size:16px;'>"
    cal_html += "<tr style='background-color:#f0f2f6; font-weight:bold;'>" + "".join([f"<th style='padding:8px; border:1px solid #ddd;'>{d}</th>" for d in days_headers]) + "</tr>"
    
    for week in cal:
        cal_html += "<tr>"
        for day in week:
            if day == 0:
                cal_html += "<td style='padding:15px; border:1px solid #ddd; background-color:#fafafa;'></td>"
            else:
                sticker = emoji_calendar_map.get(day, "⠀")
                cal_html += f"<td style='padding:10px; border:1px solid #ddd; font-weight:bold;'>{day}<br><span style='font-size:22px;'>{sticker}</span></td>"
        cal_html += "</tr>"
    cal_html += "</table>"
    
    st.markdown(cal_html, unsafe_allow_html=True)
    st.caption("※ 감정 스티커는 '24시간 일과 기록' 메뉴 하단 종합 회고에서 선택한 이모지가 연동되어 출력됩니다.")
    st.markdown("---")
    
    search_date = st.date_input("상세 타임라인 조회 날짜 선택", datetime.today())
    conn = sqlite3.connect(DB_FILE)
    df_emotion = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ?", conn, params=(str(search_date),))
    conn.close()
    
    if not df_emotion.empty:
        st.subheader(f"📅 {search_date} 시간대별 실시간 감정 스펙트럼")
        df_emotion = df_emotion.rename(columns={'depression':'우울','anxiety':'불안','anger':'분노','joy':'기쁨','fear':'공포','dread':'무서움'})
        df_emotion = df_emotion.sort_values('time_slot')
        base_emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        df_melted = df_emotion.melt(id_vars=['time_slot'], value_vars=base_emotions, var_name='감정 종류', value_name='점수(%)')
        
        fig_line = px.line(df_melted, x='time_slot', y='점수(%)', color='감정 종류', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# 5. 나만의 감정 극복법
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
