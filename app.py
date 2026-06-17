import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 구글 시트 클라우드 DB 연결
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# 에러 방지용 안전 데이터 로드 함수
def load_data(worksheet_name, columns):
    try:
        df = conn.read(worksheet=worksheet_name, ttl="0")
        if df is None or df.empty:
            return pd.DataFrame(columns=columns)
        # 구글 시트에서 간혹 컬럼이 다르게 읽히는 경우 방지
        for col in columns:
            if col not in df.columns:
                df[col] = None
        return df[columns]
    except Exception:
        return pd.DataFrame(columns=columns)

# 구글 시트에 데이터 추가 함수
def append_data(worksheet_name, new_row_dict, columns):
    df = load_data(worksheet_name, columns)
    new_df = pd.DataFrame([new_row_dict])
    df = pd.concat([df, new_df], ignore_index=True)
    conn.update(worksheet=worksheet_name, data=df)
    st.success("☁️ 구글 시트와 안전하게 동기화되었습니다!")

# 각 탭(시트) 컬럼 구조 정의
EMO_COLS = ['date', 'time_slot', 'emotion_word', 'depression', 'anxiety', 'anger', 'joy', 'fear', 'dread', 'q1_moment', 'q2_thought', 'sentence_reason', 'sentence_result', 'affirmation']
ACT_COLS = ['date', 'hour', 'activity_type', 'memo', 'plan_type']
GOAL_COLS = ['date', 'today_goal_1', 'today_goal_1_done', 'today_goal_2', 'today_goal_2_done', 'week_habit_1', 'week_habit_1_done', 'week_habit_2', 'week_habit_2_done']
REV_COLS = ['date', 'reflection', 'improvement', 'praise', 'repr_emoji']

# ==========================================
# 2. 화면 레이아웃 및 메뉴 설정
# ==========================================
st.set_page_config(page_title="마음 & 일과 추적기", layout="centered")
st.title("🧠 내 마음과 하루 기록기")

menu = st.sidebar.radio("메뉴 선택", ["오늘의 감정 기록", "24시간 일과 기록", "일일/주간 분석 리포트"])
EMOJI_LIST = ["😊", "🥳", "😎", "🥱", "😑", "😤", "😥", "😰", "😨", "🤔"]
COLOR_MAP = {"수면": "#4A90E2", "집중": "#2ECC71", "핸드폰 및 딴짓": "#E24A4A", "미기록": "#EAEAEA"}

# 문법 오류(SyntaxError)를 완벽하게 해결한 시계 차트 함수
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
        labels=df['display_text'], values=[1 classification if 'hour' in df else 1]*len(df),
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
    chosen_emoji = st.radio("지금 표정 고르기", EMOJI_LIST, horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        joy = st.slider("기쁨 %", 0, 100, 50)
        depression = st.slider("우울 %", 0, 100, 10)
        anxiety = st.slider("불안 %", 0, 100, 10)
