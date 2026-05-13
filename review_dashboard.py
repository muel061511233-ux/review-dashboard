"""
허위·협찬 리뷰 탐지 대시보드
================================
실행: streamlit run review_dashboard.py
(run_pipeline.py와 같은 폴더에서 실행)

설치: pip install streamlit plotly pandas
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="리뷰 신뢰도 분석", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    .trust-high { background-color: #d4edda; border-left: 5px solid #28a745; padding: 10px; margin: 5px 0; border-radius: 5px; }
    .trust-mid { background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 10px; margin: 5px 0; border-radius: 5px; }
    .trust-low { background-color: #f8d7da; border-left: 5px solid #dc3545; padding: 10px; margin: 5px 0; border-radius: 5px; }
    .score-badge { display: inline-block; padding: 3px 10px; border-radius: 15px; font-weight: bold; font-size: 14px; margin-right: 8px; }
    .score-green { background-color: #28a745; color: white; }
    .score-yellow { background-color: #ffc107; color: black; }
    .score-red { background-color: #dc3545; color: white; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    for f in ['review_data_final.csv', 'outputs/review_data_final.csv']:
        if os.path.exists(f):
            df = pd.read_csv(f)
            break
    else:
        st.error("❌ review_data_final.csv를 찾을 수 없습니다. run_pipeline.py를 먼저 실행해주세요.")
        st.stop()
    
    if '신뢰등급' not in df.columns:
        df['신뢰등급'] = df['신뢰도'].apply(lambda x: '신뢰' if x>=70 else ('주의' if x>=40 else '의심'))
    df['신뢰표시'] = df['신뢰도'].apply(lambda x: '✅ 신뢰 가능' if x>=70 else ('⚠️ 주의 필요' if x>=40 else '🚨 허위 의심'))
    
    if '의심라벨' not in df.columns:
        labels = []
        for _, row in df.iterrows():
            parts = []
            if row.get('협찬표기', False): parts.append('협찬표기')
            if row.get('과장의심', False): parts.append('과장표현')
            if row.get('감정의심', False): parts.append('과도긍정')
            if not row.get('단점있음', True): parts.append('단점없음')
            if row.get('시간의심', False): parts.append('시간몰림')
            if row.get('블로거의심', False): parts.append('다작블로거')
            if row.get('구조의심', False): parts.append('홍보구조')
            if row.get('내돈내산표기', False) and row.get('분류','') == '내돈내산 위장': parts.append('내돈내산위장')
            labels.append(', '.join(parts) if parts else '없음')
        df['의심라벨'] = labels
    return df

df = load_data()

st.title("🔍 AI 기반 허위·협찬 리뷰 탐지 대시보드")
st.markdown("리뷰의 신뢰도를 AI가 분석하여 점수와 등급을 제공합니다.")
st.markdown("---")

# 사이드바
st.sidebar.header("🎛️ 필터 설정")
min_s, max_s = st.sidebar.slider("신뢰도 점수 범위", 0, 100, (0, 100))
trust_opt = st.sidebar.multiselect("신뢰 등급", ['✅ 신뢰 가능','⚠️ 주의 필요','🚨 허위 의심'], default=['✅ 신뢰 가능','⚠️ 주의 필요','🚨 허위 의심'])
if '분류' in df.columns:
    cat_opt = st.sidebar.multiselect("분류 선택", df['분류'].unique().tolist(), default=df['분류'].unique().tolist())
st.sidebar.markdown("---")
quick = st.sidebar.radio("⚡ 빠른 필터", ['전체 보기','신뢰 리뷰만','의심 리뷰만'])

fdf = df[(df['신뢰도']>=min_s)&(df['신뢰도']<=max_s)]
fdf = fdf[fdf['신뢰표시'].isin(trust_opt)]
if '분류' in df.columns: fdf = fdf[fdf['분류'].isin(cat_opt)]
if quick == '신뢰 리뷰만': fdf = fdf[fdf['신뢰도']>=70]
elif quick == '의심 리뷰만': fdf = fdf[fdf['신뢰도']<40]

# KPI
c1,c2,c3,c4 = st.columns(4)
with c1: st.metric("📊 전체 리뷰", f"{len(df)}개")
with c2:
    t=len(df[df['신뢰도']>=70]); st.metric("✅ 신뢰 가능", f"{t}개", delta=f"{t/len(df)*100:.0f}%")
with c3:
    c=len(df[(df['신뢰도']>=40)&(df['신뢰도']<70)]); st.metric("⚠️ 주의 필요", f"{c}개", delta=f"{c/len(df)*100:.0f}%", delta_color="off")
with c4:
    s=len(df[df['신뢰도']<40]); st.metric("🚨 허위 의심", f"{s}개", delta=f"-{s/len(df)*100:.0f}%", delta_color="inverse")
st.markdown("---")

# 차트
cl, cr = st.columns(2)
with cl:
    st.subheader("📈 4단계 분류 비율")
    if '분류' in df.columns:
        cc = df['분류'].value_counts().reset_index(); cc.columns=['분류','개수']
        cm = {'일반 리뷰':'#16C79A','정당한 협찬':'#F5A623','뒷광고 의심':'#E43F5A','내돈내산 위장':'#8B0000'}
        fig = px.pie(cc, values='개수', names='분류', hole=0.4, color='분류', color_discrete_map=cm)
        fig.update_layout(height=350); st.plotly_chart(fig, use_container_width=True)

with cr:
    st.subheader("📊 신뢰도 점수 분포")
    fig2 = px.histogram(df, x='신뢰도', nbins=20, color_discrete_sequence=['#16C79A'])
    fig2.add_vline(x=70, line_dash="dash", line_color="green", annotation_text="신뢰 기준")
    fig2.add_vline(x=40, line_dash="dash", line_color="red", annotation_text="의심 기준")
    fig2.update_layout(height=350); st.plotly_chart(fig2, use_container_width=True)

ca, cb = st.columns(2)
with ca:
    st.subheader("😊 분류별 감정 비교")
    if '분류' in df.columns and '긍정수' in df.columns:
        se = df.groupby('분류').agg(긍정=('긍정수','mean'),부정=('부정수','mean')).reset_index()
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(name='긍정', x=se['분류'], y=se['긍정'], marker_color='#16C79A'))
        fig3.add_trace(go.Bar(name='부정', x=se['분류'], y=se['부정'], marker_color='#E43F5A'))
        fig3.update_layout(barmode='group', height=350); st.plotly_chart(fig3, use_container_width=True)

with cb:
    st.subheader("🏷️ 의심 유형별 분포")
    lc = {}
    for ls in df['의심라벨']:
        if str(ls) not in ['없음','nan']:
            for l in str(ls).split(', '):
                if l: lc[l] = lc.get(l,0)+1
    if lc:
        fig4 = px.bar(x=list(lc.keys()), y=list(lc.values()), color=list(lc.values()),
                      color_continuous_scale=['#16C79A','#F5A623','#E43F5A'], labels={'x':'유형','y':'건수'})
        fig4.update_layout(height=350, showlegend=False); st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# 리뷰 목록
st.subheader(f"📝 리뷰 목록 ({len(fdf)}개)")
sort_o = st.selectbox("정렬", ['신뢰도 높은순','신뢰도 낮은순','최신순'])
if sort_o == '신뢰도 높은순': fdf = fdf.sort_values('신뢰도', ascending=False)
elif sort_o == '신뢰도 낮은순': fdf = fdf.sort_values('신뢰도', ascending=True)
else: fdf = fdf.sort_values('작성일', ascending=False)

for _, row in fdf.head(30).iterrows():
    sc = int(row['신뢰도'])
    if sc >= 70: css,badge,emo = 'trust-high','score-green','✅'
    elif sc >= 40: css,badge,emo = 'trust-mid','score-yellow','⚠️'
    else: css,badge,emo = 'trust-low','score-red','🚨'
    
    lbl = ''
    lv = str(row.get('의심라벨','없음'))
    if lv not in ['없음','nan']:
        for l in lv.split(', '):
            if l: lbl += f' <span style="background:#eee;padding:2px 6px;border-radius:3px;font-size:12px;">#{l}</span>'
    
    cat = row.get('분류','')
    ch = f' <span style="background:#ddd;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:bold;">{cat}</span>' if cat else ''
    
    st.markdown(f"""
    <div class="{css}">
        <span class="score-badge {badge}">{emo} 신뢰도 {sc}점</span>{ch}{lbl}
        <br><br>
        <strong>{str(row.get('제목',''))[:60]}</strong><br>
        <span style="color:#666;font-size:14px;">{str(row.get('내용',''))[:150]}...</span><br>
        <span style="color:#999;font-size:12px;">👤 {row.get('블로거','')} | 📅 {row.get('작성일','')}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
with st.expander("ℹ️ 신뢰도 점수 산출 방법"):
    st.markdown("""
    | 분석 항목 | 감점 |
    |----------|------|
    | 협찬 키워드 포함 | -30점 |
    | 과장 표현 3개+ | -15점 |
    | 과도한 긍정 + 단점 없음 | -15점 |
    | 단점 미언급 | -10점 |
    | 시간 몰림 | -10점 |
    | 다작 블로거 | -10점 |
    | 홍보 구조 | -10점 |
    | 내돈내산 위장 | -15점 |
    
    ✅ 70+ 신뢰 | ⚠️ 40~69 주의 | 🚨 40- 의심
    """)
