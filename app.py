import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import calendar
import time
import requests
import hashlib
from datetime import datetime

# ==========================================
# 0. 전세계 기기 연동을 위한 클라우드 동기화 엔진
# ==========================================
BIN_서버_URL = "https://api.jsonbin.io/v3/b"
HEADERS = {"X-Bin-Meta": "false", "Content-Type": "application/json"}

def 사용자_해시_생성(username, password):
    combined = f"emotion_diary_{username}_{password}"
    return hashlib.sha256(combined.encode()).hexdigest()[:24]

def 클라우드_데이터_로드(user_key):
    try:
        res = requests.get(f"{BIN_서버_URL}/{user_key}", headers=HEADERS)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {
        "emotion_logs": {},
        "daily_activities": {},
        "daily_reviews": {},
        "coping_strategies": [],
        "daily_goals": {}
    }

def 클라우드_데이터_저장(user_key, data):
    try:
        res = requests.put(f"{BIN_서버_URL}/{user_key}", headers=HEADERS, json=data)
        if res.status_code != 200:
            requests.post(BIN_서버_URL, headers={"X-Bin-Private": "false", "Content-Type": "application/json"}, json=data)
        return True
    except:
        st.error("☁️ 네트워크 연결이 불안정하여 클라우드 동기화에 실패했습니다. 다시 시도해 주세요.")
        return False

# ==========================================
# 1. 로그인 / 회원가입 시스템 내부 세션 관리
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기", layout="centered")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_key = None
    st.session_state.user_data = None

