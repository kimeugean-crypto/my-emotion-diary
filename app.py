import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import json
from datetime import datetime, timedelta

# ==========================================
# 0. 데이터베이스(DB) 구조 업데이트
# ==========================================
DB_FILE = "emotion_diary_v6.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 성찰 질문 및 필사 데이터 저장을 위한 테이블 스키마 확장
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
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 1. 프론트엔드 설정 및 공통 에셋
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기", layout="centered")
st.title("🧠 내 마음과 하루 기록기")

menu = st.sidebar.radio("메뉴 선택", ["오늘의 감정 기록", "24시간 일과 기록", "일일/주간 분석 리포트"])

# 오직 이모티콘만 선택할 수 있도록 이모티콘 리스트 생성 (기능 2)
EMOJI_LIST = ["😊", "🥳", "😎", "🥱", "😑", "😤", "😥", "😰", "😨", "🤔"]

# 기능 3: 감정 성격에 맞춤화된 배터리 렌더러
def render_custom_battery(label, score):
    # 긍정적인 감정 목록
    positive_emotions = ["기쁨", "joy", "Joy"]
    
    is_positive = any(pos in label for pos in positive_emotions)
    
    if is_positive:
        # 긍정 감정: 높을수록 충전, 낮을수록 방전
        if score >= 80: status = "🔋 가득 참 (최상)"
        elif score >= 40: status = "🪫 중간 (유지 필요)"
        else: status = "🔌 방전 임박 (충전 필요!)"
    else:
        # 부정 감정: 높을수록 방전 임박(위험), 낮을수록 안정
        if score >= 70: status = "🪫 방전 임박 (스트레스 과부하!)"
        elif score >= 35: status = "⚠️ 주의 (감정 소모 중)"
        else: status = "🔋 안정 (완만함)"
        
    st.write(f"**{label}** : {score}% — *{status}*")
    st.progress(score / 100.0)

