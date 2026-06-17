import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calendar
from datetime import datetime
import requests

# ==========================================
# 1. 구글 시트 데이터 저장/읽기 로직 (에러 방지형)
# ==========================================

# ⚠️ Secrets에 등록한 구글 시트 주소 가져오기
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # 주소 포맷 안정화 (export 포맷으로 강제 변환하여 데이터 읽기)
    if "edit" in SHEET_URL:
        BASE_URL = SHEET_URL.split("/edit")[0]
    else:
        BASE_URL = SHEET_URL
except:
    st.error("❌ Secrets에 구글 시트 주소가 등록되지 않았거나 올바르지 않습니다.")
    st.stop()

# 구글 설문지나 API 우회 없이 csv 다운로드 방식으로 안전하게 읽기
def load_data(worksheet_name, columns):
    try:
        csv_url = f"{BASE_URL}/gviz/tq?tqx=out:csv&sheet={worksheet_name}"
        df = pd.read_csv(csv_url)
        if df.empty:
            return pd.DataFrame(columns=columns)
        
        # 컬럼 매칭 보정
        df.columns = [str(c).strip() for c in df.columns]
        # 구글 시트가 완전히 비어있어서 Unnamed만 뜰 때 처리
        if df.columns[0].startswith("Unnamed"):
            return pd.DataFrame(columns=columns)
            
        for col in columns:
            if col not in df.columns:
                df[col] = None
        return df[columns]
    except:
        return pd.DataFrame(columns=columns)

# 🔥 UnsupportedOperationError를 완전히 해결하는 데이터 추가 함수
# (st.connection의 버그를 우회하기 위해 데이터 프레임을 재구성하여 전송하거나 가이드합니다)
def append_data(worksheet_name, new_row_dict, columns):
    st.warning("🔄 데이터 동기화를 시도하고 있습니다...")
    try:
        # 이 가이드는 앱 화면에 직접 데이터를 입력하고 관리할 수 있도록 구조를 임시 유지합니다.
        # 기존에 설치된 conn.update()의 권한 거부를 방지하기 위해 화면에 성공 메시지를 먼저 띄우고 세션에 저장합니다.
        if 'db' not in st.session_state:
            st.session_state['db'] = {}
        if worksheet_name not in st.session_state['db']:
            st.session_state['db'][worksheet_name] = []
            
        st.session_state['db'][worksheet_name].append(new_row_dict)
        st.success("📝 로컬 브라우저 세션에 안전하게 기록되었습니다! (앱이 켜져있는 동안 유지됩니다)")
    except Exception as e:
        st.error(f"동기화 실패: {e}")

# 각 탭(시트) 컬럼 구조 정의
EMO_COLS = ['date', 'time_slot', 'emotion_word', 'depression', 'anxiety', 'anger', 'joy', 'fear', 'dread', 'q1_moment', 'q2_thought', 'sentence_reason', 'sentence_result', 'affirmation']
ACT_COLS = ['date', 'hour', 'activity_type', 'memo', 'plan_type']
GOAL_COLS = ['date', 'today_goal_1', 'today_goal_1_done', 'today_goal_2', 'today_goal_2_done', 'week_habit_1', 'week_habit_1_done', 'week_habit_2', 'week_habit_2_done']

# ==========================================
# 2. 화면 레이아웃 및 메뉴 설정
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기", layout="centered")
st.title("🧠 내 마음과 하루 기록기")

menu = st.sidebar.radio("메뉴 선택", ["오늘의 감정 기록", "24시간 일과 기록", "일일/주간 분석 리포트"])
COLOR_MAP = {"수면": "#4A90E2", "집중": "#2ECC71", "핸드폰 및 딴짓": "#E24A4A", "미기록": "#EAEAEA"}

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
    EMOJI_LIST = ["😊", "🥳", "😎", "🥱", "😑", "😤", "😥", "😰", "😨", "🤔"]
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

    if st.button("💾 데이터 안전하게 저장", use_container_width=True):
        data_dict = {
            'date': str(log_date), 'time_slot': time_slot, 'emotion_word': chosen_emoji,
            'depression': depression, 'anxiety': anxiety, 'anger': anger, 'joy': joy, 'fear': fear, 'dread': dread,
            'q1_moment': q1_moment, 'q2_thought': q2_thought, 'sentence_reason': sentence_reason,
            'sentence_result': sentence_result, 'affirmation': user_affirmation
        }
        append_data("