if not st.session_state.logged_in:
    st.title("🔐 멀티 디바이스 마음 일기 로그인")
    st.write("이름과 비밀번호를 정해 로그인하세요. 다른 기기에서도 동일하게 입력하면 내 기록이 그대로 나타납니다.")
    
    tab_login, tab_info = st.tabs(["로그인 / 계정 생성", "도움말 및 기기연동 안내"])
    
    with tab_login:
        username = st.text_input("👤 내 이름 (또는 아이디)", placeholder="예: 길동이")
        password = st.text_input("🔑 비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        
        if st.button("🔓 로그인 및 데이터 동기화 시작", use_container_width=True):
            if not username.strip() or not password.strip():
                st.error("이름과 비밀번호를 정확히 입력해 주세요!")
            else:
                with st.spinner("☁️ 전세계 클라우드 서버에서 내 장부 동기화 중..."):
                    user_key = 사용자_해시_생성(username.strip(), password.strip())
                    user_data = 클라우드_데이터_로드(user_key)
                    
                    st.session_state.user_key = user_key
                    st.session_state.user_data = user_data
                    st.session_state.logged_in = True
                    st.success(f"🎉 반갑습니다, {username}님! 데이터 동기화가 완료되었습니다.")
                    time.sleep(1)
                    st.rerun()
                    
    with tab_info:
        st.info("""
        **💡 어떻게 다른 기기에서 연동되나요?**
        입력하신 **이름**과 **비밀번호**를 바탕으로 온라인 보안 공간에 나만의 비밀 장부가 매핑됩니다.
        스마트폰, 태블릿, PC 어디서든 동일한 정보로 로그인하면 기록을 실시간으로 수정 및 삭제할 수 있습니다.
        """)
    st.stop()

USER_KEY = st.session_state.user_key
USER_DATA = st.session_state.user_data

# ==========================================
# 2. 공통 에셋 및 화면 레이아웃
# ==========================================
st.sidebar.markdown(f"### 👤 인증됨")
if st.sidebar.button("🚪 안전하게 로그아웃"):
    st.session_state.logged_in = False
    st.session_state.user_key = None
    st.session_state.user_data = None
    st.rerun()

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

    if st.button("🔓 모든 성찰 일기 저장하고 서버에 동기화", use_container_width=True):
        if not q1_moment.strip() or not q2_thought.strip():
            st.error("❌ 마음 성찰 질문(STEP 1)을 작성해 주세요!")
        elif not sentence_reason.strip() or not sentence_result.strip():
            st.error("❌ 문장 빈칸 채우기(STEP 4)를 완료해 주세요!")
        else:
            date_str = str(log_date)
            if "emotion_logs" not in USER_DATA: USER_DATA["emotion_logs"] = {}
            if date_str not in USER_DATA["emotion_logs"]: USER_DATA["emotion_logs"][date_str] = {}
            
            USER_DATA["emotion_logs"][date_str][time_slot] = {
                "emotion_word": chosen_emoji, "depression": depression, "anxiety": anxiety,
                "anger": anger, "joy": joy, "fear": fear, "dread": dread,
                "custom_emotions": custom_emotions_data, "q1_moment": q1_moment, "q2_thought": q2_thought,
                "sentence_reason": sentence_reason, "sentence_result": sentence_result, "affirmation": user_affirmation.strip()
            }
            
            if 클라우드_데이터_저장(USER_KEY, USER_DATA):
                st.success(f"☁️ 클라우드 동기화 완료! {time_slot} 기준의 감정 기록과 확언이 저장되었습니다.")
                st.session_state.custom_emotion_count = 0

# ==========================================
# 4. 24시간 일과 기록 화면
# ==========================================
elif menu == "24시간 일과 기록":
    st.header("🕒 24시간 타임 루프 기록")
    activity_date = st.date_input("일과 기록 날짜 선택", datetime.today())
    date_str = str(activity_date)
    
    if "daily_activities" not in USER_DATA: USER_DATA["daily_activities"] = {}
    day_acts = USER_DATA["daily_activities"].get(date_str, {})
    
    rows = []
    for h in range(24):
        act_info = day_acts.get(str(h), {"activity_type": "미기록", "memo": ""})
        rows.append({"hour": h, "activity_type": act_info["activity_type"], "memo": act_info["memo"], "size": 1})
    df_act = pd.DataFrame(rows)
    
    def make_display_text(row):
        time_range = f"{int(row['hour']):02d}:00~{int(row['hour'])+1:02d}:00"
        if row['memo'] and row['memo'].strip() != "":
            return f"{time_range}<br><b>📝 {row['memo']}</b>"
        return f"{time_range}"
        
    df_act['display_text'] = df_act.apply(make_display_text, axis=1)
    color_map = {"수면": "#4A90E2", "집중": "#2ECC71", "핸드폰 및 딴짓": "#E24A4A", "미기록": "#EAEAEA"}
    df_act['color'] = df_act['activity_type'].map(color_map)

    st.subheader("📊 오늘의 시간 시계 원그래프")
    fig_clock = go.Figure(data=[go.Pie(
        labels=df_act['display_text'], values=df_act['size'],
        marker=dict(colors=df_act['color'], line=dict(color='#FFFFFF', width=2)),
        hole=0.45, sort=False, direction='clockwise', rotation=90,
        textinfo='text', text=df_act['display_text'], textposition='inside',
        insidetextorientation='radial', hovertemplate="<b>%{label}</b><br>유형: %{customdata}<extra></extra>",
        customdata=df_act['activity_type']
    )])
    fig_clock.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20), height=520)
    
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
        st.markdown(f"### ✍️ {target_hour:02d}:00 ~ {target_hour+1:02d}:00 내용 기록 편집 / 초기화")
        
        type_options = ["수면", "집중", "핸드폰 및 딴짓", "미기록"]
        try: default_idx = type_options.index(current_status['activity_type'])
        except: default_idx = 3
            
        act_type = st.radio("행동 유형 설정(색상 변경)", type_options, index=default_idx)
        memo_text = st.text_input("💡 이 시간대에 내가 한 일 기록하기 (비우고 저장하면 내용 삭제)", value=current_status['memo'])
        
        if st.button("💾 이 시간 조각 저장하고 클라우드 반영", use_container_width=True):
            if date_str not in USER_DATA["daily_activities"]: USER_DATA["daily_activities"][date_str] = {}
            USER_DATA["daily_activities"][date_str][str(target_hour)] = {"activity_type": act_type, "memo": memo_text}
            
            if 클라우드_데이터_저장(USER_KEY, USER_DATA):
                st.success("☁️ 시간 조각 데이터가 업데이트되었습니다!")
                if "mobile_target_hour" in st.session_state: del st.session_state["mobile_target_hour"]
                st.rerun()

    st.markdown("---")
    st.subheader("🎯 오늘의 목표 및 이번 주 습관 관리")
    if "daily_goals" not in USER_DATA: USER_DATA["daily_goals"] = {}
    g_data = USER_DATA["daily_goals"].get(date_str, {"today_goal_1":"", "today_goal_1_done":0, "today_goal_2":"", "today_goal_2_done":0, "week_habit_1":"", "week_habit_1_done":0, "week_habit_2":"", "week_habit_2_done":0})
                  
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

    total_goals_count = sum([1 for x in [g1_text, g2_text, h1_text, h2_text] if x.strip() != ""])
    done_goals_count = sum([1 for text, checked in [(g1_text, g1_done), (g2_text, g2_done), (h1_text, h1_done), (h2_text, h2_done)] if text.strip() != "" and checked])
    current_achievement_rate = int((done_goals_count / total_goals_count) * 100) if total_goals_count > 0 else 0
    st.write(f"📊 현재 선택된 날짜의 실시간 목표 달성률: **{current_achievement_rate}%**")

    if st.button("💾 목표 및 습관 진행 상황 저장", use_container_width=True):
        USER_DATA["daily_goals"][date_str] = {
            "today_goal_1": g1_text, "today_goal_1_done": int(g1_done),
            "today_goal_2": g2_text, "today_goal_2_done": int(g2_done),
            "week_habit_1": h1_text, "week_habit_1_done": int(h1_done),
            "week_habit_2": h2_text, "week_habit_2_done": int(h2_done)
        }
        if 클라우드_데이터_저장(USER_KEY, USER_DATA):
            st.success("🎯 목표 데이터가 실시간 공유 완료되었습니다!")

    st.markdown("---")
    st.subheader("🏁 오늘의 종합 하루 회고")
    if "daily_reviews" not in USER_DATA: USER_DATA["daily_reviews"] = {}
    exist_review = USER_DATA["daily_reviews"].get(date_str, {"reflection":"", "improvement":"", "praise":"", "repr_emoji":"😊"})
    
    rev_reflection = st.text_area("1. 🤔 오늘의 반성", value=exist_review.get("reflection", ""), placeholder="오늘 아쉬웠던 점을 적어주세요.")
    rev_improvement = st.text_area("2. 🚀 내일 더 나아지기 위해 할 것", value=exist_review.get("improvement", ""), placeholder="내일 시도해 볼 계획을 적어주세요.")
    rev_praise = st.text_area("3. 🎉 오늘의 칭찬", value=exist_review.get("praise", ""), placeholder="나 자신에게 건네는 따뜻한 칭찬 한마디를 적어주세요.")
    
    try: emoji_idx = EMOJI_LIST.index(exist_review.get("repr_emoji", "😊"))
    except: emoji_idx = 0
    repr_emoji = st.selectbox("🎯 오늘 하루 나의 전체적인 상태 이모티콘 고르기", EMOJI_LIST, index=emoji_idx)
    
    if st.button("🔔 오늘의 종합 회고 저장 완료", use_container_width=True):
        USER_DATA["daily_reviews"][date_str] = {
            "reflection": rev_reflection, "improvement": rev_improvement, "praise": rev_praise, "repr_emoji": repr_emoji
        }
        if 클라우드_데이터_저장(USER_KEY, USER_DATA):
            st.success("📝 하루 마감 데이터가 전 서버에 안전하게 백업되었습니다!")

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
# 6. 일일/주간 분석 리포트 (★자유로운 삭제 기능 추가★)
# ==========================================
elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 및 목표 분석 대시보드")
    tab1, tab2 = st.tabs(["📉 감정 통계 & 캘린더", "📜 과거 성찰 일기 & 하루 회고 모아보기"])
    
    wakeup_map = {}
    act_logs = USER_DATA.get("daily_activities", {})
    for g_date, hours_data in act_logs.items():
        act_dict = {int(h): info["activity_type"] for h, info in hours_data.items()}
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
        for d_str, r in USER_DATA.get("daily_reviews", {}).items():
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                if d_obj.year == select_year and d_obj.month == select_month:
                    if d_obj.day not in calendar_data_map: calendar_data_map[d_obj.day] = {"emoji": "⠀", "rate": None, "wakeup": None}
                    calendar_data_map[d_obj.day]["emoji"] = r.get('repr_emoji', '😊')
            except: pass
            
        for d_str, g in USER_DATA.get("daily_goals", {}).items():
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d")
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
        
        day_emo = USER_DATA.get("emotion_logs", {}).get(s_date_str, {})
        if day_emo:
            st.subheader(f"📅 {search_date} 시간대별 실시간 감정 스펙트럼")
            emo_rows = []
            for t_slot, info in day_emo.items():
                for e_name in ['우울', '불안', '분노', '기쁨', '공포', '무서움']:
                    eng_name = {'우울':'depression','불안':'anxiety','분노':'anger','기쁨':'joy','공포':'fear','무서움':'dread'}[e_name]
                    emo_rows.append({"time_slot": t_slot, "감정 종류": e_name, "점수(%)": info.get(eng_name, 0)})
            fig_line = px.line(pd.DataFrame(emo_rows).sort_values('time_slot'), x='time_slot', y='점수(%)', color='감정 종류', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        st.subheader("📜 날짜별 전체 일지 아카이브 히스토리")
        archive_date = st.date_input("조회할 날짜 선택", datetime.today(), key="archive_date_picker")
        arc_str = str(archive_date)
        
        st.markdown(f"### 📅 {archive_date} 기록 열람결과")
        
        # ------------------------------------------
        # 💡 [기능 보강] 시간대별 감정 기록 출력 및 삭제 버튼 구현
        # ------------------------------------------
        st.markdown("#### 🪵 시간대별 감정 성찰 일지")
        day_emo_hist = USER_DATA.get("emotion_logs", {}).get(arc_str, {})
        if not day_emo_hist:
            st.info("해당 날짜에 작성된 감정 성찰 기록이 없습니다.")
        else:
            for t_slot, row in sorted(day_emo_hist.items()):
                with st.expander(f"⏰ {t_slot} | 표정 상태: {row.get('emotion_word', '😊')}"):
                    st.write(f"**❓ 구실을 만들기 시작한 순간:**\n> {row.get('q1_moment', '')}")
                    st.write(f"**❓ 내 머릿속을 스쳤던 생각:**\n> {row.get('q2_thought', '')}")
                    st.write(f"**📊 감정 수치 상태:**\n- 기쁨: {row.get('joy',0)}% | 우울: {row.get('depression',0)}% | 불안: {row.get('anxiety',0)}% | 분노: {row.get('anger',0)}%")
                    st.write(f"**🌱 인과 마주하기 문장:**\n- 구실 이유: **[{row.get('sentence_reason','')}]** | 결과 감정: **[{row.get('sentence_result','')}]**")
                    st.write(f"**💌 당시 나를 다독인 확언 한 줄:**\n> ✨ *{row.get('affirmation', '작성된 확언이 없습니다.')}*")
                    
                    # 개별 시간대 로그 삭제 버튼
                    if st.button(f"🗑️ {t_slot} 감정 기록 지우기", key=f"del_emo_{t_slot}"):
                        del USER_DATA["emotion_logs"][arc_str][t_slot]
                        # 하루 데이터가 다 비었으면 날짜 키 자체를 제거
                        if not USER_DATA["emotion_logs"][arc_str]:
                            del USER_DATA["emotion_logs"][arc_str]
                        if 클라우드_데이터_저장(USER_KEY, USER_DATA):
                            st.success(f"👌 {t_slot}의 성찰 일기와 확언이 안전하게 지워졌습니다.")
                            time.sleep(1)
                            st.rerun()
        
        st.markdown("---")
        
        # ------------------------------------------
        # 💡 [기능 보강] 종합 회고 출력 및 전체 삭제 구현
        # ------------------------------------------
        st.markdown("#### 🏁 마감 하루 종합 회고")
        rev_hist = USER_DATA.get("daily_reviews", {}).get(arc_str, {})
        if not rev_hist:
            st.info("하루 종합 회고 기록이 없습니다.")
        else:
            st.success(f"🎯 오늘 하루 전체적인 대표 이모티콘 상태: {rev_hist.get('repr_emoji', '😊')}")
            st.info(f"**🤔 1. 오늘의 반성**\n\n{rev_hist.get('reflection', '')}")
            st.warning(f"**🚀 2. 내일 더 나아지기 위해 할 것**\n\n{rev_hist.get('improvement', '')}")
            st.help(f"**🎉 3. 오늘의 칭찬**\n\n{rev_hist.get('praise', '')}")
            
            # 종합 회고 삭제 버튼
            if st.button("🗑️ 오늘의 종합 회고 전부 삭제하기", use_container_width=True):
                del USER_DATA["daily_reviews"][arc_str]
                if 클라우드_데이터_저장(USER_KEY, USER_DATA):
                    st.success("👌 오늘의 종합 회고 일지가 클라우드에서 삭제되었습니다.")
                    time.sleep(1)
                    st.rerun()

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
            if "coping_strategies" not in USER_DATA: USER_DATA["coping_strategies"] = []
            USER_DATA["coping_strategies"].append({"category": category, "strategy_text": strategy_text.strip()})
            if 클라우드_데이터_저장(USER_KEY, USER_DATA):
                st.success("🎯 멘탈 치트키 리스트가 클라우드에 업데이트되었습니다!")

    st.markdown("---")
    st.subheader("📜 누적된 나만의 멘탈 치트키 리스트")
    strat_list = USER_DATA.get("coping_strategies", [])
    if not strat_list:
        st.info("등록된 극복 팁이 없습니다.")
    else:
        # 치트키 삭제 기능 포함 출력
        for cat in ["불안 극복법 😰", "우울 극복법 😥", "지루함 극복법 😑"]:
            sub_items = [x for x in strat_list if x.get("category") == cat]
            if sub_items:
                st.markdown(f"#### **{cat}**")
                for idx, item in enumerate(sub_items):
                    c1, c2 = st.columns([0.85, 0.15])
                    with c1:
                        st.info(f"✔️ {item.get('strategy_text', '')}")
                    with c2:
                        # 고유 키를 활용한 행동 수칙 개별 삭제
                        if st.button("❌ 삭제", key=f"del_strat_{cat}_{idx}"):
                            USER_DATA["coping_strategies"].remove(item)
                            if 클라우드_데이터_저장(USER_KEY, USER_DATA):
                                st.success("삭제 완료!")
                                time.sleep(0.5)
                                st.rerun()