# ==========================================
# 2. [기능 개편] 오늘의 감정 기록 화면
# ==========================================
if menu == "오늘의 감정 기록":
    st.header("📝 오늘의 감정 성찰 기록")
    
    # 1시간 단위 시간대 설정 (기능 1)
    col1, col2 = st.columns(2)
    with col1: 
        log_date = st.date_input("기록 날짜", datetime.today())
    with col2: 
        hours_options = [f"{h:02d}:00 ~ {h+1:02d}:00" for h in range(24)]
        time_slot = st.selectbox("기록 시간대 선택 (1시간 단위)", hours_options)
        
    st.markdown("---")
    
    # 기능 4: 감정 기록 이전 마음 성찰 질문
    st.subheader("🧐 STEP 1. 마음 들여다보기")
    q1_moment = st.text_area("❓ 내가 구실을 만들기 시작한 순간은 언제인가요?", placeholder="예: 운동을 가기 싫어서 날씨가 흐리다고 핑계 대기 시작했을 때", height=80)
    q2_thought = st.text_area("❓ 그때 내 머릿속을 스쳤던 생각은 무엇인가요?", placeholder="예: '오늘 하루 안 가도 티 안 나잖아', '피곤한데 그냥 쉬자'", height=80)
    
    st.markdown("---")
    
    # 기능 2: 단어 없는 순수 이모티콘 고르기
    st.subheader("🎭 STEP 2. 현재 내 표정 고르기")
    chosen_emoji = st.radio("지금 상태와 가장 어울리는 얼굴 이모티콘을 터치하세요", EMOJI_LIST, horizontal=True)
    st.markdown(f"<h1 style='text-align: center; font-size: 90px; margin: 10px 0;'>{chosen_emoji}</h1>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 직접 수치 입력받기
    st.subheader("🔋 STEP 3. 감정 배터리 잔량 입력 (% 직접 기입)")
    c1, c2 = st.columns(2)
    with c1:
        joy = st.number_input("기쁨 (Joy) %", 0, 100, 50, 5)
        depression = st.number_input("우울 (Depression) %", 0, 100, 10, 5)
        anxiety = st.number_input("불안 (Anxiety) %", 0, 100, 10, 5)
    with c2:
        anger = st.number_input("분노 (Anger) %", 0, 100, 0, 5)
        fear = st.number_input("공포 (Fear) %", 0, 100, 0, 5)
        dread = st.number_input("무서움 (Dread) %", 0, 100, 0, 5)
        
    # 나만의 감정 추가 (동적 여러 개 기능 유지)
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
            # 커스텀 감정은 기본적으로 부정 카테고리로 간주하여 렌더링하되 이름에 '기쁨/행복'이 들어가면 긍정으로 처리
            render_custom_battery(name, score)

    st.markdown("---")
    
    # 기능 5: 감정 배터리 완료 후 인과 관계 문장 작성
    st.subheader("✍️ STEP 4. 구실과 결과 마주하기")
    st.write("아래 빈칸을 채워 완성된 문장을 만들어주세요.")
    
    sc1, sc2 = st.columns(2)
    with sc1:
        sentence_reason = st.text_input("그때 내가 구실을 만든 이유는 [ ______ ] 때문이다.", placeholder="예: 실패하는 게 두려웠기")
    with sc2:
        sentence_result = st.text_input("하지만 그 결과 나는 [ ______ ]를 느꼈다.", placeholder="예: 마음 한구석의 찝찝함과 자책감")

    st.markdown("---")
    
    # 기능 6: 자기 수용 확언 따라 쓰기 필사 코너
    st.subheader("🌱 STEP 5. 나를 다독이는 확언 한 줄")
    target_affirmation = "완벽하지 않아도 괜찮아. 나는 시도하고 있다."
    st.info(f"따라 쓰실 문장: **{target_affirmation}**")
    user_affirmation = st.text_input("위 문장을 아래에 똑같이 받아 적어주세요.", placeholder="여기에 정자로 똑같이 타이핑해 주세요.")

    # 저장 프로세스 작동
    if st.button("🔓 모든 성찰 일기 저장하기", use_container_width=True):
        if not q1_moment.strip() or not q2_thought.strip():
            st.error("❌ STEP 1의 성찰 질문 답변을 성실히 작성해 주세요!")
        elif not sentence_reason.strip() or not sentence_result.strip():
            st.error("❌ STEP 4의 문장 빈칸 채우기를 완료해 주세요!")
        elif user_affirmation.strip() != target_affirmation:
            st.error("❌ STEP 5의 위로 문장을 정확하게 똑같이 입력해야 마음이 저장됩니다.")
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
            
            st.success(f"❤️ 대견합니다! {time_slot} 의 마음 방 청소가 무사히 완료되어 기록되었습니다.")
            st.session_state.custom_emotion_count = 0

# ==========================================
# 3. 24시간 일과 기록 (원그래프 터치)
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
    df_act['label'] = df_act['hour'].apply(lambda x: f"{x:02d}시~{x+1:02d}시")

    color_map = {"수면": "blue", "집중": "yellow", "핸드폰 및 딴짓": "red", "미기록": "lightgray"}
    
    st.subheader("📊 오늘의 시간 원그래프")
    df_act['size'] = 1
    
    fig_pie = px.pie(
        df_act, values='size', names='label', color='activity_type',
        color_discrete_map=color_map, hole=0.5,
        title=f"{activity_date} 하루 순환 도넛 차트"
    )
    fig_pie.update_traces(textinfo='label', sort=False)
    fig_pie.update_traces(customdata=df_act[['activity_type', 'memo']].values)
    
    selected_points = st.plotly_chart(fig_pie, use_container_width=True, on_select="rerun")
    
    target_hour = 0
    if selected_points and "selection" in selected_points and "points" in selected_points["selection"] and len(selected_points["selection"]["points"]) > 0:
        point_index = selected_points["selection"]["points"][0]["point_number"]
        target_hour = int(df_act.iloc[point_index]['hour'])
        st.success(f"🎯 원그래프에서 **[{target_hour:02d}시 ~ {target_hour+1:02d}시]** 블럭이 선택되었습니다.")
    else:
        st.markdown("---")
        select_hour = st.selectbox("또는 기록할 시간대를 직접 선택하세요", [f"{h:02d}시 ~ {h+1:02d}시" for h in range(24)])
        target_hour = int(select_hour.split("시")[0])

    current_status = df_act[df_act['hour'] == target_hour].iloc[0]
    st.markdown(f"### ✍️ {target_hour:02d}시 상태 편집")
    
    type_options = ["수면", "집중", "핸드폰 및 딴짓", "미기록"]
    try: default_idx = type_options.index(current_status['activity_type'])
    except: default_idx = 3
        
    act_type = st.radio("유형 변경", type_options, index=default_idx)
    memo_text = st.text_input("간단히 한 일 기록", value=current_status['memo'], key=f"act_memo_{target_hour}")
    
    if st.button("💾 이 조각 저장하기", use_container_width=True):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_activities (date, hour, activity_type, memo)
            VALUES (?, ?, ?, ?)
        ''', (str(activity_date), target_hour, act_type, memo_text))
        conn.commit()
        conn.close()
        st.success("저장 완료!")
        st.rerun()

# ==========================================
# 4. 에러가 나지 않는 유연한 리포트 대시보드
# ==========================================
elif menu == "일일/주간 분석 리포트":
    st.header("📊 감정 분석 대시보드")
    search_date = st.date_input("조회 날짜 선택", datetime.today())
    
    conn = sqlite3.connect(DB_FILE)
    df_emotion = pd.read_sql_query("SELECT * FROM emotion_logs WHERE date = ?", conn, params=(str(search_date),))
    conn.close()
    
    if df_emotion.empty:
        st.warning("기록된 감정이 없습니다. 먼저 오늘 하루의 성찰 배터리를 채워주세요!")
    else:
        st.subheader(f"📅 {search_date} 시간대별 감정 스펙트럼")
        
        # 안전한 영어-한글 매핑 가공
        df_emotion = df_emotion.rename(columns={
            'depression': '우울', 'anxiety': '불안', 'anger': '분노',
            'joy': '기쁨', 'fear': '공포', 'dread': '무서움'
        })
        base_emotions = ['우울', '불안', '분노', '기쁨', '공포', '무서움']
        
        df_melted = df_emotion.melt(
            id_vars=['time_slot', 'emotion_word'], value_vars=base_emotions, 
            var_name='감정 종류', value_name='점수(%)'
        )
        
        fig_line = px.line(df_melted, x='time_slot', y='점수(%)', color='감정 종류', markers=True)
        fig_line.update_layout(yaxis=dict(range=[-5, 105]))
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.subheader("💭 오늘의 심리 성찰 기록 모아보기")
        for _, row in df_emotion.iterrows():
            with st.expander(f"⏰ {row['time_slot']} | 선택한 표정: {row['emotion_word']}"):
                st.write(f"**순간:** {row['q1_moment']}")
                st.write(f"**생각:** {row['q2_thought']}")
                st.info(f"📝 *\"내가 구실을 만든 이유는 **{row['sentence_reason']}** 때문이다. 하지만 그 결과 나는 **{row['sentence_result']}**를 느꼈다.\"*")
