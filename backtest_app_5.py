import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import yfinance as yf
import io
import base64
import os
import time
import random
import requests
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tickflow import TickFlow

# 设置yfinance缓存目录到当前工作目录
os.environ['YFINANCE_CACHE_DIR'] = str(Path('.') / 'yfinance_cache')

# 创建缓存目录
cache_dir = Path('.') / 'yfinance_cache'
cache_dir.mkdir(parents=True, exist_ok=True)

# 创建会话级别的requests对象，配置重试机制
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.timeout = 30
    return session

# 兼容不同pandas版本的月度重采样
def resample_monthly(df, agg_dict):
    """
    兼容多个pandas版本的月度重采样函数
    自动尝试不同的频率格式
    """
    frequencies = ['ME', 'M', 'MS']
    for freq in frequencies:
        try:
            return df.resample(freq).agg(agg_dict)
        except Exception:
            continue
    # 如果都失败，尝试按月分组
    try:
        df_copy = df.copy()
        df_copy['year'] = df_copy.index.year
        df_copy['month'] = df_copy.index.month
        result = df_copy.groupby(['year', 'month']).agg(agg_dict)
        # 创建日期索引
        result.index = pd.to_datetime([f"{y}-{m:02d}-01" for y, m in result.index])
        return result
    except Exception:
        # 最后的后备方案：返回空数据框
        return pd.DataFrame()

# 兼容不同pandas版本的月份转换
def to_period_monthly(index):
    """
    兼容多个pandas版本的日期转月份函数
    """
    frequencies = ['ME', 'M', 'MS']
    for freq in frequencies:
        try:
            return index.to_period(freq)
        except Exception:
            continue
    # 如果都失败，返回年月字符串
    return pd.to_datetime(index).strftime('%Y-%m')

# 初始化 TickFlow 客户端
def get_deploy_secret(name, default=None):
    """Read secrets from Streamlit Cloud first, then local environment variables."""
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)

def get_tickflow_client():
    try:
        api_key = get_deploy_secret("TICKFLOW_API_KEY")
        if api_key:
            return TickFlow(api_key=api_key)

        st.info("未配置 TICKFLOW_API_KEY，將嘗試使用 TickFlow 免費模式。")
        return TickFlow.free()
    except Exception as e:
        st.write(f"TickFlow 初始化失败: {str(e)[:100]}...")
        try:
            return TickFlow.free()
        except Exception as e2:
            st.write(f"TickFlow 免费模式也失败: {str(e2)[:100]}...")
            return None

# Matplotlib Apple 风格设置
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#F5F5F7'
plt.rcParams['axes.facecolor'] = '#FFFFFF'
plt.rcParams['axes.edgecolor'] = '#E5E5EA'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.4
plt.rcParams['grid.color'] = '#E5E5EA'
plt.rcParams['text.color'] = '#1D1D1F'
plt.rcParams['axes.labelcolor'] = '#6E6E73'
plt.rcParams['xtick.color'] = '#6E6E73'
plt.rcParams['ytick.color'] = '#6E6E73'
plt.rcParams['font.size'] = 11
plt.rcParams['lines.linewidth'] = 1.5
plt.rcParams['lines.color'] = '#007AFF'

# 设置Streamlit主题
st.set_page_config(
    page_title="股票交易策略回测系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 检测当前主题模式
def get_theme_mode():
    """获取当前Streamlit主题模式"""
    try:
        # 尝试获取当前主题
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx:
            # 检查session_state中是否有主题信息
            if 'theme_mode' in st.session_state:
                return st.session_state.theme_mode
        # 默认返回light
        return 'light'
    except Exception:
        # 如果获取失败，默认返回light
        return 'light'

# 根据主题获取颜色方案 — Apple palette
def get_color_scheme():
    """返回 Apple 风格的 Plotly 图表颜色方案"""
    theme = get_theme_mode()
    if theme == 'dark':
        return {
            'bg_color': '#000000',
            'paper_color': '#1C1C1E',
            'text_color': '#F5F5F7',
            'text_secondary': '#AEAEB2',
            'grid_color': 'rgba(255,255,255,0.06)',
            'zero_line': 'rgba(255,255,255,0.12)',
            'border_color': 'rgba(255,255,255,0.08)',
            'hover_bg': 'rgba(44,44,46,0.95)',
            'hover_border': '#0A84FF',
            'accent': '#0A84FF',
        }
    else:
        return {
            'bg_color': '#F5F5F7',
            'paper_color': '#FFFFFF',
            'text_color': '#1D1D1F',
            'text_secondary': '#6E6E73',
            'grid_color': 'rgba(0,0,0,0.04)',
            'zero_line': 'rgba(0,0,0,0.10)',
            'border_color': 'rgba(0,0,0,0.06)',
            'hover_bg': 'rgba(255,255,255,0.96)',
            'hover_border': '#007AFF',
            'accent': '#007AFF',
        }

# 统一的 Plotly 图表 Apple 风格模板
def get_plotly_template(colors):
    """返回 Apple 风格 Plotly layout 基础配置"""
    return dict(
        plot_bgcolor=colors['paper_color'],
        paper_bgcolor=colors['bg_color'],
        font=dict(
            color=colors['text_color'],
            size=13,
            family='-apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", sans-serif'
        ),
        xaxis=dict(
            gridcolor=colors['grid_color'],
            zerolinecolor=colors['zero_line'],
            color=colors['text_secondary'],
            tickfont=dict(size=11),
            title_font=dict(size=12, color=colors['text_color']),
        ),
        yaxis=dict(
            gridcolor=colors['grid_color'],
            zerolinecolor=colors['zero_line'],
            color=colors['text_secondary'],
            tickfont=dict(size=11),
            title_font=dict(size=12, color=colors['text_color']),
        ),
        hoverlabel=dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['hover_border'],
            font=dict(size=12, color=colors['text_color'], family='SF Mono, Menlo, monospace'),
            namelength=-1,
        ),
        legend=dict(
            bgcolor='rgba(255,255,255,0.0)',
            bordercolor='rgba(0,0,0,0)',
            font=dict(size=12, color=colors['text_secondary']),
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
        ),
        margin=dict(l=40, r=24, t=48, b=40),
        dragmode='pan',
        modebar=dict(
            bgcolor='rgba(0,0,0,0)',
            color=colors['text_secondary'],
            activecolor=colors['accent'],
            orientation='h',
        ),
        colorway=['#007AFF', '#FF3B30', '#34C759', '#FF9500', '#5AC8FA', '#AF52DE'],
    )

# 自定义CSS样式 — Apple-style premium minimalist
st.markdown("""
<style>
    /* ═══════════════════════════════════════════════
     * Design tokens — Apple HIG inspired
     * ═══════════════════════════════════════════════ */
    :root {
        --apple-bg: #F5F5F7;
        --apple-paper: #FFFFFF;
        --apple-text: #1D1D1F;
        --apple-text-2: #6E6E73;
        --apple-text-3: #AEAEB2;
        --apple-accent: #007AFF;
        --apple-accent-hover: #0062CC;
        --apple-border: rgba(0,0,0,0.06);
        --apple-shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
        --apple-shadow-md: 0 4px 16px rgba(0,0,0,0.06);
        --apple-shadow-lg: 0 8px 32px rgba(0,0,0,0.08);
        --apple-radius-sm: 10px;
        --apple-radius-md: 16px;
        --apple-radius-lg: 20px;
        --apple-radius-pill: 980px;
        --apple-green: #34C759;
        --apple-red: #FF3B30;
        --apple-orange: #FF9500;
        --apple-teal: #5AC8FA;
    }

    /* ── Global · base ── */
    .main {
        background-color: rgba(245, 245, 247, 0.78);
        backdrop-filter: blur(18px) saturate(140%);
        -webkit-backdrop-filter: blur(18px) saturate(140%);
        color: #1D1D1F;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", sans-serif;
        -webkit-font-smoothing: antialiased;
        position: relative;
        z-index: 1;
    }
    /* Ensure the app root is transparent */
    [data-testid="stApp"] {
        background: transparent !important;
    }
    #root {
        background: transparent !important;
    }
    body {
        background: linear-gradient(135deg, #E8E6E1 0%, #DDD9D2 30%, #D5D0C8 60%, #E0DBD4 100%) !important;
        overflow-x: hidden;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* ── Sidebar · frosted glass ── */
    [data-testid="stSidebar"] {
        background: rgba(245,245,247,0.82);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border-right: 1px solid rgba(0,0,0,0.06);
    }
    [data-testid="stSidebar"] .block-container {
        padding: 1.5rem 1.25rem;
    }

    /* ── Typography ── */
    h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.022em !important;
        color: #1D1D1F !important;
        margin-bottom: 0.25rem !important;
    }
    h2 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.018em !important;
        color: #1D1D1F !important;
    }
    h3 {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: #1D1D1F !important;
    }
    h4, h5, h6 {
        font-weight: 600 !important;
        color: #1D1D1F !important;
    }
    p, li, span, div {
        color: #1D1D1F;
    }

    /* ── Accent text helpers ── */
    .accent-positive {
        color: #34C759 !important;
        font-weight: 600;
    }
    .accent-negative {
        color: #FF3B30 !important;
        font-weight: 600;
    }
    .accent-primary {
        color: #007AFF !important;
        font-weight: 600;
    }
    .accent-highlight {
        color: #FF9500 !important;
        font-weight: 590;
    }
    .text-caption {
        color: #6E6E73 !important;
        font-size: 0.82rem;
        letter-spacing: 0.01em;
    }
    .text-mono {
        font-family: 'SF Mono', 'Cascadia Code', 'JetBrains Mono', 'Menlo', monospace !important;
        font-feature-settings: "tnum";
    }

    /* ── Section accent bar ── */
    .section-accent {
        border-left: 3px solid #007AFF;
        padding-left: 1rem;
        margin: 1rem 0;
    }

    /* ── Buttons · pill shape ── */
    .stButton > button {
        background: #007AFF;
        color: #FFFFFF;
        border: none;
        border-radius: 980px;
        padding: 0.6rem 1.5rem;
        font-weight: 590;
        font-size: 0.9rem;
        letter-spacing: -0.01em;
        transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
        box-shadow: none;
    }
    .stButton > button:hover {
        background: #0062CC;
        box-shadow: 0 2px 12px rgba(0,122,255,0.25);
        transform: none;
    }
    .stButton > button:active {
        background: #0051AA;
        transform: scale(0.98);
    }

    /* ── Inputs · clean border ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > select {
        background: #FFFFFF;
        color: #1D1D1F;
        border: 1px solid rgba(0,0,0,0.12);
        border-radius: 10px;
        padding: 0.5rem 0.75rem;
        font-size: 0.9rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stDateInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #007AFF;
        box-shadow: 0 0 0 3px rgba(0,122,255,0.12);
        outline: none;
    }

    /* ── Tables · subtle striped ── */
    .stTable, [data-testid="stTable"] {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.06);
    }
    .stTable table {
        border-collapse: separate;
        border-spacing: 0;
    }
    .stTable thead th {
        background: #FAFAFA;
        color: #6E6E73;
        font-weight: 590;
        font-size: 0.8rem;
        text-transform: none;
        letter-spacing: -0.01em;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid rgba(0,0,0,0.06);
    }
    .stTable tbody td {
        padding: 0.65rem 1rem;
        font-size: 0.9rem;
        border-bottom: 1px solid rgba(0,0,0,0.04);
        color: #1D1D1F;
    }
    .stTable tbody tr:last-child td {
        border-bottom: none;
    }
    .stTable tbody tr:nth-child(even) {
        background: rgba(0,0,0,0.015);
    }

    /* ── DataFrame styling ── */
    [data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.06);
    }

    /* ── Charts · card-like ── */
    .stPlotlyChart {
        background: #FFFFFF;
        border-radius: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.06);
        padding: 1rem;
        margin: 0.75rem 0;
    }

    /* ── Expander · frosted card ── */
    [data-testid="stExpander"] {
        background: #FFFFFF;
        border-radius: 16px;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        overflow: hidden;
    }
    [data-testid="stExpander"] details {
        border-radius: 16px;
    }
    [data-testid="stExpander"] summary {
        padding: 0.75rem 1.25rem;
        font-weight: 590;
        color: #1D1D1F;
    }

    /* ── Metrics · big numbers ── */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.06);
    }
    [data-testid="stMetric"] label {
        color: #6E6E73 !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #1D1D1F !important;
    }

    /* ── Success / Warning / Error ── */
    [data-testid="stSuccess"] {
        background: rgba(52,199,89,0.08);
        border: 1px solid rgba(52,199,89,0.2);
        border-radius: 12px;
        color: #248A3D;
    }
    [data-testid="stWarning"] {
        background: rgba(255,149,0,0.08);
        border: 1px solid rgba(255,149,0,0.2);
        border-radius: 12px;
        color: #C46500;
    }
    [data-testid="stError"] {
        background: rgba(255,59,48,0.08);
        border: 1px solid rgba(255,59,48,0.2);
        border-radius: 12px;
        color: #C41E1E;
    }
    [data-testid="stInfo"] {
        background: rgba(0,122,255,0.06);
        border: 1px solid rgba(0,122,255,0.15);
        border-radius: 12px;
        color: #0062CC;
    }

    /* ── Dividers ── */
    hr {
        border: none;
        border-top: 1px solid rgba(0,0,0,0.06);
        margin: 1.5rem 0;
    }

    /* ── Scrollbar · thin ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(0,0,0,0.15);
        border-radius: 20px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0,0,0,0.25);
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        border-radius: 16px;
        border: 1.5px dashed rgba(0,0,0,0.12);
        background: transparent;
    }

    /* ═══════════════════════════════════════════════
     * Dark mode overrides
     * ═══════════════════════════════════════════════ */
    [data-theme="dark"] .main {
        background-color: rgba(28, 28, 30, 0.78);
        backdrop-filter: blur(18px) saturate(140%);
        -webkit-backdrop-filter: blur(18px) saturate(140%);
        color: #F5F5F7;
    }
    [data-theme="dark"] body {
        background: linear-gradient(135deg, #1C1C1E 0%, #161618 40%, #1E1E20 70%, #18181A 100%) !important;
    }
    [data-theme="dark"] [data-testid="stSidebar"] {
        background: rgba(28,28,30,0.82);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3,
    [data-theme="dark"] h4, [data-theme="dark"] h5, [data-theme="dark"] h6,
    [data-theme="dark"] p, [data-theme="dark"] li, [data-theme="dark"] span, [data-theme="dark"] div {
        color: #F5F5F7;
    }
    [data-theme="dark"] .accent-primary {
        color: #0A84FF !important;
    }
    [data-theme="dark"] .text-caption {
        color: #AEAEB2 !important;
    }
    [data-theme="dark"] .stTextInput > div > div > input,
    [data-theme="dark"] .stNumberInput > div > div > input,
    [data-theme="dark"] .stDateInput > div > div > input,
    [data-theme="dark"] .stSelectbox > div > div > select {
        background: #1C1C1E;
        color: #F5F5F7;
        border: 1px solid rgba(255,255,255,0.12);
    }
    [data-theme="dark"] .stTable thead th {
        background: #1C1C1E;
        color: #AEAEB2;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    [data-theme="dark"] .stTable tbody td {
        color: #F5F5F7;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    [data-theme="dark"] .stTable tbody tr:nth-child(even) {
        background: rgba(255,255,255,0.025);
    }
    [data-theme="dark"] .stPlotlyChart,
    [data-theme="dark"] [data-testid="stExpander"],
    [data-theme="dark"] [data-testid="stMetric"] {
        background: #1C1C1E;
        border: 1px solid rgba(255,255,255,0.08);
    }
    [data-theme="dark"] hr {
        border-top: 1px solid rgba(255,255,255,0.08);
    }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem; }
        .stPlotlyChart { padding: 0.5rem; margin: 0.5rem 0; }
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# Interactive 3D background — frosted glass + sphere
# ═══════════════════════════════════════════════
st.markdown("""
<canvas id="bg-sphere-canvas" style="position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:0;display:block;pointer-events:auto;"></canvas>
<script>
(function(){
    /* ── Load Three.js from multiple CDN fallbacks ── */
    var CDNS = [
        'https://cdn.jsdelivr.net/npm/three@0.157.0/build/three.min.js',
        'https://cdn.bootcdn.net/ajax/libs/three.js/r128/three.min.js',
        'https://unpkg.com/three@0.157.0/build/three.min.js'
    ];
    var cdnIdx = 0;
    function tryLoad() {
        if (cdnIdx >= CDNS.length) { console.warn('Three.js failed to load from all CDNs'); return; }
        var s = document.createElement('script');
        s.src = CDNS[cdnIdx];
        s.onload = init;
        s.onerror = function() { cdnIdx++; tryLoad(); };
        document.head.appendChild(s);
    }
    tryLoad();

    function init() {
        if (typeof THREE === 'undefined') { setTimeout(init, 200); return; }

        var canvas = document.getElementById('bg-sphere-canvas');
        var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setClearColor(0x000000, 0.0);

        var scene = new THREE.Scene();
        var camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.5, 20);
        camera.position.z = 6.5;

        /* ── GLSL simplex noise ── */
        var noiseGLSL = `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(0.1666666667,0.3333333333);
  vec3 i=floor(v+dot(v,C.yyy));
  vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz);
  vec3 l=1.0-g;
  vec3 i1=min(g.xyz,l.zxy);
  vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx;
  vec3 x2=x0-i2+C.yyy;
  vec3 x3=x0-0.5;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857;
  vec3 ns=n_*(1.0/3.0)-vec3(0.1666666667);
  vec4 j=p-49.0*floor(p*ns.z*ns.z);
  vec4 x_=floor(j*ns.z);
  vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+vec4(0.0,1.0,1.0,1.0);
  vec4 y=y_*ns.y+vec4(0.0,1.0,1.0,1.0);
  vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy);
  vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0;
  vec4 s1=floor(b1)*2.0+1.0;
  vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;
  vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x);
  vec3 p1=vec3(a0.zw,h.y);
  vec3 p2=vec3(a1.xy,h.z);
  vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);
  m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}`;

        /* ── Shader uniforms ── */
        var uniforms = {
            uTime: { value: 0 },
            uMouse3D: { value: new THREE.Vector3(99, 99, 99) },
            uMouseActive: { value: 0 },
        };

        var vertexShader = noiseGLSL + `
varying vec3 vNormal;
varying vec3 vPosition;
varying float vDisplacement;
varying vec3 vWorldNormal;
uniform float uTime;
uniform vec3 uMouse3D;
uniform float uMouseActive;

void main() {
    float n1 = snoise(position * 2.2 + uTime * 0.35);
    float n2 = snoise(position * 4.5 - uTime * 0.25) * 0.55;
    float n3 = snoise(position * 7.0 + uTime * 0.45) * 0.3;
    float displacement = (n1 + n2 + n3) * 0.04;

    /* Mouse turbulence */
    float dist = length(position - uMouse3D);
    float influence = exp(-dist * 2.8) * uMouseActive;
    float turb = (sin(dist * 14.0 - uTime * 10.0) * 0.5
                + sin(dist * 9.0 + uTime * 7.0) * 0.35
                + cos(dist * 18.0 - uTime * 7.0) * 0.25) * influence * 0.12;
    displacement += turb;

    vec3 newPos = position + normal * displacement;
    vDisplacement = displacement;
    vNormal = normalize(normalMatrix * normal);
    vWorldNormal = normal;
    vPosition = position;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPos, 1.0);
}`;

        var fragmentShader = `
varying vec3 vNormal;
varying vec3 vPosition;
varying float vDisplacement;
varying vec3 vWorldNormal;
uniform float uTime;
uniform vec3 uMouse3D;
uniform float uMouseActive;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    /* Base warm-red, slowly drifting hue */
    float hue = 0.985 + sin(uTime * 0.18) * 0.05 + cos(uTime * 0.23) * 0.04 + sin(uTime * 0.09) * 0.03;
    float sat = 0.70 + sin(uTime * 0.31) * 0.14;
    float val = 0.72 + sin(uTime * 0.22) * 0.10;
    vec3 baseColor = hsv2rgb(vec3(fract(hue), sat, val));

    /* Mouse rainbow */
    float dist = length(vPosition - uMouse3D);
    float influence = exp(-dist * 2.5) * uMouseActive;

    /* Iridescent rings */
    float ring1 = exp(-abs(dist - 0.15) * 20.0);
    float ring2 = exp(-abs(dist - 0.35) * 12.0);
    float ring3 = exp(-abs(dist - 0.55) * 8.0);
    float rings = ring1 * 0.7 + ring2 * 0.4 + ring3 * 0.25;

    float rainbowHue = fract(dist * 0.7 - uTime * 0.13 + sin(uTime * 2.0 + dist * 5.0) * 0.1);
    vec3 rainbowColor = hsv2rgb(vec3(rainbowHue, 0.82, 0.92));
    vec3 color = mix(baseColor, rainbowColor, influence * 0.65);
    color = mix(color, rainbowColor * 1.3, rings * influence);

    /* Fresnel */
    vec3 viewDir = vec3(0.0, 0.0, 1.0);
    float fresnel = pow(1.0 - abs(dot(vWorldNormal, viewDir)), 3.5);
    vec3 edgeColor = hsv2rgb(vec3(fract(hue + 0.08), 0.5, 0.85));
    color = mix(color, edgeColor, fresnel * 0.28);

    /* Lighting */
    vec3 lightDir = normalize(vec3(0.8, 0.6, 1.2));
    float diffuse = dot(vWorldNormal, lightDir) * 0.5 + 0.5;
    float specular = pow(max(dot(reflect(-lightDir, vWorldNormal), viewDir), 0.0), 32.0) * 0.2;
    color *= (0.50 + diffuse * 0.58 + specular * 0.55);

    /* Surface noise detail */
    color += vDisplacement * 2.5;
    float edgeFade = 1.0 - fresnel * 0.12;
    color *= edgeFade;

    gl_FragColor = vec4(color, 1.0);
}`;

        /* ── Build sphere ── */
        var geometry = new THREE.SphereGeometry(1.6, 96, 96);
        var material = new THREE.ShaderMaterial({
            uniforms: uniforms,
            vertexShader: vertexShader,
            fragmentShader: fragmentShader,
        });
        var sphere = new THREE.Mesh(geometry, material);
        scene.add(sphere);

        /* ── Mouse tracking ── */
        var mouse = new THREE.Vector2();
        var raycaster = new THREE.Raycaster();
        var mouse3DTarget = new THREE.Vector3(99, 99, 99);
        var mouseActiveTarget = 0;
        var lastRaycast = 0;

        function updateMouse(event) {
            mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
            var now = performance.now() * 0.001;
            if (now - lastRaycast < 0.03) return;
            lastRaycast = now;
            raycaster.setFromCamera(mouse, camera);
            var intersects = raycaster.intersectObject(sphere);
            if (intersects.length > 0) {
                mouse3DTarget.copy(intersects[0].point);
                sphere.worldToLocal(mouse3DTarget);
                mouseActiveTarget = 1.0;
            } else {
                mouseActiveTarget = 0.0;
            }
        }

        window.addEventListener('mousemove', updateMouse, { passive: true });
        window.addEventListener('touchmove', function(e) {
            if (e.touches.length > 0) updateMouse({ clientX: e.touches[0].clientX, clientY: e.touches[0].clientY });
        }, { passive: true });
        window.addEventListener('touchend', function() { mouseActiveTarget = 0.0; });
        window.addEventListener('mouseleave', function() { mouseActiveTarget = 0.0; });
        window.addEventListener('resize', function() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        /* ── Render loop ── */
        var clock = new THREE.Clock();
        function animate() {
            requestAnimationFrame(animate);
            var dt = Math.min(clock.getDelta(), 0.1);
            uniforms.uTime.value += dt;
            uniforms.uMouse3D.value.lerp(mouse3DTarget, 0.10);
            uniforms.uMouseActive.value += (mouseActiveTarget - uniforms.uMouseActive.value) * 0.07;
            sphere.rotation.y += dt * 0.06;
            sphere.rotation.x += dt * 0.025;
            renderer.render(scene, camera);
        }
        animate();
    }
})();
</script>
""", unsafe_allow_html=True)

# 获取股票数据
def get_stock_data(stock_code, start_date, end_date):
    st.write(f"正在获取 {stock_code} 从 {start_date} 到 {end_date} 的数据...")
    
    def retry_with_backoff(func, max_retries=3, initial_delay=1):
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                    st.write(f"第 {attempt + 1} 次尝试失败，等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    raise e

    try:
        # 优先使用 TickFlow
        try:
            tf = get_tickflow_client()
            if tf:
                # 转换股票代码格式 - 支持A股和美股
                # 检查是否已经带后缀
                if '.' in stock_code:
                    tickflow_code = stock_code
                elif stock_code.startswith('6') or stock_code.startswith('5'):
                    tickflow_code = f"{stock_code}.SH"
                elif stock_code.startswith('0') or stock_code.startswith('3'):
                    tickflow_code = f"{stock_code}.SZ"
                elif stock_code.startswith('8') or stock_code.startswith('4'):
                    tickflow_code = f"{stock_code}.BJ"
                else:
                    # 假设是美股
                    tickflow_code = f"{stock_code}.US"
                
                st.write(f"尝试使用 TickFlow 获取 {tickflow_code}...")
                def fetch_tickflow():
                    return tf.klines.get(tickflow_code, period="1d", count=10000, as_dataframe=True)
                
                df = retry_with_backoff(fetch_tickflow)
                
                if not df.empty:
                    # 处理 TickFlow 返回的 DataFrame
                    if 'timestamp' in df.columns:
                        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('date', inplace=True)
                    
                    df.rename(columns={
                        'close': 'close',
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'volume': 'volume'
                    }, inplace=True)
                    
                    df.index = pd.to_datetime(df.index)
                    df = df[(df.index >= start_date) & (df.index <= end_date)]
                    
                    st.write(f"✓ 使用 TickFlow 获取到 {len(df)} 条数据")
                    return df
                else:
                    st.write("✗ TickFlow 返回空数据")
        except Exception as e:
            st.write(f"✗ TickFlow 获取数据时出错: {str(e)[:100]}...")
        
        st.write("已停用 efinance 数据源，继续尝试 yfinance。")
        
        # 使用yfinance作为备用数据源（禁用缓存以避免权限问题）
        try:
            def fetch_yfinance(code):
                return yf.download(code, start=start_date, end=end_date, threads=False, progress=False, timeout=20)
            
            # 根据代码类型确定yfinance代码
            if stock_code.startswith('6') or stock_code.startswith('5'):
                yf_code = f"{stock_code}.SS"
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                yf_code = f"{stock_code}.SZ"
            elif stock_code.startswith('8') or stock_code.startswith('4'):
                yf_code = f"{stock_code}.BJ"
            elif '.' in stock_code:
                yf_code = stock_code
            else:
                yf_code = stock_code  # 美股直接使用代码
            
            st.write(f"尝试使用yfinance获取 {yf_code} 的数据...")
            data = retry_with_backoff(lambda: fetch_yfinance(yf_code))
            
            if not data.empty:
                data.rename(columns={
                    'Close': 'close',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Volume': 'volume'
                }, inplace=True)
                st.write(f"✓ 使用 yfinance 获取到 {len(data)} 条数据")
                return data
            else:
                st.write(f"✗ yfinance 未能获取到 {yf_code} 的数据")
        except Exception as e:
            st.write(f"✗ yfinance 获取数据时出错: {str(e)[:100]}...")
        
        st.warning("所有数据源均无法获取数据！")
        st.info("请检查：1. 网络连接 2. 代理设置 3. 股票代码是否正确")
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"获取数据时出错: {str(e)}")
        return pd.DataFrame()

# 获取上证指数数据作为基准
def get_benchmark_data(start_date, end_date):
    st.write(f"正在获取上证指数从 {start_date} 到 {end_date} 的数据...")
    try:
        def retry_with_backoff(func, max_retries=3, initial_delay=1):
            for attempt in range(max_retries):
                try:
                    return func()
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                        st.write(f"第 {attempt + 1} 次尝试失败，等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                    else:
                        raise e

        # 优先使用 TickFlow
        try:
            tf = get_tickflow_client()
            if tf:
                def fetch_tickflow():
                    return tf.klines.get("000001.SH", period="1d", count=10000, as_dataframe=True)
                
                df = retry_with_backoff(fetch_tickflow)
                
                if not df.empty:
                    # 处理 TickFlow 返回的 DataFrame
                    if 'timestamp' in df.columns:
                        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('date', inplace=True)
                    
                    df.rename(columns={'close': 'close'}, inplace=True)
                    df.index = pd.to_datetime(df.index)
                    df = df[(df.index >= start_date) & (df.index <= end_date)]
                    df['benchmark_return'] = df['close'].pct_change()
                    df['cumulative_benchmark'] = (1 + df['benchmark_return']).cumprod()
                    
                    st.write(f"✓ 使用 TickFlow 获取到 {len(df)} 条上证指数数据")
                    return df
                else:
                    st.write("✗ TickFlow 返回空数据")
        except Exception as e:
            st.write(f"✗ TickFlow 获取上证指数时出错: {str(e)[:100]}...")
        
        st.write("已停用 efinance 上证指数数据源，继续尝试 yfinance。")
        
        # 尝试使用 yfinance
        try:
            def fetch_yfinance():
                return yf.download('000001.SS', start=start_date, end=end_date, threads=False, progress=False, timeout=20)
            
            data = retry_with_backoff(fetch_yfinance)
            
            if not data.empty:
                data.rename(columns={'Close': 'close'}, inplace=True)
                
                data['benchmark_return'] = data['close'].pct_change()
                data['cumulative_benchmark'] = (1 + data['benchmark_return']).cumprod()
                
                st.write(f"✓ 使用 yfinance 获取到 {len(data)} 条上证指数数据")
                return data
            else:
                st.write("✗ yfinance 未能获取到上证指数数据")
                return pd.DataFrame()
        except Exception as e:
            st.write(f"✗ yfinance 获取上证指数数据时出错: {str(e)[:100]}...")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"获取上证指数数据时出错: {str(e)}")
        return pd.DataFrame()

# 获取股票名称
def get_stock_name(stock_code):
    try:
        def retry_with_backoff(func, max_retries=3, initial_delay=1):
            for attempt in range(max_retries):
                try:
                    return func()
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(delay)
                    else:
                        raise e

        # 优先使用 TickFlow
        try:
            tf = get_tickflow_client()
            if tf:
                # 支持A股和美股
                if '.' in stock_code:
                    tickflow_code = stock_code
                elif stock_code.startswith('6') or stock_code.startswith('5'):
                    tickflow_code = f"{stock_code}.SH"
                elif stock_code.startswith('0') or stock_code.startswith('3'):
                    tickflow_code = f"{stock_code}.SZ"
                elif stock_code.startswith('8') or stock_code.startswith('4'):
                    tickflow_code = f"{stock_code}.BJ"
                else:
                    tickflow_code = f"{stock_code}.US"
                
                def fetch_tickflow():
                    return tf.instruments.batch(symbols=[tickflow_code])
                
                instruments = retry_with_backoff(fetch_tickflow)
                if instruments and len(instruments) > 0:
                    stock_name = instruments[0].get('name', '')
                    if stock_name:
                        st.write(f"股票名称: {stock_name}")
                        return stock_name
        except Exception as e:
            st.write(f"✗ TickFlow 获取股票名称时出错: {str(e)[:100]}...")
        
        st.write("已停用 efinance 股票名称数据源。")
        
        # 对于美股，直接返回股票代码作为名称（避免yfinance缓存权限问题）
        if not (stock_code.startswith('6') or stock_code.startswith('5') or 
                stock_code.startswith('0') or stock_code.startswith('3') or
                stock_code.startswith('8') or stock_code.startswith('4')):
            return stock_code.upper()
            
    except Exception as e:
        st.write(f"获取股票名称时出错: {str(e)[:100]}...")
    
    return f"股票代码: {stock_code}"

# 计算买卖点胜率分析
def calculate_trade_win_rate(strategy_data):
    """
    计算策略的买卖点胜率
    :param strategy_data: 包含signal和close列的DataFrame
    :return: 包含各种胜率指标的字典
    """
    buy_signals = strategy_data[strategy_data.get('signal', 0) == 1]
    sell_signals = strategy_data[strategy_data.get('signal', 0) == -1]
    
    trades = []
    current_position = 0
    entry_price = 0
    
    for date, row in strategy_data.iterrows():
        if row.get('signal', 0) == 1 and current_position == 0:
            current_position = 1
            entry_price = row['close']
        elif row.get('signal', 0) == -1 and current_position == 1:
            exit_price = row['close']
            profit = (exit_price - entry_price) / entry_price
            trades.append({
                'entry_date': date,
                'exit_date': date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'profit': profit,
                'win': profit > 0
            })
            current_position = 0
            entry_price = 0
    
    if current_position == 1 and len(strategy_data) > 0:
        last_date = strategy_data.index[-1]
        exit_price = strategy_data.loc[last_date, 'close']
        profit = (exit_price - entry_price) / entry_price
        trades.append({
            'entry_date': entry_price,
            'exit_date': last_date,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit': profit,
            'win': profit > 0
        })
    
    if len(trades) == 0:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_win': 0,
            'max_loss': 0,
            'trades': trades
        }
    
    winning_trades = [t for t in trades if t['win']]
    losing_trades = [t for t in trades if not t['win']]
    
    total_profit = sum(t['profit'] for t in winning_trades)
    total_loss = abs(sum(t['profit'] for t in losing_trades))
    
    return {
        'total_trades': len(trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': len(winning_trades) / len(trades),
        'avg_profit': total_profit / len(winning_trades) if winning_trades else 0,
        'avg_loss': total_loss / len(losing_trades) if losing_trades else 0,
        'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf'),
        'max_win': max(t['profit'] for t in winning_trades) if winning_trades else 0,
        'max_loss': min(t['profit'] for t in losing_trades) if losing_trades else 0,
        'trades': trades
    }

# 计算技术指标
def calculate_indicators(data):
    # 计算价格均线（改为MA25）
    data['MA25'] = data['close'].rolling(window=25).mean()
    
    # 计算成交量均线
    data['VMA5'] = data['volume'].rolling(window=5).mean()
    data['VMA60'] = data['volume'].rolling(window=60).mean()
    
    # 计算成交量均线缠绕（差值百分比）
    data['VMA_diff'] = abs(data['VMA5'] - data['VMA60']) / data['VMA60'] * 100
    
    # 计算MACD指标
    exp1 = data['close'].ewm(span=12, adjust=False).mean()
    exp2 = data['close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
    data['MACD_Hist'] = data['MACD'] - data['Signal']
    
    # 计算RSI指标
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    return data

# 实现交易策略
def implement_strategy(data):
    # 初始化仓位和交易信号
    data['position'] = 0.0  # 0: 空仓, 0.2: 1/5仓位, 1: 满仓（使用float类型避免类型警告）
    data['signal'] = 0  # 0: 无信号, 1: 买入, 2: 加仓, -1: 卖出, 3: 买回, 4: 止损
    data['buy_price'] = 0.0  # 记录买入价格
    
    # 检查是否存在必要的指标列
    has_macd = 'MACD' in data.columns and 'Signal' in data.columns
    has_rsi = 'RSI' in data.columns
    has_vma = 'VMA5' in data.columns and 'VMA60' in data.columns and 'VMA_diff' in data.columns
    has_ma25 = 'MA25' in data.columns
    
    # 记录卖出日期
    sell_dates = []
    
    # 遍历数据
    for i in range(60, len(data)):
        current = data.iloc[i]
        previous = data.iloc[i-1]
        
        # 更新买入价格
        if previous['position'] == 0 and current['position'] > 0:
            # 新买入，记录买入价格
            data.loc[data.index[i], 'buy_price'] = current['close']
        elif previous['position'] == 0.2 and current['position'] == 1:
            # 加仓，更新买入价格为加权平均
            data.loc[data.index[i], 'buy_price'] = (previous['buy_price'] * 0.2 + current['close'] * 0.8)
        else:
            # 保持买入价格不变
            data.loc[data.index[i], 'buy_price'] = previous['buy_price']
        
        # 止损逻辑：当股价下跌超过8%时止损
        if previous['position'] > 0 and current['close'] < previous['buy_price'] * 0.92:
            data.loc[data.index[i], 'position'] = 0
            data.loc[data.index[i], 'signal'] = 4  # 止损信号
            sell_dates.append(data.index[i])
            continue
        
        # 卖出信号：股价破掉25日均线
        if has_ma25 and current['close'] < current['MA25'] and previous['position'] > 0:
            data.loc[data.index[i], 'position'] = 0
            data.loc[data.index[i], 'signal'] = -1
            sell_dates.append(data.index[i])
            continue
        
        # 已有仓位，检查是否需要加仓
        if previous['position'] == 0.2:
            # 股价上涨且成交量5日均线上穿60日均线，同时MACD金叉
            if has_macd and has_vma and current['close'] > previous['close'] and \
               current['VMA5'] > current['VMA60'] and \
               previous['VMA5'] <= previous['VMA60'] and \
               current['MACD'] > current['Signal'] and \
               previous['MACD'] <= previous['Signal']:
                data.loc[data.index[i], 'position'] = 1
                data.loc[data.index[i], 'signal'] = 2
            # 股价上涨且成交量逐渐远离60日均线，同时RSI在正常区间
            elif has_vma and has_rsi and current['close'] > previous['close'] and \
                 current['VMA5'] > current['VMA60'] and \
                 current['VMA_diff'] > previous['VMA_diff'] and \
                 30 < current['RSI'] < 70:
                data.loc[data.index[i], 'position'] = 1
                data.loc[data.index[i], 'signal'] = 2
            else:
                data.loc[data.index[i], 'position'] = previous['position']
        
        # 空仓，检查是否需要买入
        elif previous['position'] == 0:
            # 检查是否在卖出后2-3个交易日内
            buyback = False
            if sell_dates:
                last_sell_date = sell_dates[-1]
                days_since_sell = (data.index[i] - last_sell_date).days
                # 卖出后2-3个交易日内，股价突破25日均线
                if has_ma25 and 2 <= days_since_sell <= 3 and current['close'] > current['MA25']:
                    buyback = True
            
            # 原始买入条件：股价回踩25日均线且成交量缩量，同时MACD和RSI指标配合
            price_near_ma = has_ma25 and abs(current['close'] - current['MA25']) / current['MA25'] < 0.03
            volume_contraction = has_vma and current['VMA_diff'] < 7
            macd_bullish = has_macd and current['MACD'] > current['Signal']  # MACD金叉
            rsi_neutral = has_rsi and 30 < current['RSI'] < 70  # RSI在正常区间
            
            # 简化条件：如果缺少指标，使用更基本的条件
            basic_condition = price_near_ma and volume_contraction
            advanced_condition = (macd_bullish or rsi_neutral) if (has_macd or has_rsi) else True
            
            if buyback:
                # 全仓买回
                data.loc[data.index[i], 'position'] = 1
                data.loc[data.index[i], 'signal'] = 3
            elif basic_condition and advanced_condition:
                # 原始买入条件，1/5仓位，加入技术指标过滤
                data.loc[data.index[i], 'position'] = 0.2
                data.loc[data.index[i], 'signal'] = 1
            else:
                data.loc[data.index[i], 'position'] = 0
        
        else:
            data.loc[data.index[i], 'position'] = previous['position']
    
    return data

# 计算策略收益率
def calculate_returns(data, benchmark_data=None):
    # 计算每日收益率
    data['daily_return'] = data['close'].pct_change()
    
    # 计算策略收益率
    data['strategy_return'] = data['position'].shift(1) * data['daily_return']
    
    # 计算累计收益率
    data['cumulative_return'] = (1 + data['strategy_return']).cumprod()
    
    # 计算基准收益率（买入持有）
    data['benchmark_return'] = data['daily_return'].cumsum()
    
    # 计算与上证指数的对比
    if benchmark_data is not None and not benchmark_data.empty:
        # 对齐日期
        aligned_benchmark = benchmark_data.reindex(data.index)
        
        # 计算累计基准收益率
        data['cumulative_benchmark'] = aligned_benchmark['cumulative_benchmark']
        
        # 计算超额收益
        data['excess_return'] = data['cumulative_return'] - data['cumulative_benchmark']
    
    return data

# 计算策略性能指标
def calculate_performance_metrics(data, initial_capital=100000, benchmark_data=None):
    # 计算总收益率
    total_return = data['cumulative_return'].iloc[-1] - 1
    
    # 计算年化收益率
    days = (data.index[-1] - data.index[0]).days
    annual_return = (1 + total_return) ** (365 / days) - 1
    
    # 计算最大回撤
    data['cum_max'] = data['cumulative_return'].cummax()
    data['drawdown'] = (data['cumulative_return'] - data['cum_max']) / data['cum_max']
    max_drawdown = data['drawdown'].min()
    
    # 计算夏普比率（假设无风险利率为0）
    daily_returns = data['strategy_return'].dropna()
    sharpe_ratio = daily_returns.mean() / daily_returns.std() * (252 ** 0.5) if daily_returns.std() > 0 else 0
    
    # 计算Sortino比率（只考虑下行风险）
    downside_returns = daily_returns[daily_returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 1
    sortino_ratio = daily_returns.mean() / downside_std * (252 ** 0.5)
    
    # 计算收益波动率
    volatility = daily_returns.std() * (252 ** 0.5)
    
    # 计算下行风险
    downside_risk = downside_std * (252 ** 0.5)
    
    # 计算Alpha和Beta
    alpha = 0
    beta = 1
    if benchmark_data is not None and not benchmark_data.empty:
        # 对齐日期
        aligned_benchmark = benchmark_data.reindex(data.index)
        benchmark_returns = aligned_benchmark['benchmark_return'].dropna()
        strategy_returns = data['strategy_return'].reindex(benchmark_returns.index).dropna()
        
        if len(benchmark_returns) > 0 and len(strategy_returns) > 0:
            # 计算Beta
            covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
            benchmark_variance = np.var(benchmark_returns)
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 1
            
            # 计算Alpha（假设无风险利率为0）
            alpha = (strategy_returns.mean() - beta * benchmark_returns.mean()) * 252
    
    # 计算信息比率
    information_ratio = 0
    if 'excess_return' in data.columns:
        excess_returns = data['excess_return'].diff().dropna()
        if len(excess_returns) > 0:
            excess_return_mean = excess_returns.mean()
            tracking_error = excess_returns.std()
            information_ratio = excess_return_mean / tracking_error * (252 ** 0.5) if tracking_error > 0 else 0
    
    # 计算盈利额度和净利润（考虑手续费）
    total_profit = initial_capital * total_return
    
    # 计算交易次数和胜率
    buy_signals = data[data['signal'] == 1]
    sell_signals = data[data['signal'] == -1]
    buyback_signals = data[data['signal'] == 3]
    stop_loss_signals = data[data['signal'] == 4]
    
    total_trades = len(buy_signals) + len(buyback_signals)
    
    # 计算胜率
    winning_trades = 0
    if total_trades > 0:
        # 简单胜率计算：卖出时价格高于买入价格
        for i in range(len(data)):
            if data.iloc[i]['signal'] in [-1, 4]:  # 卖出或止损
                # 找到最近的买入信号
                for j in range(i-1, -1, -1):
                    if data.iloc[j]['signal'] in [1, 3]:  # 买入或买回
                        buy_price = data.iloc[j]['close']
                        sell_price = data.iloc[i]['close']
                        if sell_price > buy_price:
                            winning_trades += 1
                        break
        
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # 计算手续费（万一）
    trade_value = initial_capital * total_trades * 2  # 买入和卖出各一次
    commission = trade_value * 0.0001
    net_profit = total_profit - commission
    
    # 计算相对收益率（相对于基准）
    benchmark_total_return = 0
    relative_return = 0
    if benchmark_data is not None and not benchmark_data.empty:
        aligned_benchmark = benchmark_data.reindex(data.index)
        if not aligned_benchmark.empty:
            benchmark_total_return = aligned_benchmark['cumulative_benchmark'].iloc[-1] - 1
            relative_return = total_return - benchmark_total_return
    else:
        # 回退到使用股票本身作为基准
        benchmark_total_return = data['close'].iloc[-1] / data['close'].iloc[0] - 1
        relative_return = total_return - benchmark_total_return
    
    # 计算最大回撤比
    max_drawdown_ratio = abs(max_drawdown) / (total_return + 1) if total_return > 0 else float('inf')
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'volatility': volatility,
        'downside_risk': downside_risk,
        'alpha': alpha,
        'beta': beta,
        'information_ratio': information_ratio,
        'total_profit': total_profit,
        'net_profit': net_profit,
        'commission': commission,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'benchmark_return': benchmark_total_return,
        'relative_return': relative_return,
        'max_drawdown_ratio': max_drawdown_ratio
    }

# 生成K线图（使用plotly）
def generate_kline_chart(data, stock_code, time_frame='day', show_ma5=False, show_ma10=False, show_ma50=False, show_ma100=False):
    # 提取买卖信号
    buy_signals = data[data.get('signal', 0) == 1]
    add_signals = data[data.get('signal', 0) == 2]
    sell_signals = data[data.get('signal', 0) == -1]
    buyback_signals = data[data.get('signal', 0) == 3]
    stop_loss_signals = data[data.get('signal', 0) == 4]
    
    # 计算均线
    data['MA20'] = data['close'].rolling(window=20).mean()
    data['MA5'] = data['close'].rolling(window=5).mean()
    data['MA10'] = data['close'].rolling(window=10).mean()
    data['MA50'] = data['close'].rolling(window=50).mean()
    data['MA100'] = data['close'].rolling(window=100).mean()
    
    # Apple palette signal colors
    green = '#34C759'
    red = '#FF3B30'

    # K-line candlestick
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='K线',
        increasing=dict(line=dict(color=red, width=1)),
        decreasing=dict(line=dict(color=green, width=1)),
        increasing_fillcolor=red,
        decreasing_fillcolor=green,
    )])

    # MA20 (primary)
    fig.add_trace(go.Scatter(
        x=data.index, y=data['MA20'], mode='lines',
        name='MA20', line=dict(color='#FF9500', width=1.5),
    ))

    if show_ma5:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA5'], mode='lines',
            name='MA5', line=dict(color='#007AFF', width=1),
        ))
    if show_ma10:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA10'], mode='lines',
            name='MA10', line=dict(color='#5AC8FA', width=1),
        ))
    if show_ma50:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA50'], mode='lines',
            name='MA50', line=dict(color='#AF52DE', width=1),
        ))
    if show_ma100:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA100'], mode='lines',
            name='MA100', line=dict(color='#6E6E73', width=1),
        ))

    # Buy/Sell markers
    if not buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=buy_signals.index, y=buy_signals['close'], mode='markers',
            name='买入', marker=dict(color=red, size=10, symbol='triangle-up',
            line=dict(width=1, color='white')),
        ))
    if not add_signals.empty:
        fig.add_trace(go.Scatter(
            x=add_signals.index, y=add_signals['close'], mode='markers',
            name='加仓', marker=dict(color='#FF9500', size=10, symbol='cross',
            line=dict(width=1, color='white')),
        ))
    if not sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=sell_signals.index, y=sell_signals['close'], mode='markers',
            name='卖出', marker=dict(color=green, size=10, symbol='triangle-down',
            line=dict(width=1, color='white')),
        ))
    if not buyback_signals.empty:
        fig.add_trace(go.Scatter(
            x=buyback_signals.index, y=buyback_signals['close'], mode='markers',
            name='买回', marker=dict(color='#5AC8FA', size=10, symbol='circle',
            line=dict(width=1, color='white')),
        ))
    if not stop_loss_signals.empty:
        fig.add_trace(go.Scatter(
            x=stop_loss_signals.index, y=stop_loss_signals['close'], mode='markers',
            name='止损', marker=dict(color='#FF9500', size=10, symbol='x',
            line=dict(width=1, color='white')),
        ))

    # Layout
    colors_scheme = get_color_scheme()
    template = get_plotly_template(colors_scheme)
    fig.update_layout(**template)
    fig.update_layout(
        title=f'{stock_code} 价格走势和交易信号',
        height=550,
        xaxis_rangeslider_visible=True,
        hovermode='x unified',
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all")
                ]),
                bgcolor=colors_scheme['paper_color'],
                activecolor=colors_scheme['accent'],
                font=dict(color=colors_scheme['text_color'], size=11),
            ),
            type="category",
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
            tickangle=0,
        ),
    )
    
    return fig

# 生成成交量和均量线图表
def generate_volume_chart(data, time_frame='day'):
    # 计算均量线
    data['VMA5'] = data['volume'].rolling(window=5).mean()
    data['VMA60'] = data['volume'].rolling(window=60).mean()
    
    colors_scheme = get_color_scheme()
    template = get_plotly_template(colors_scheme)

    data['color'] = ['#FF3B30' if close > open else '#34C759' for close, open in zip(data['close'], data['open'])]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data.index, y=data['volume'], name='成交量',
        marker=dict(color=data['color'], opacity=0.25),
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data['VMA5'], mode='lines', name='VMA5',
        line=dict(color='#007AFF', width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data['VMA60'], mode='lines', name='VMA60',
        line=dict(color='#FF9500', width=1.5),
    ))

    fig.update_layout(**template)
    fig.update_layout(
        title='成交量和均量线',
        height=400,
        hovermode='x unified',
        xaxis_rangeslider_visible=True,
        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
            tickangle=0,
        ),
    )
    
    return fig

# 生成仓位和策略收益率图表
def generate_position_chart(data, time_frame='day'):
    colors_scheme = get_color_scheme()
    template = get_plotly_template(colors_scheme)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data['position'] * 100, mode='lines',
        name='仓位 (%)', line=dict(color='#34C759', width=1.5), yaxis='y1',
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=(data['cumulative_return'] - 1) * 100, mode='lines',
        name='策略收益率 (%)', line=dict(color='#007AFF', width=1.5), yaxis='y2',
    ))

    fig.update_layout(**template)
    fig.update_layout(
        title='仓位和策略收益率',
        height=400,
        hovermode='x unified',
        xaxis_rangeslider_visible=True,
        yaxis=dict(title='仓位 (%)', side='left', range=[0, 100]),
        yaxis2=dict(title='策略收益率 (%)', side='right', overlaying='y'),
        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
            tickangle=0,
        ),
    )
    
    return fig

# 生成技术指标图表
def generate_indicators_chart(data):
    # 获取颜色方案
    colors = get_color_scheme()
    
    fig = go.Figure()
    
    # 检查是否存在MACD和Signal列
    has_macd = 'MACD' in data.columns and 'Signal' in data.columns
    # 检查是否存在RSI列
    has_rsi = 'RSI' in data.columns
    
    # 添加MACD和Signal（如果存在）
    if has_macd:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MACD'],
            mode='lines',
            name='MACD',
            line=dict(color='blue', width=1.5)
        ))
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Signal'],
            mode='lines',
            name='Signal',
            line=dict(color='red', width=1.5)
        ))
    
    # 添加RSI（如果存在）
    if has_rsi:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['RSI'],
            mode='lines',
            name='RSI',
            line=dict(color='purple', width=1.5),
            yaxis='y2'
        ))
    
    # 设置图表布局
    layout_updates = {
        'title': '技术指标',
        'xaxis_title': '日期',
        'hovermode': 'x unified',
        'height': 400,
        # 根据主题设置颜色
        'plot_bgcolor': colors['bg_color'],
        'paper_bgcolor': colors['paper_color'],
        'font': dict(color=colors['text_color']),
        'xaxis': dict(
            type="category",  # 使用分类x轴消除空白
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],  # 只显示部分日期
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),  # 只显示年月
            tickangle=45,  # 旋转标签避免重叠
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        'yaxis': dict(
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        # 启用缩放和平移工具
        'dragmode': "zoom",
        # 添加工具栏
        'modebar': dict(
            orientation="h",
            bgcolor=colors['hover_bg'],
            activecolor="#007bff",
            color=colors['text_color']
        ),
        # 半透明悬浮窗
        'hoverlabel': dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['hover_border'],
            font=dict(size=12, color=colors['text_color'])
        ),
        # 图例
        'legend': dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['border_color'],
            font=dict(color=colors['text_color'])
        )
    }
    
    # 根据存在的指标设置y轴标题
    if has_macd:
        layout_updates['yaxis_title'] = 'MACD'
    elif has_rsi:
        layout_updates['yaxis_title'] = 'RSI'
    
    # 添加RSI的y轴设置（如果RSI存在）
    if has_rsi:
        layout_updates['yaxis2'] = dict(
            title='RSI',
            overlaying='y',
            side='right',
            range=[0, 100],
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        )
    
    fig.update_layout(**layout_updates)
    
    # 添加RSI超买超卖线（如果RSI存在）
    if has_rsi:
        fig.add_hline(y=70, line_dash="dash", line_color="red", name="超买线")
        fig.add_hline(y=30, line_dash="dash", line_color="green", name="超卖线")
    
    return fig

# 生成简洁合图（只保留线图，省略K线）
def generate_simple_combined_chart(data, stock_code):
    import plotly.subplots as sp
    
    # 获取颜色方案
    colors = get_color_scheme()
    
    # 创建3行1列的子图
    fig = sp.make_subplots(rows=3, cols=1, 
                          vertical_spacing=0.1, 
                          subplot_titles=(f'{stock_code} 价格走势和交易信号', 
                                         '成交量和均量线', 
                                         '仓位和策略收益率'))
    
    # 提取买卖信号
    buy_signals = data[data.get('signal', 0) == 1]
    add_signals = data[data.get('signal', 0) == 2]
    sell_signals = data[data.get('signal', 0) == -1]
    buyback_signals = data[data.get('signal', 0) == 3]
    stop_loss_signals = data[data.get('signal', 0) == 4]
    
    # 第一行：价格走势和交易信号
    # 添加收盘价
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['close'],
        mode='lines',
        name='收盘价',
        line=dict(color='blue', width=1.5)
    ), row=1, col=1)
    
    # 添加MA25（如果存在）
    if 'MA25' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MA25'],
            mode='lines',
            name='MA25',
            line=dict(color='orange', width=1.5)
        ), row=1, col=1)
    
    # 添加买卖信号标记
    if not buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=buy_signals.index,
            y=buy_signals['close'],
            mode='markers',
            name='买入',
            marker=dict(color='green', size=10, symbol='triangle-up', line=dict(width=2, color='black'))
        ), row=1, col=1)
    
    if not add_signals.empty:
        fig.add_trace(go.Scatter(
            x=add_signals.index,
            y=add_signals['close'],
            mode='markers',
            name='加仓',
            marker=dict(color='blue', size=10, symbol='cross', line=dict(width=2, color='black'))
        ), row=1, col=1)
    
    if not sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=sell_signals.index,
            y=sell_signals['close'],
            mode='markers',
            name='卖出',
            marker=dict(color='red', size=10, symbol='triangle-down', line=dict(width=2, color='black'))
        ), row=1, col=1)
    
    if not buyback_signals.empty:
        fig.add_trace(go.Scatter(
            x=buyback_signals.index,
            y=buyback_signals['close'],
            mode='markers',
            name='买回',
            marker=dict(color='yellow', size=10, symbol='circle', line=dict(width=2, color='black'))
        ), row=1, col=1)
    
    if not stop_loss_signals.empty:
        fig.add_trace(go.Scatter(
            x=stop_loss_signals.index,
            y=stop_loss_signals['close'],
            mode='markers',
            name='止损',
            marker=dict(color='orange', size=10, symbol='x', line=dict(width=2, color='black'))
        ), row=1, col=1)
    
    # 第二行：成交量和均量线
    # 计算均量线
    data['VMA5'] = data['volume'].rolling(window=5).mean()
    data['VMA60'] = data['volume'].rolling(window=60).mean()
    
    # 计算涨跌颜色
    data['color'] = ['red' if close > open else 'green' for close, open in zip(data['close'], data['open'])]
    
    # 添加成交量柱体
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['volume'],
        name='成交量',
        marker=dict(color=data['color'], opacity=0.3)
    ), row=2, col=1)
    
    # 添加VMA5
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['VMA5'],
        mode='lines',
        name='VMA5',
        line=dict(color='blue', width=1.5)
    ), row=2, col=1)
    
    # 添加VMA60
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['VMA60'],
        mode='lines',
        name='VMA60',
        line=dict(color='orange', width=1.5)
    ), row=2, col=1)
    
    # 第三行：仓位和策略收益率
    # 添加仓位
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['position'] * 100,
        mode='lines',
        name='仓位 (%)',
        line=dict(color='green', width=1.5)
    ), row=3, col=1)
    
    # 添加策略收益率
    fig.add_trace(go.Scatter(
        x=data.index,
        y=(data['cumulative_return'] - 1) * 100,
        mode='lines',
        name='策略收益率 (%)',
        line=dict(color='blue', width=1.5)
    ), row=3, col=1)
    
    # 设置图表布局
    fig.update_layout(
        height=900,
        width=1200,
        title=f'{stock_code} 策略回测结果',
        hovermode='x unified',
        # 根据主题设置颜色
        plot_bgcolor=colors['bg_color'],
        paper_bgcolor=colors['paper_color'],
        font=dict(color=colors['text_color']),
        # 统一x轴设置
        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
            tickangle=45,
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        xaxis2=dict(
            type="category",
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
            tickangle=45,
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        xaxis3=dict(
            type="category",
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
            tickangle=45,
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        # 统一y轴设置
        yaxis=dict(
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        yaxis2=dict(
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        yaxis3=dict(
            gridcolor=colors['grid_color'],
            color=colors['text_color']
        ),
        # 简洁的图例
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor=colors['hover_bg'],
            bordercolor=colors['border_color'],
            font=dict(color=colors['text_color'])
        ),
        # 添加图示标注
        annotations=[
            # 价格走势图表标注
            dict(
                x=1.02,
                y=1.0,
                xref='paper',
                yref='paper',
                text='<b>价格走势图示:</b><br>● 蓝色线: 收盘价<br>● 橙色线: MA25<br>● 绿色三角形: 买入<br>● 蓝色叉号: 加仓<br>● 红色三角形: 卖出<br>● 黄色圆形: 买回<br>● 橙色叉号: 止损',
                showarrow=False,
                font=dict(size=10, color=colors['text_color']),
                align='left',
                bgcolor=colors['hover_bg'],
                bordercolor=colors['border_color'],
                borderwidth=1
            ),
            # 成交量图表标注
            dict(
                x=1.02,
                y=0.65,
                xref='paper',
                yref='paper',
                text='<b>成交量图示:</b><br>● 红色柱体: 上涨日成交量<br>● 绿色柱体: 下跌日成交量<br>● 蓝色线: VMA5<br>● 橙色线: VMA60',
                showarrow=False,
                font=dict(size=10, color=colors['text_color']),
                align='left',
                bgcolor=colors['hover_bg'],
                bordercolor=colors['border_color'],
                borderwidth=1
            ),
            # 仓位和收益率图表标注
            dict(
                x=1.02,
                y=0.3,
                xref='paper',
                yref='paper',
                text='<b>仓位和收益率图示:</b><br>● 绿色线: 仓位 (%)<br>● 蓝色线: 策略收益率 (%)',
                showarrow=False,
                font=dict(size=10, color=colors['text_color']),
                align='left',
                bgcolor=colors['hover_bg'],
                bordercolor=colors['border_color'],
                borderwidth=1
            )
        ],
        # 调整右边距以容纳标注
        margin=dict(
            l=50,
            r=300,  # 增加右边距以容纳标注
            b=100,
            t=100,
            pad=4
        ),
        # 启用缩放和平移工具
        dragmode="zoom",
        # 添加工具栏
        modebar=dict(
            orientation="h",
            bgcolor=colors['hover_bg'],
            activecolor="#007bff",
            color=colors['text_color']
        ),
        # 半透明悬浮窗
        hoverlabel=dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['hover_border'],
            font=dict(size=12, color=colors['text_color'])
        )
    )
    
    return fig

# 生成策略与基准对比图表
def generate_strategy_benchmark_chart(data, stock_code):
    fig = go.Figure()
    
    colors_scheme = get_color_scheme()
    template = get_plotly_template(colors_scheme)

    # 策略净值
    fig.add_trace(go.Scatter(
        x=data.index, y=data['cumulative_return'], mode='lines',
        name='策略收益',
        line=dict(width=2, color='#007AFF'),
    ))

    # 基准净值
    if 'cumulative_benchmark' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['cumulative_benchmark'], mode='lines',
            name='基准收益',
            line=dict(width=1.5, color='#AEAEB2', dash='dash'),
        ))
    else:
        data['cumulative_benchmark'] = (1 + data['daily_return']).cumprod()
        fig.add_trace(go.Scatter(
            x=data.index, y=data['cumulative_benchmark'], mode='lines',
            name='基准收益',
            line=dict(width=1.5, color='#AEAEB2', dash='dash'),
        ))

    # 超额收益
    if 'excess_return' not in data.columns:
        data['excess_return'] = data['cumulative_return'] - data['cumulative_benchmark']
    fig.add_trace(go.Scatter(
        x=data.index, y=data['excess_return'], mode='lines',
        name='超额收益',
        line=dict(width=1.5, color='#34C759'),
    ))

    fig.add_hline(y=1, line_dash="dot", line_color=colors_scheme['text_secondary'], opacity=0.4)

    fig.update_layout(**template)
    fig.update_layout(
        title="策略与基准对比",
        height=420,
        hovermode='x unified',
        xaxis=dict(
            type="category",
            tickmode="array",
            tickvals=data.index[::max(1, len(data)//20)],
            ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
            tickangle=0,
        ),
    )
    
    return fig

# 生成雷达图对比不同策略的性能指标
def generate_radar_chart(metrics_list, strategy_names):
    # 定义要展示的指标
    indicators = ['总收益率', '年化收益率', '夏普比率', 'Sortino比率', '信息比率', 'Alpha', '胜率']
    
    # 获取颜色方案
    theme_colors = get_color_scheme()
    
    # 准备数据
    data = []
    colors = ['#007bff', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeead']
    
    for i, (metrics, name) in enumerate(zip(metrics_list, strategy_names)):
        # 归一化数据
        values = [
            metrics.get('total_return', 0),
            metrics.get('annual_return', 0),
            metrics.get('sharpe_ratio', 0) / 3,  # 归一化
            metrics.get('sortino_ratio', 0) / 3,  # 归一化
            metrics.get('information_ratio', 0) / 2,  # 归一化
            metrics.get('alpha', 0) * 5,  # 归一化
            metrics.get('win_rate', 0)
        ]
        
        data.append(go.Scatterpolar(
            r=values,
            theta=indicators,
            fill='toself',
            name=name,
            line=dict(color=colors[i % len(colors)]),
            fillcolor='rgba(0, 123, 255, 0.25)'  # 使用rgba格式
        ))
    
    # 创建图表
    fig = go.Figure(data=data)
    
    # 设置布局
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                color=theme_colors['text_color']
            ),
            angularaxis=dict(
                color=theme_colors['text_color']
            )
        ),
        title="策略性能雷达图",
        height=500,
        # 根据主题设置颜色
        plot_bgcolor=theme_colors['bg_color'],
        paper_bgcolor=theme_colors['paper_color'],
        font=dict(color=theme_colors['text_color']),
        # 图例
        legend=dict(
            bgcolor=theme_colors['hover_bg'],
            bordercolor=theme_colors['border_color'],
            font=dict(color=theme_colors['text_color'])
        )
    )
    
    return fig

# 生成月度收益率图表
def generate_monthly_returns_chart(data):
    # 计算月度收益率
    monthly_data = data.copy()
    monthly_data['month'] = to_period_monthly(monthly_data.index)
    monthly_returns = monthly_data.groupby('month')['strategy_return'].sum().reset_index()
    monthly_returns['month'] = monthly_returns['month'].astype(str)
    
    colors_scheme = get_color_scheme()
    template = get_plotly_template(colors_scheme)

    bar_colors = ['#FF3B30' if x > 0 else '#34C759' for x in monthly_returns['strategy_return']]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_returns['month'], y=monthly_returns['strategy_return'] * 100,
        name='月度收益率', marker=dict(color=bar_colors, opacity=0.85),
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=colors_scheme['text_secondary'], opacity=0.4)

    fig.update_layout(**template)
    fig.update_layout(
        title="月度收益率", height=320,
        xaxis=dict(tickangle=0),
        yaxis=dict(title='收益率 (%)'),
    )
    
    return fig

# 生成交易信号分布饼图
def generate_trade_signals_chart(data):
    # 统计交易信号
    signal_counts = data['signal'].value_counts().to_dict()
    
    # 信号映射
    signal_labels = {
        0: '无信号',
        1: '买入',
        2: '加仓',
        -1: '卖出',
        3: '买回',
        4: '止损'
    }
    
    # 获取颜色方案
    colors = get_color_scheme()
    
    # 准备数据
    labels = []
    values = []
    for signal, count in signal_counts.items():
        if signal in signal_labels:
            labels.append(signal_labels[signal])
            values.append(count)
    
    # 创建图表
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        textinfo='label+percent',
        marker=dict(
            colors=['#E0E0E0', '#4CAF50', '#2196F3', '#F44336', '#FFC107', '#FF9800']
        )
    )])
    
    # 设置布局
    fig.update_layout(
        title="交易信号分布",
        height=300,
        # 根据主题设置颜色
        plot_bgcolor=colors['bg_color'],
        paper_bgcolor=colors['paper_color'],
        font=dict(color=colors['text_color']),
        # 图例
        legend=dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['border_color'],
            font=dict(color=colors['text_color'])
        )
    )
    
    return fig

# 生成3D策略净值对比图表
def generate_3d_strategy_comparison_chart(all_data, stock_code, strategy_names):
    """生成3D的策略净值对比图表"""
    # 获取颜色方案
    colors = get_color_scheme()
    
    fig = go.Figure()
    
    # 准备数据
    for i, strategy_name in enumerate(strategy_names):
        if strategy_name in all_data[stock_code]:
            strategy_data = all_data[stock_code][strategy_name]
            # 计算收益率
            returns = (strategy_data['cumulative_return'] - 1) * 100
            
            # 生成x, y, z数据
            x = list(range(len(returns)))
            y = [i] * len(returns)  # 策略索引作为y轴
            z = returns.values.tolist()
            
            # 生成颜色
            color = ['#007bff', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeead'][i % 6]
            
            # 添加3D柱状图（使用Mesh3d）
            # 限制数据点数量，提高性能
            max_points = 50  # 最多显示50个数据点
            step = max(1, len(x) // max_points)
            
            # 为部分数据点创建柱状图
            for j in range(0, len(x), step):
                # 柱状图的8个顶点（柱体变粗）
                vertices = [
                    [x[j]-0.8, y[j]-0.7, 0],      # 底部左下角
                    [x[j]+0.8, y[j]-0.7, 0],      # 底部右下角
                    [x[j]+0.8, y[j]+0.7, 0],      # 底部右上角
                    [x[j]-0.8, y[j]+0.7, 0],      # 底部左上角
                    [x[j]-0.8, y[j]-0.7, z[j]],   # 顶部左下角
                    [x[j]+0.8, y[j]-0.7, z[j]],   # 顶部右下角
                    [x[j]+0.8, y[j]+0.7, z[j]],   # 顶部右上角
                    [x[j]-0.8, y[j]+0.7, z[j]]    # 顶部左上角
                ]
                
                # 面的索引（每个面由两个三角形组成）
                faces = [
                    # 底部
                    [0, 1, 2],
                    [0, 2, 3],
                    # 顶部
                    [4, 5, 6],
                    [4, 6, 7],
                    # 前面
                    [0, 1, 5],
                    [0, 5, 4],
                    # 右面
                    [1, 2, 6],
                    [1, 6, 5],
                    # 后面
                    [2, 3, 7],
                    [2, 7, 6],
                    # 左面
                    [3, 0, 4],
                    [3, 4, 7]
                ]
                
                # 添加Mesh3d轨迹
                fig.add_trace(go.Mesh3d(
                    x=[v[0] for v in vertices],
                    y=[v[1] for v in vertices],
                    z=[v[2] for v in vertices],
                    i=[f[0] for f in faces],
                    j=[f[1] for f in faces],
                    k=[f[2] for f in faces],
                    name=strategy_name,
                    color=color,
                    opacity=1.0,  # 改为不透明实体
                    hovertext=[f"策略: {strategy_name}<br>月份: {strategy_data.index[j].strftime('%Y-%m')}<br>收益率: {z[j]:.2f}%" for _ in faces],
                    hoverinfo="text"
                ))
    
    # 计算时间轴标注
    step = 1  # 默认为1
    if strategy_names and strategy_names[0] in all_data[stock_code]:
        strategy_data = all_data[stock_code][strategy_names[0]]
        dates = strategy_data.index
        if len(dates) > 0:
            # 计算标注点，每2个月标注一次
            step = max(1, len(dates) // 6)  # 最多标注6个点
            tickvals = list(range(0, len(dates), step))
            ticktext = [date.strftime('%Y-%m') for date in dates[::step]]
        else:
            tickvals = []
            ticktext = []
    else:
        tickvals = []
        ticktext = []
    
    # 设置布局
    fig.update_layout(
        title="3D策略净值对比",
        height=400,  # 缩小其所占空间
        margin=dict(l=20, r=20, t=60, b=20),
        # 根据主题设置颜色
        plot_bgcolor=colors['bg_color'],
        paper_bgcolor=colors['paper_color'],
        font=dict(color=colors['text_color']),
        scene=dict(
            xaxis=dict(
                title="时间",
                color=colors['text_color'],
                gridcolor=colors['grid_color'],
                tickvals=tickvals,
                ticktext=ticktext,
                range=[-0.5, len(tickvals) * step if tickvals else 10]  # 限制x轴范围
            ),
            yaxis=dict(
                title="策略",
                color=colors['text_color'],
                gridcolor=colors['grid_color'],
                tickvals=list(range(len(strategy_names))),
                ticktext=strategy_names,
                range=[-0.5, len(strategy_names) - 0.5]  # 限制y轴范围
            ),
            zaxis=dict(
                title="收益率 (%)",
                color=colors['text_color'],
                gridcolor=colors['grid_color']
            ),
            bgcolor=colors['bg_color'],
            camera=dict(
                eye=dict(x=1.2, y=1.2, z=0.6),  # 设置更合适的初始视角
                up=dict(x=0, y=0, z=1),  # 设置上方向
                center=dict(x=0, y=0, z=0)  # 设置中心点
            ),
            aspectmode="manual",  # 手动设置纵横比
            aspectratio=dict(x=1, y=0.5, z=0.5)  # 调整纵横比，使图表更紧凑
        ),
        # 启用缩放和平移工具，但限制旋转
        dragmode="turntable",  # 限制旋转范围
        # 添加工具栏
        modebar=dict(
            orientation="h",
            bgcolor=colors['hover_bg'],
            activecolor="#007bff",
            color=colors['text_color']
        ),
        # 半透明悬浮窗
        hoverlabel=dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['hover_border'],
            font=dict(size=12, color=colors['text_color'])
        ),
        # 图例
        legend=dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['border_color'],
            font=dict(color=colors['text_color'])
        )
    )
    
    return fig

# 主函数
def main():
    # 设置页面标题和图标
    st.title("股票交易策略回测系统")
    st.markdown("### 专业的股票策略回测与分析工具")
    
    # 侧边栏输入参数
    with st.sidebar:
        st.header("回测参数")
        
        # 支持多个股票代码输入，用逗号分隔
        stock_codes_input = st.text_input(
            "股票代码（多个代码用逗号分隔）", 
            "600519",
            help="例如：600519, 000001, 601318"
        )
        
        # 日期选择
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", pd.to_datetime("2023-01-01"))
        with col2:
            end_date = st.date_input("结束日期", pd.to_datetime("2026-03-22"))
        
        # 初始本金
        initial_capital = st.number_input(
            "初始本金（元）", 
            value=100000, 
            min_value=10000, 
            step=10000,
            help="用于计算实际盈利金额"
        )
        
        # 上传策略文件（支持多个）
        uploaded_files = st.file_uploader(
            "📁 上传策略代码文件（支持多个）", 
            type=["py"], 
            accept_multiple_files=True,
            help="上传包含策略逻辑的Python文件"
        )
        
        # 回测按钮
        st.markdown("---")
        run_backtest = st.button(
            "开始回测",
            use_container_width=True
        )
        
        # 提示信息
        st.markdown("\n**回测完成后将展示：**")
        st.markdown("- 详细的性能指标")
        st.markdown("- 策略与基准对比")
        st.markdown("- 月度收益率分析")
        st.markdown("- 交易信号分布")
        st.markdown("- 技术指标图表")
    
    if run_backtest:
        try:
            # 处理上传的策略文件
            strategies = []
            strategy_functions = []  # 存储每个策略的函数
            if uploaded_files:
                for i, uploaded_file in enumerate(uploaded_files):
                    # 读取上传的策略代码
                    strategy_code = uploaded_file.read().decode('utf-8')
                    # 创建独立的命名空间
                    strategy_namespace = {}
                    # 执行上传的策略代码
                    exec(strategy_code, strategy_namespace)
                    # 检查是否包含必要的函数
                    required_functions = ['calculate_indicators', 'implement_strategy', 'calculate_returns', 'calculate_performance_metrics']
                    if all(func in strategy_namespace for func in required_functions):
                        strategy_functions.append({
                            'name': f"策略 {i+1}",
                            'namespace': strategy_namespace
                        })
                        strategies.append(f"策略 {i+1}")
                        st.success(f"策略 {i+1} 加载成功！")
                    else:
                        st.error(f"策略 {i+1} 缺少必要的函数，请检查代码")
            else:
                # 使用默认策略
                strategies.append("默认策略")
                # 保存默认策略的函数
                strategy_functions.append({
                    'name': "默认策略",
                    'namespace': {
                        'calculate_indicators': calculate_indicators,
                        'implement_strategy': implement_strategy,
                        'calculate_returns': calculate_returns,
                        'calculate_performance_metrics': calculate_performance_metrics
                    }
                })
            
            # 分割股票代码
            stock_codes = [code.strip() for code in stock_codes_input.split(',')]
            
            # 存储所有股票和策略的回测结果
            all_results = []
            all_data = {}
            
            # 对每个股票进行回测
            for stock_code in stock_codes:
                # 获取股票名称
                stock_name = get_stock_name(stock_code)
                stock_display = f"{stock_code} - {stock_name}" if stock_name else stock_code
                
                # 获取数据（将date类型转换为字符串）
                data = get_stock_data(stock_code, str(start_date), str(end_date))
                
                # 检查数据是否为空
                if data.empty:
                    st.warning(f"无法获取 {stock_code} 的数据，可能是因为权限问题或代码不存在")
                    continue
                
                # 对每个策略进行回测
                for strategy_info in strategy_functions:
                    strategy_name = strategy_info['name']
                    strategy_namespace = strategy_info['namespace']
                    
                    st.subheader(f"{stock_display} - {strategy_name} 回测结果")
                    
                    # 复制数据以避免策略间相互影响
                    strategy_data = data.copy()
                    
                    # 获取策略的函数
                    calc_indicators = strategy_namespace['calculate_indicators']
                    impl_strategy = strategy_namespace['implement_strategy']
                    calc_returns = strategy_namespace['calculate_returns']
                    calc_metrics = strategy_namespace['calculate_performance_metrics']
                    
                    # 获取基准数据
                    benchmark_data = get_benchmark_data(str(start_date), str(end_date))
                    
                    # 计算技术指标
                    strategy_data = calc_indicators(strategy_data)
                    
                    # 实现策略
                    strategy_data = impl_strategy(strategy_data)
                    
                    # 计算收益率，根据函数参数数量决定是否传入基准数据
                    import inspect
                    sig = inspect.signature(calc_returns)
                    if len(sig.parameters) >= 2:
                        # 函数接受至少两个参数，传入基准数据
                        strategy_data = calc_returns(strategy_data, benchmark_data)
                    else:
                        # 函数只接受一个参数，只传入数据
                        strategy_data = calc_returns(strategy_data)
                    
                    # 计算性能指标，根据函数参数数量决定传递参数
                    import inspect
                    sig = inspect.signature(calc_metrics)
                    num_params = len(sig.parameters)
                    
                    try:
                        if num_params >= 3:
                            # 函数接受至少三个参数，传入全部参数
                            metrics = calc_metrics(strategy_data, initial_capital, benchmark_data)
                        elif num_params >= 2:
                            # 函数接受至少两个参数，传入数据和初始本金
                            metrics = calc_metrics(strategy_data, initial_capital)
                        else:
                            # 函数只接受一个参数，只传入数据
                            metrics = calc_metrics(strategy_data)
                    except TypeError:
                        # 如果失败，尝试不同的参数组合
                        try:
                            metrics = calc_metrics(strategy_data)
                        except Exception as e:
                            st.error(f"计算性能指标时出错: {str(e)}")
                            continue
                        # 手动计算盈利相关指标
                        total_return = metrics['total_return']
                        total_profit = initial_capital * total_return
                        
                        # 计算交易次数和胜率
                        buy_signals = strategy_data[strategy_data['signal'] == 1]
                        sell_signals = strategy_data[strategy_data['signal'] == -1]
                        buyback_signals = strategy_data[strategy_data['signal'] == 3]
                        stop_loss_signals = strategy_data[strategy_data['signal'] == 4]
                        
                        total_trades = len(buy_signals) + len(buyback_signals)
                        
                        # 计算胜率
                        winning_trades = 0
                        if total_trades > 0:
                            # 简单胜率计算：卖出时价格高于买入价格
                            for i in range(len(strategy_data)):
                                if strategy_data.iloc[i]['signal'] in [-1, 4]:  # 卖出或止损
                                    # 找到最近的买入信号
                                    for j in range(i-1, -1, -1):
                                        if strategy_data.iloc[j]['signal'] in [1, 3]:  # 买入或买回
                                            buy_price = strategy_data.iloc[j]['close']
                                            sell_price = strategy_data.iloc[i]['close']
                                            if sell_price > buy_price:
                                                winning_trades += 1
                                            break
                        
                        win_rate = winning_trades / total_trades if total_trades > 0 else 0
                        
                        # 计算手续费（万一）
                        trade_value = initial_capital * total_trades * 2  # 买入和卖出各一次
                        commission = trade_value * 0.0001
                        net_profit = total_profit - commission
                        
                        # 计算相对收益率（相对于基准）
                        benchmark_total_return = 0
                        relative_return = 0
                        if benchmark_data is not None and not benchmark_data.empty:
                            aligned_benchmark = benchmark_data.reindex(strategy_data.index)
                            if not aligned_benchmark.empty:
                                benchmark_total_return = aligned_benchmark['cumulative_benchmark'].iloc[-1] - 1
                                relative_return = total_return - benchmark_total_return
                        else:
                            benchmark_total_return = strategy_data['close'].iloc[-1] / strategy_data['close'].iloc[0] - 1
                            relative_return = total_return - benchmark_total_return
                        
                        # 计算最大回撤比
                        max_drawdown_ratio = abs(metrics['max_drawdown']) / (total_return + 1) if total_return > 0 else float('inf')
                        
                        # 更新metrics字典
                        metrics.update({
                            'total_profit': total_profit,
                            'net_profit': net_profit,
                            'commission': commission,
                            'win_rate': win_rate,
                            'total_trades': total_trades,
                            'benchmark_return': benchmark_total_return,
                            'relative_return': relative_return,
                            'max_drawdown_ratio': max_drawdown_ratio
                        })
                    
                    # 保存结果
                    all_results.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'strategy': strategy_name,
                        'metrics': metrics,
                        'data': strategy_data
                    })
                    
                    # 存储数据
                    if stock_code not in all_data:
                        all_data[stock_code] = {}
                    all_data[stock_code][strategy_name] = strategy_data
                    
                    # 显示图表
                    st.markdown("### 策略分析")
                    
                    # 只有单个策略时才显示策略与基准对比图表
                    if len(strategies) == 1:
                        # 策略与基准对比图表（只显示策略收益、基准收益和超额收益）
                        benchmark_fig = generate_strategy_benchmark_chart(strategy_data, stock_code)
                        st.plotly_chart(benchmark_fig, use_container_width=True, key=f"benchmark_{stock_code}_{strategy_name}")
                
                # 横向排列策略
                if len(strategies) > 1:
                    st.subheader(f"{stock_display} 策略对比")
                    
                    # 横向排列策略，放在页面两侧
                    cols = st.columns(2, gap="large")
                    for i, (strategy_name, col) in enumerate(zip(strategies, cols)):
                        with col:
                            # 添加策略标题
                            st.subheader(f"{strategy_name}")
                            
                            # 获取该策略的数据和指标
                            strategy_data = all_data[stock_code][strategy_name]
                            # 找到对应的结果
                            for result in all_results:
                                if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                    metrics = result['metrics']
                                    break
                            
                            # 创建丰富的结果表格
                            results_df = pd.DataFrame({
                                '指标': ['总收益率', '年化收益率', '最大回撤', '夏普比率', 'Sortino比率', 'Alpha', 'Beta', '信息比率', '基准收益', '超额收益', '胜率', '总交易次数'],
                                '数值': [
                                    f"{metrics.get('total_return', 0):.2%}",
                                    f"{metrics.get('annual_return', 0):.2%}",
                                    f"{metrics.get('max_drawdown', 0):.2%}",
                                    f"{metrics.get('sharpe_ratio', 0):.2f}",
                                    f"{metrics.get('sortino_ratio', 0):.2f}",
                                    f"{metrics.get('alpha', 0):.2f}",
                                    f"{metrics.get('beta', 1):.2f}",
                                    f"{metrics.get('information_ratio', 0):.2f}",
                                    f"{metrics.get('benchmark_return', 0):.2%}",
                                    f"{metrics.get('relative_return', 0):.2%}",
                                    f"{metrics.get('win_rate', 0):.2%}",
                                    f"{metrics.get('total_trades', 0)}"
                                ]
                            })
                            
                            st.table(results_df)
                            
                            # 生成策略与基准对比图表（只显示策略收益、基准收益和超额收益）
                            benchmark_fig = generate_strategy_benchmark_chart(strategy_data, stock_code)
                            st.plotly_chart(benchmark_fig, use_container_width=True, key=f"benchmark_compare_{stock_code}_{strategy_name}")
                            
                            # 生成月度收益率分析图
                            monthly_fig = generate_monthly_returns_chart(strategy_data)
                            st.plotly_chart(monthly_fig, use_container_width=True, key=f"monthly_returns_{stock_code}_{strategy_name}")
                    
                    # 策略净值对比
                    st.subheader("策略净值对比")
                    nv_colors = get_color_scheme()
                    nv_tpl = get_plotly_template(nv_colors)
                    net_value_compare_fig = go.Figure()
                    for i, strategy_name in enumerate(strategies):
                        if strategy_name in all_data[stock_code]:
                            strategy_data = all_data[stock_code][strategy_name]
                            net_value_compare_fig.add_trace(go.Scatter(
                                x=strategy_data.index, y=strategy_data['cumulative_return'],
                                mode='lines', name=strategy_name,
                                line=dict(width=2, color=nv_tpl['colorway'][i % len(nv_tpl['colorway'])]),
                            ))
                    if net_value_compare_fig.data:
                        net_value_compare_fig.add_hline(y=1, line_dash="dot",
                            line_color=nv_colors['text_secondary'], opacity=0.4)
                        net_value_compare_fig.update_layout(**nv_tpl)
                        net_value_compare_fig.update_layout(
                            title=f"{stock_display} 策略净值对比", height=440,
                            hovermode='x unified',
                            xaxis=dict(type="category",
                                tickmode="array",
                                tickvals=strategy_data.index[::max(1, len(strategy_data)//30)],
                                ticktext=strategy_data.index[::max(1, len(strategy_data)//30)].strftime('%Y-%m'),
                                tickangle=0),
                        )
                        st.plotly_chart(net_value_compare_fig, use_container_width=True, key=f"net_value_compare_{stock_code}")

                    # 策略回撤对比
                    st.subheader("策略回撤对比")
                    dd2_colors = get_color_scheme()
                    dd2_tpl = get_plotly_template(dd2_colors)
                    drawdown_compare_fig = go.Figure()
                    for i, strategy_name in enumerate(strategies):
                        if strategy_name in all_data[stock_code]:
                            strategy_data = all_data[stock_code][strategy_name]
                            drawdown_compare_fig.add_trace(go.Scatter(
                                x=strategy_data.index, y=strategy_data['drawdown'] * 100,
                                mode='lines', name=strategy_name,
                                line=dict(width=2, color=dd2_tpl['colorway'][i % len(dd2_tpl['colorway'])]),
                            ))
                    if drawdown_compare_fig.data:
                        drawdown_compare_fig.update_layout(**dd2_tpl)
                        drawdown_compare_fig.update_layout(
                            title=f"{stock_display} 策略回撤对比", height=440,
                            hovermode='x unified',
                            xaxis=dict(type="category",
                                tickmode="array",
                                tickvals=strategy_data.index[::max(1, len(strategy_data)//30)],
                                ticktext=strategy_data.index[::max(1, len(strategy_data)//30)].strftime('%Y-%m'),
                                tickangle=0),
                        )
                        st.plotly_chart(drawdown_compare_fig, use_container_width=True, key=f"drawdown_compare_{stock_code}")
                    
                    # 策略性能指标雷达图对比
                    st.subheader("策略性能指标雷达图对比")
                    radar_colors_s = get_color_scheme()
                    apple_colors = ['#007AFF', '#FF3B30', '#34C759', '#FF9500', '#5AC8FA', '#AF52DE']
                    radar_compare_fig = go.Figure()
                    for i, strategy_name in enumerate(strategies):
                        if strategy_name in all_data[stock_code]:
                            for result in all_results:
                                if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                    metrics = result['metrics']
                                    break
                            normalized_metrics = {
                                '总收益率': min(metrics['total_return'] * 100, 100),
                                '年化收益率': min(metrics['annual_return'] * 100, 100),
                                '夏普比率': min(metrics['sharpe_ratio'], 5) * 20,
                                '胜率': min(metrics['win_rate'] * 100, 100),
                                '最大回撤': min(abs(metrics['max_drawdown']) * 100, 100),
                                '交易频率': min(metrics['total_trades'] / (len(strategy_data)/252) * 12, 120) * 0.83
                            }
                            c = apple_colors[i % len(apple_colors)]
                            r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
                            radar_compare_fig.add_trace(go.Scatterpolar(
                                r=list(normalized_metrics.values()),
                                theta=list(normalized_metrics.keys()),
                                fill='toself',
                                name=strategy_name,
                                line=dict(width=2, color=c),
                                fillcolor=f'rgba({r}, {g}, {b}, 0.15)',
                            ))
                    if radar_compare_fig.data:
                        radar_compare_fig.update_layout(
                            polar=dict(
                                radialaxis=dict(visible=True, range=[0, 100],
                                    tickfont=dict(size=11), gridcolor=radar_colors_s['grid_color'],
                                    color=radar_colors_s['text_secondary']),
                                angularaxis=dict(tickfont=dict(size=12),
                                    color=radar_colors_s['text_color'], gridcolor=radar_colors_s['grid_color']),
                                bgcolor='rgba(0,0,0,0)',
                            ),
                            title=f"{stock_display} 策略性能指标雷达图对比",
                            height=480,
                            paper_bgcolor=radar_colors_s['bg_color'],
                            font=dict(color=radar_colors_s['text_color'], size=13,
                                family='-apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif'),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                                font=dict(size=12)),
                        )
                        st.plotly_chart(radar_compare_fig, use_container_width=True, key=f"radar_compare_{stock_code}")
                        
                        # 添加雷达图下载链接
                        radar_compare_fig.write_html(f"radar_compare_{stock_code}.html")
                        with open(f"radar_compare_{stock_code}.html", "rb") as f:
                            radar_html = f.read()
                        b64 = base64.b64encode(radar_html).decode()
                        href = f'<a href="data:text/html;base64,{b64}" download="radar_compare_{stock_code}.html">📥 下载雷达图对比</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    # 3D策略净值对比
                    st.subheader("3D 策略净值对比")
                    try:
                        if len(strategies) > 1:
                            fig_3d = generate_3d_strategy_comparison_chart(all_data, stock_code, strategies)
                            if fig_3d.data:
                                st.plotly_chart(fig_3d, use_container_width=True, key=f"3d_strategy_compare_{stock_code}")
                    except Exception as e:
                        st.error(f"生成3D图表时出错: {str(e)}")
                    
                    # 添加策略对比下载功能
                    st.subheader("对比图表下载")
                    
                    # 下载净值对比图
                    if net_value_compare_fig.data:
                        # HTML格式下载
                        net_value_compare_fig.write_html(f"net_value_compare_{stock_code}.html")
                        with open(f"net_value_compare_{stock_code}.html", "rb") as f:
                            net_value_html = f.read()
                        b64 = base64.b64encode(net_value_html).decode()
                        href = f'<a href="data:text/html;base64,{b64}" download="net_value_compare_{stock_code}.html">📥 下载净值对比图 (HTML)</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    # 下载回撤对比图
                    if drawdown_compare_fig.data:
                        # HTML格式下载
                        drawdown_compare_fig.write_html(f"drawdown_compare_{stock_code}.html")
                        with open(f"drawdown_compare_{stock_code}.html", "rb") as f:
                            drawdown_html = f.read()
                        b64 = base64.b64encode(drawdown_html).decode()
                        href = f'<a href="data:text/html;base64,{b64}" download="drawdown_compare_{stock_code}.html">📥 下载回撤对比图 (HTML)</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    # 下载雷达图对比
                    if radar_compare_fig.data:
                        # HTML格式下载
                        radar_compare_fig.write_html(f"radar_compare_{stock_code}.html")
                        with open(f"radar_compare_{stock_code}.html", "rb") as f:
                            radar_html = f.read()
                        b64 = base64.b64encode(radar_html).decode()
                        href = f'<a href="data:text/html;base64,{b64}" download="radar_compare_{stock_code}.html">📥 下载雷达图对比 (HTML)</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    # 添加综合对比图像
                    st.subheader("综合对比图像")
                    if len(strategies) > 1:
                        # 创建综合对比图像
                        import matplotlib.pyplot as plt

                        # 创建一个大的画布
                        mp_colors = ['#007AFF', '#FF3B30', '#34C759', '#FF9500', '#5AC8FA', '#AF52DE']
                        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
                        
                        # 第一个子图：净值对比
                        ax1 = axes[0, 0]
                        for i, strategy_name in enumerate(strategies):
                            if strategy_name in all_data[stock_code]:
                                strategy_data = all_data[stock_code][strategy_name]
                                ax1.plot(strategy_data.index, strategy_data['cumulative_return'], 
                                         label=strategy_name, color=mp_colors[i % len(mp_colors)], linewidth=2)
                        ax1.axhline(y=1, linestyle='--', color='gray')
                        ax1.set_title('策略净值对比')
                        ax1.set_xlabel('日期')
                        ax1.set_ylabel('净值')
                        ax1.legend()
                        ax1.grid(True)
                        ax1.tick_params(axis='x', rotation=45)

                        # 第二个子图：回撤对比
                        ax2 = axes[0, 1]
                        for i, strategy_name in enumerate(strategies):
                            if strategy_name in all_data[stock_code]:
                                strategy_data = all_data[stock_code][strategy_name]
                                ax2.plot(strategy_data.index, strategy_data['drawdown'] * 100,
                                         label=strategy_name, color=mp_colors[i % len(mp_colors)], linewidth=2)
                        ax2.set_title('策略回撤对比')
                        ax2.set_xlabel('日期')
                        ax2.set_ylabel('回撤 (%)')
                        ax2.legend()
                        ax2.grid(True)
                        ax2.tick_params(axis='x', rotation=45)
                        
                        # 第三个子图：性能指标对比
                        ax3 = axes[1, 0]
                        metrics_data = []
                        metrics_labels = ['总收益率', '年化收益率', '夏普比率', '胜率']
                        for strategy_name in strategies:
                            if strategy_name in all_data[stock_code]:
                                for result in all_results:
                                    if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                        metrics = result['metrics']
                                        break
                                metrics_data.append([
                                    metrics['total_return'] * 100,
                                    metrics['annual_return'] * 100,
                                    metrics['sharpe_ratio'],
                                    metrics['win_rate'] * 100
                                ])
                        
                        # 绘制柱状图
                        x = range(len(metrics_labels))
                        width = 0.35
                        for i, (strategy_name, metric_values) in enumerate(zip(strategies, metrics_data)):
                            offset = i * width / (len(strategies) - 1) if len(strategies) > 1 else 0
                            ax3.bar([xi - width/2 + offset for xi in x], metric_values, 
                                    width=width/len(strategies), label=strategy_name, 
                                    color=mp_colors[i % len(mp_colors)])
                        ax3.set_title('性能指标对比')
                        ax3.set_xticks(x)
                        ax3.set_xticklabels(metrics_labels)
                        ax3.set_ylabel('数值')
                        ax3.legend()
                        ax3.grid(True)
                        
                        # 第四个子图：交易频率对比
                        ax4 = axes[1, 1]
                        trade_counts = []
                        for strategy_name in strategies:
                            if strategy_name in all_data[stock_code]:
                                for result in all_results:
                                    if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                        metrics = result['metrics']
                                        break
                                trade_counts.append(metrics['total_trades'])
                        
                        ax4.bar(strategies, trade_counts, color=[mp_colors[i % len(mp_colors)] for i in range(len(strategies))])
                        ax4.set_title('交易频率对比')
                        ax4.set_ylabel('交易次数')
                        ax4.grid(True)
                        
                        # 调整布局
                        plt.tight_layout()
                        
                        # 保存为PNG
                        buf = io.BytesIO()
                        plt.savefig(buf, format='png')
                        buf.seek(0)
                        
                        # 提供PNG下载链接
                        b64 = base64.b64encode(buf.read()).decode()
                        href = f'<a href="data:image/png;base64,{b64}" download="comprehensive_comparison_{stock_code}.png">📥 下载综合对比图像 (PNG)</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        # 显示图像
                        st.pyplot(fig)
                    
                    # 添加综合评估
                    st.subheader("策略综合评估")
                    if strategies:
                        # 计算每个策略的综合得分
                        strategy_scores = {}
                        for strategy_name in strategies:
                            if strategy_name in all_data[stock_code]:
                                # 找到对应的结果
                                for result in all_results:
                                    if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                        metrics = result['metrics']
                                        break
                                # 计算综合得分（权重可调整）
                                score = (
                                    metrics['total_return'] * 30 +  # 总收益率权重30%
                                    metrics['annual_return'] * 25 +  # 年化收益率权重25%
                                    (1 + metrics['max_drawdown']) * 20 +  # 最大回撤权重20%（注意是负的，所以用1+）
                                    metrics['sharpe_ratio'] * 15 +  # 夏普比率权重15%
                                    metrics['win_rate'] * 10  # 胜率权重10%
                                )
                                strategy_scores[strategy_name] = score
                        
                        # 排序策略
                        sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
                        
                        # 生成综合评估
                        st.write("### 综合评估结论")
                        if sorted_strategies:
                            best_strategy = sorted_strategies[0][0]
                            st.write(f"**最佳策略**: {best_strategy} 🎉")
                            
                            # 分析每个策略的优缺点
                            st.write("\n**策略表现分析**:")
                            for strategy_name, score in sorted_strategies:
                                for result in all_results:
                                    if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                        metrics = result['metrics']
                                        break
                                
                                strengths = []
                                weaknesses = []
                                
                                # 分析优势
                                if metrics['total_return'] > 0.1:
                                    strengths.append(f"总收益率较高 ({metrics['total_return']:.2%}) 📈")
                                if metrics['annual_return'] > 0.08:
                                    strengths.append(f"年化收益率较好 ({metrics['annual_return']:.2%}) 📅")
                                if metrics['sharpe_ratio'] > 1:
                                    strengths.append(f"风险调整收益优秀 (夏普比率: {metrics['sharpe_ratio']:.2f}) ⚖️")
                                if metrics['win_rate'] > 0.5:
                                    strengths.append(f"胜率较高 ({metrics['win_rate']:.2%}) ✅")
                                if abs(metrics['max_drawdown']) < 0.2:
                                    strengths.append(f"回撤控制良好 ({metrics['max_drawdown']:.2%}) 🛡️")
                                
                                # 分析劣势
                                if metrics['total_return'] < 0:
                                    weaknesses.append(f"总收益率为负 ({metrics['total_return']:.2%}) 📉")
                                if metrics['annual_return'] < 0.05:
                                    weaknesses.append(f"年化收益率较低 ({metrics['annual_return']:.2%}) ⏰")
                                if metrics['sharpe_ratio'] < 0.5:
                                    weaknesses.append(f"风险调整收益一般 (夏普比率: {metrics['sharpe_ratio']:.2f}) ⚠️")
                                if metrics['win_rate'] < 0.4:
                                    weaknesses.append(f"胜率较低 ({metrics['win_rate']:.2%}) ❌")
                                if abs(metrics['max_drawdown']) > 0.3:
                                    weaknesses.append(f"回撤较大 ({metrics['max_drawdown']:.2%}) 💥")
                                
                                # 使用卡片式布局显示每个策略的分析
                                with st.expander(f"{strategy_name} (得分: {score:.2f})"):
                                    if strengths:
                                        st.write("**✨ 优势**:")
                                        for strength in strengths:
                                            st.write(f"- {strength}")
                                    if weaknesses:
                                        st.write("**劣势**:")
                                        for weakness in weaknesses:
                                            st.write(f"- {weakness}")
                        
                        # 添加买卖点胜率分析
                        st.write("\n### 买卖点胜率分析")
                        trade_stats = {}
                        for strategy_name in strategies:
                            if strategy_name in all_data[stock_code]:
                                strategy_data = all_data[stock_code][strategy_name]
                                stats = calculate_trade_win_rate(strategy_data)
                                trade_stats[strategy_name] = stats
                        
                        if trade_stats:
                            # 创建胜率对比表格
                            win_rate_data = []
                            for strategy_name, stats in trade_stats.items():
                                win_rate_data.append({
                                    '策略名称': strategy_name,
                                    '总交易次数': stats['total_trades'],
                                    '盈利次数': stats['winning_trades'],
                                    '亏损次数': stats['losing_trades'],
                                    '胜率': f"{stats['win_rate']:.2%}",
                                    '平均盈利': f"{stats['avg_profit']:.2%}",
                                    '平均亏损': f"{stats['avg_loss']:.2%}",
                                    '利润因子': f"{stats['profit_factor']:.2f}" if stats['profit_factor'] != float('inf') else '∞',
                                    '最大盈利': f"{stats['max_win']:.2%}",
                                    '最大亏损': f"{stats['max_loss']:.2%}"
                                })
                            
                            win_rate_df = pd.DataFrame(win_rate_data)
                            st.dataframe(win_rate_df, use_container_width=True)
                            
                            # 分析买卖点质量
                            st.write("\n**买卖点质量分析**:")
                            for strategy_name, stats in trade_stats.items():
                                with st.expander(f"{strategy_name} 买卖点详情"):
                                    if stats['total_trades'] == 0:
                                        st.write("该策略没有产生任何交易信号")
                                    else:
                                        st.write(f"**交易概况**: 共 {stats['total_trades']} 次交易")
                                        st.write(f"**胜率**: {stats['win_rate']:.2%} ({stats['winning_trades']} 次盈利 / {stats['losing_trades']} 次亏损)")
                                        
                                        if stats['win_rate'] >= 0.6:
                                            st.write("✅ **胜率表现优秀** - 超过60%的交易是盈利的")
                                        elif stats['win_rate'] >= 0.5:
                                            st.write("**胜率表现一般** - 接近50%，需要优化")
                                        else:
                                            st.write("❌ **胜率表现较差** - 低于50%，建议改进策略")
                                        
                                        if stats['profit_factor'] >= 2:
                                            st.write("✅ **利润因子优秀** - 盈利是亏损的2倍以上")
                                        elif stats['profit_factor'] >= 1.5:
                                            st.write("**利润因子一般** - 盈利略高于亏损")
                                        else:
                                            st.write("❌ **利润因子较差** - 盈利不足以覆盖亏损")
                                        
                                        st.write(f"\n**单次交易分析**:")
                                        st.write(f"- 平均盈利: {stats['avg_profit']:.2%}")
                                        st.write(f"- 平均亏损: {stats['avg_loss']:.2%}")
                                        st.write(f"- 最大盈利: {stats['max_win']:.2%}")
                                        st.write(f"- 最大亏损: {stats['max_loss']:.2%}")
                            
                            # 买卖点改进建议
                            st.write("\n**买卖点优化建议**:")
                            suggestions = []
                            for strategy_name, stats in trade_stats.items():
                                if stats['total_trades'] > 0:
                                    if stats['win_rate'] < 0.5:
                                        suggestions.append(f"• **{strategy_name}**: 胜率较低，建议优化入场时机筛选条件")
                                    if stats['avg_loss'] > stats['avg_profit']:
                                        suggestions.append(f"• **{strategy_name}**: 平均亏损大于平均盈利，建议设置止损")
                                    if stats['total_trades'] < 5:
                                        suggestions.append(f"• **{strategy_name}**: 交易次数过少，建议放宽信号条件")
                            
                            if suggestions:
                                for suggestion in suggestions:
                                    st.write(suggestion)
                            else:
                                st.write("✓ 所有策略的买卖点表现良好！")
                        else:
                            st.write("暂无交易数据可分析")
                        
                        # 添加投资建议，使用emoji增强视觉效果
                        st.write("\n**投资建议**:")
                        if sorted_strategies:
                            best_strategy = sorted_strategies[0][0]
                            worst_strategy = sorted_strategies[-1][0]
                            
                            # 找到最佳策略和最差策略的指标
                            for result in all_results:
                                if result['stock_code'] == stock_code and result['strategy'] == best_strategy:
                                    best_metrics = result['metrics']
                                if result['stock_code'] == stock_code and result['strategy'] == worst_strategy:
                                    worst_metrics = result['metrics']
                            
                            st.write(f"1. **最佳策略推荐**: {best_strategy}")
                            st.write(f"   - **推荐理由**: 该策略在综合评估中得分最高，表现最为出色")
                            st.write(f"   - **关键优势**: 总收益率 {best_metrics['total_return']:.2%}，年化收益率 {best_metrics['annual_return']:.2%}，夏普比率 {best_metrics['sharpe_ratio']:.2f}")
                            st.write(f"   - **风险特性**: 最大回撤 {best_metrics['max_drawdown']:.2%}，胜率 {best_metrics['win_rate']:.2%}")
                            
                            if len(sorted_strategies) > 1:
                                st.write(f"2. **需要改进的策略**: {worst_strategy}")
                                st.write(f"   - **主要问题**: 综合得分较低，表现相对较弱")
                                st.write(f"   - **需要关注**: 总收益率 {worst_metrics['total_return']:.2%}，年化收益率 {worst_metrics['annual_return']:.2%}，夏普比率 {worst_metrics['sharpe_ratio']:.2f}")
                                st.write(f"   - **风险特性**: 最大回撤 {worst_metrics['max_drawdown']:.2%}，胜率 {worst_metrics['win_rate']:.2%}")
                        
                        st.write("3. **风险控制建议**:")
                        st.write("   - 根据个人风险承受能力选择合适的策略")
                        st.write("   - 对于风险偏好较低的投资者，建议选择回撤较小的策略")
                        st.write("   - 对于风险偏好较高的投资者，可以考虑收益潜力更大的策略")
                        
                        st.write("4. **策略管理建议**:")
                        st.write("   - 定期评估策略表现，至少每季度进行一次全面分析")
                        st.write("   - 根据市场环境变化调整策略参数")
                        st.write("   - 关注宏观经济指标和行业发展趋势")
                        
                        st.write("5. **投资组合构建**:")
                        st.write("   - 可以考虑多种策略组合，分散投资风险")
                        st.write("   - 结合不同风格的策略，如趋势跟踪和均值回归")
                        st.write("   - 根据市场周期调整不同策略的权重")
                        
                        st.write("6. **执行建议**:")
                        st.write("   - 严格按照策略信号执行交易，避免情绪干扰")
                        st.write("   - 控制交易频率，避免过度交易")
                        st.write("   - 合理设置止损和止盈点位")
                else:
                    # 只有一个策略时的显示
                    for strategy_name in strategies:
                        # 获取该策略的数据和指标
                        strategy_data = all_data[stock_code][strategy_name]
                        # 找到对应的结果
                        for result in all_results:
                            if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                metrics = result['metrics']
                                break
                        
                        # 创建结果表格
                        results_df = pd.DataFrame({
                            '指标': ['股票代码', '策略', '总收益率', '年化收益率', '最大回撤', '夏普比率', 
                                    '总盈利（元）', '净利润（元）', '手续费（元）', '胜率', '总交易次数',
                                    '相对收益率', '最大回撤比'],
                            '数值': [
                                stock_display,
                                strategy_name,
                                f"{metrics['total_return']:.2%}",
                                f"{metrics['annual_return']:.2%}",
                                f"{metrics['max_drawdown']:.2%}",
                                f"{metrics['sharpe_ratio']:.2f}",
                                f"{metrics['total_profit']:.2f}",
                                f"{metrics['net_profit']:.2f}",
                                f"{metrics['commission']:.2f}",
                                f"{metrics['win_rate']:.2%}",
                                f"{metrics['total_trades']}",
                                f"{metrics['relative_return']:.2%}",
                                f"{metrics['max_drawdown_ratio']:.2f}"
                            ]
                        })
                        
                        st.table(results_df)
                        
                        # 显示图表
                        # K线图
                        st.subheader(f"{strategy_name} - 价格走势和交易信号")
                        
                        # 添加均线显示控制按钮
                        with st.sidebar:
                            st.subheader("均线显示控制")
                            show_ma5 = st.checkbox("显示MA5", key=f"ma5_{stock_code}_{strategy_name}")
                            show_ma10 = st.checkbox("显示MA10", key=f"ma10_{stock_code}_{strategy_name}")
                            show_ma50 = st.checkbox("显示MA50", key=f"ma50_{stock_code}_{strategy_name}")
                            show_ma100 = st.checkbox("显示MA100", key=f"ma100_{stock_code}_{strategy_name}")
                        
                        # 固定使用日K
                        time_frame = "day"
                        kline_fig = generate_kline_chart(strategy_data, f"{stock_display} - {strategy_name}", time_frame, 
                                                      show_ma5=show_ma5, show_ma10=show_ma10, 
                                                      show_ma50=show_ma50, show_ma100=show_ma100)
                        st.plotly_chart(kline_fig, use_container_width=True, key=f"kline_{stock_code}_{strategy_name}")
                        
                        # 成交量和均量线图表
                        st.subheader(f"{strategy_name} - 成交量和均量线")
                        volume_fig = generate_volume_chart(strategy_data, time_frame)
                        st.plotly_chart(volume_fig, use_container_width=True, key=f"volume_{stock_code}_{strategy_name}")
                        
                        # 仓位和策略收益率图表
                        st.subheader(f"{strategy_name} - 仓位和策略收益率")
                        position_fig = generate_position_chart(strategy_data, time_frame)
                        st.plotly_chart(position_fig, use_container_width=True, key=f"position_{stock_code}_{strategy_name}")
                        

                        # 回撤曲线
                        st.subheader(f"{strategy_name} - 回撤曲线")
                        dd_colors = get_color_scheme()
                        dd_tpl = get_plotly_template(dd_colors)
                        drawdown_fig = go.Figure()
                        drawdown_fig.add_trace(go.Scatter(
                            x=strategy_data.index,
                            y=strategy_data['drawdown'] * 100,
                            mode='lines',
                            name='回撤',
                            line=dict(color='#FF3B30', width=1.5),
                            fill='tozeroy',
                            fillcolor='rgba(255,59,48,0.08)'
                        ))
                        drawdown_fig.update_layout(**dd_tpl)
                        drawdown_fig.update_layout(
                            title=f"{strategy_name} - 策略回撤情况", height=380,
                            hovermode='x unified',
                            xaxis=dict(type="category",
                                tickmode="array",
                                tickvals=strategy_data.index[::max(1, len(strategy_data)//20)],
                                ticktext=strategy_data.index[::max(1, len(strategy_data)//20)].strftime('%Y-%m'),
                                tickangle=0),
                            yaxis=dict(tickformat=".1f%%", title='回撤 (%)'),
                        )
                        st.plotly_chart(drawdown_fig, use_container_width=True, key=f"drawdown_{stock_code}_{strategy_name}")
                        
                        # 性能指标雷达图
                        st.subheader(f"{strategy_name} - 性能指标雷达图")
                        normalized_metrics = {
                            '总收益率': min(metrics['total_return'] * 100, 100),
                            '年化收益率': min(metrics['annual_return'] * 100, 100),
                            '夏普比率': min(metrics['sharpe_ratio'], 5),
                            '胜率': min(metrics['win_rate'] * 100, 100),
                            '最大回撤': min(abs(metrics['max_drawdown']) * 100, 100),
                            '交易频率': min(metrics['total_trades'] / (len(strategy_data)/252) * 12, 120)
                        }
                        radar_colors = get_color_scheme()
                        radar_fig = go.Figure()
                        radar_fig.add_trace(go.Scatterpolar(
                            r=list(normalized_metrics.values()),
                            theta=list(normalized_metrics.keys()),
                            fill='toself',
                            name=strategy_name,
                            fillcolor='rgba(0,122,255,0.12)',
                            line=dict(color='#007AFF', width=2),
                        ))
                        radar_fig.update_layout(
                            polar=dict(
                                radialaxis=dict(visible=True, range=[0, 100],
                                    gridcolor=radar_colors['grid_color'],
                                    color=radar_colors['text_secondary']),
                                angularaxis=dict(color=radar_colors['text_color'], gridcolor=radar_colors['grid_color']),
                                bgcolor='rgba(0,0,0,0)',
                            ),
                            title=f"{strategy_name} - 策略性能指标雷达图",
                            height=420,
                            paper_bgcolor=radar_colors['bg_color'],
                            font=dict(color=radar_colors['text_color'], size=13,
                                family='-apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif'),
                        )
                        st.plotly_chart(radar_fig, use_container_width=True, key=f"radar_{stock_code}_{strategy_name}")
                        
                        # 月度收益率
                        st.subheader(f"{strategy_name} - 月度收益率")
                        monthly_data = resample_monthly(strategy_data, {'strategy_return': 'sum'})
                        monthly_data['month'] = monthly_data.index.strftime('%Y-%m')
                        m_colors_inline = get_color_scheme()
                        m_tpl = get_plotly_template(m_colors_inline)
                        bar_colors_m = ['#FF3B30' if x > 0 else '#34C759' for x in monthly_data['strategy_return']]
                        monthly_fig = go.Figure()
                        monthly_fig.add_trace(go.Bar(
                            x=monthly_data['month'], y=monthly_data['strategy_return'] * 100,
                            name='月度收益率', marker=dict(color=bar_colors_m, opacity=0.85),
                        ))
                        monthly_fig.add_hline(y=0, line_dash="dot", line_color=m_colors_inline['text_secondary'], opacity=0.4)
                        monthly_fig.update_layout(**m_tpl)
                        monthly_fig.update_layout(
                            title=f"{strategy_name} - 月度收益率分布", height=380,
                            xaxis=dict(tickangle=0), yaxis=dict(title='收益率 (%)'),
                        )
                        st.plotly_chart(monthly_fig, use_container_width=True, key=f"monthly_{stock_code}_{strategy_name}")

                        # 交易频率分布
                        st.subheader(f"{strategy_name} - 交易频率分布")
                        monthly_trades = resample_monthly(strategy_data, {
                            'signal': lambda x: sum(abs(s) for s in x if s != 0)
                        })
                        monthly_trades['month'] = monthly_trades.index.strftime('%Y-%m')
                        tf_colors = get_color_scheme()
                        tf_tpl = get_plotly_template(tf_colors)
                        trade_freq_fig = go.Figure()
                        trade_freq_fig.add_trace(go.Bar(
                            x=monthly_trades['month'], y=monthly_trades['signal'],
                            name='交易次数', marker=dict(color='#007AFF', opacity=0.8),
                        ))
                        trade_freq_fig.update_layout(**tf_tpl)
                        trade_freq_fig.update_layout(
                            title=f"{strategy_name} - 月度交易频率分布", height=380,
                            xaxis=dict(tickangle=0), yaxis=dict(title='交易次数'),
                        )
                        st.plotly_chart(trade_freq_fig, use_container_width=True, key=f"trade_freq_{stock_code}_{strategy_name}")
                    
                    # 保存结果
                    # 保存回测结果到CSV
                    csv_buffer = io.StringIO()
                    strategy_data.to_csv(csv_buffer)
                    csv_str = csv_buffer.getvalue()
                    b64 = base64.b64encode(csv_str.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="{stock_code}_{strategy_name.replace(" ", "_")}_backtest_results.csv">下载{stock_display} - {strategy_name}回测结果CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    # 使用Matplotlib生成综合分析PNG（避免依赖Chrome）
                    try:
                        import matplotlib.pyplot as plt
                        import matplotlib.dates as mdates
                        import numpy as np
                        
                        # 创建6行1列的子图
                        fig, ((ax1, ax2), (ax3, ax4), (ax5, ax6)) = plt.subplots(3, 2, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 2, 2]})
                        
                        # 设置中文字体
                        plt.rcParams['font.sans-serif'] = ['SimHei']
                        plt.rcParams['axes.unicode_minus'] = False
                        
                        # 1. 价格走势和交易信号
                        ax1.plot(strategy_data.index, strategy_data['close'], 'b-', label='收盘价', linewidth=1)
                        # 检查MA25列是否存在
                        if 'MA25' in strategy_data.columns:
                            ax1.plot(strategy_data.index, strategy_data['MA25'], 'orange', label='MA25', linewidth=1.5)
                        
                        # 标记买卖信号
                        buy_signals = strategy_data[strategy_data.get('signal', 0) == 1]
                        add_signals = strategy_data[strategy_data.get('signal', 0) == 2]
                        sell_signals = strategy_data[strategy_data.get('signal', 0) == -1]
                        buyback_signals = strategy_data[strategy_data.get('signal', 0) == 3]
                        stop_loss_signals = strategy_data[strategy_data.get('signal', 0) == 4]
                        
                        if not buy_signals.empty:
                            ax1.scatter(buy_signals.index, buy_signals['close'], color='green', marker='^', s=50, label='买入')
                        if not add_signals.empty:
                            ax1.scatter(add_signals.index, add_signals['close'], color='blue', marker='x', s=50, label='加仓')
                        if not sell_signals.empty:
                            ax1.scatter(sell_signals.index, sell_signals['close'], color='red', marker='v', s=50, label='卖出')
                        if not buyback_signals.empty:
                            ax1.scatter(buyback_signals.index, buyback_signals['close'], color='yellow', marker='o', s=50, label='买回')
                        if not stop_loss_signals.empty:
                            ax1.scatter(stop_loss_signals.index, stop_loss_signals['close'], color='orange', marker='x', s=50, label='止损')
                        
                        ax1.set_title(f'{stock_display} - {strategy_name} 价格走势和交易信号')
                        ax1.set_ylabel('价格')
                        ax1.legend(loc='upper left')
                        ax1.grid(True, alpha=0.3)
                        
                        # 设置日期格式
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 2. 策略净值曲线
                        ax2.plot(strategy_data.index, strategy_data['cumulative_return'], 'b-', label='策略净值', linewidth=2)
                        ax2.axhline(y=1, linestyle='--', color='gray', label='基准线')
                        ax2.set_title(f'{strategy_name} - 策略净值变化')
                        ax2.set_ylabel('净值')
                        ax2.legend(loc='upper left')
                        ax2.grid(True, alpha=0.3)
                        
                        # 设置日期格式
                        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 3. 成交量和均量线
                        # 计算均量线
                        strategy_data['VMA5'] = strategy_data['volume'].rolling(window=5).mean()
                        strategy_data['VMA60'] = strategy_data['volume'].rolling(window=60).mean()
                        
                        # 计算涨跌颜色
                        strategy_data['color'] = ['red' if close > open else 'green' for close, open in zip(strategy_data['close'], strategy_data['open'])]
                        
                        # 绘制成交量柱体
                        for i, (date, row) in enumerate(strategy_data.iterrows()):
                            ax3.bar(date, row['volume'], color=row['color'], alpha=0.3)
                        
                        # 绘制均量线
                        ax3.plot(strategy_data.index, strategy_data['VMA5'], 'b-', label='VMA5', linewidth=1)
                        ax3.plot(strategy_data.index, strategy_data['VMA60'], 'orange', label='VMA60', linewidth=1)
                        
                        ax3.set_title('成交量和均量线')
                        ax3.set_ylabel('成交量')
                        ax3.legend(loc='upper left')
                        ax3.grid(True, alpha=0.3)
                        
                        # 设置日期格式
                        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 4. 回撤曲线
                        ax4.plot(strategy_data.index, strategy_data['drawdown'] * 100, 'r-', label='回撤 (%)', linewidth=2)
                        ax4.fill_between(strategy_data.index, 0, strategy_data['drawdown'] * 100, color='red', alpha=0.2)
                        ax4.set_title(f'{strategy_name} - 策略回撤情况')
                        ax4.set_ylabel('回撤 (%)')
                        ax4.legend(loc='upper left')
                        ax4.grid(True, alpha=0.3)
                        
                        # 设置日期格式
                        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 5. 仓位和策略收益率
                        ax5.plot(strategy_data.index, strategy_data['position'] * 100, 'g-', label='仓位 (%)', linewidth=1)
                        ax5.set_ylabel('仓位 (%)', color='green')
                        ax5.tick_params(axis='y', labelcolor='green')
                        ax5.set_ylim(0, 100)
                        
                        # 创建第二个y轴用于策略收益率
                        ax5_right = ax5.twinx()
                        ax5_right.plot(strategy_data.index, (strategy_data['cumulative_return'] - 1) * 100, 'b-', label='策略收益率 (%)', linewidth=1)
                        ax5_right.set_ylabel('策略收益率 (%)', color='blue')
                        ax5_right.tick_params(axis='y', labelcolor='blue')
                        
                        ax5.set_title(f'{strategy_name} - 仓位和策略收益率')
                        ax5.grid(True, alpha=0.3)
                        
                        # 合并图例
                        lines1, labels1 = ax5.get_legend_handles_labels()
                        lines2, labels2 = ax5_right.get_legend_handles_labels()
                        ax5.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
                        
                        # 设置日期格式
                        ax5.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax5.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 6. 性能指标雷达图
                        # 标准化指标值
                        normalized_metrics = {
                            '总收益率': min(metrics['total_return'] * 100, 100),
                            '年化收益率': min(metrics['annual_return'] * 100, 100),
                            '夏普比率': min(metrics['sharpe_ratio'], 5) * 20,  # 转换为0-100
                            '胜率': min(metrics['win_rate'] * 100, 100),
                            '最大回撤': min(abs(metrics['max_drawdown']) * 100, 100),
                            '交易频率': min(metrics['total_trades'] / (len(strategy_data)/252) * 12, 120) * 0.83  # 转换为0-100
                        }
                        
                        # 绘制雷达图
                        categories = list(normalized_metrics.keys())
                        values = list(normalized_metrics.values())
                        N = len(categories)
                        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
                        values += values[:1]  # 闭合
                        angles += angles[:1]
                        
                        ax6.plot(angles, values, 'o-', linewidth=2, label='性能指标')
                        ax6.fill(angles, values, alpha=0.25)
                        ax6.set_xticks(angles[:-1])
                        ax6.set_xticklabels(categories)
                        ax6.set_ylim(0, 100)
                        ax6.set_title(f'{strategy_name} - 策略性能指标')
                        ax6.grid(True)
                        
                        # 调整布局
                        plt.tight_layout()
                        
                        # 保存图片
                        strategy_filename = strategy_name.replace(" ", "_")
                        plt.savefig(f"{stock_code}_{strategy_filename}_comprehensive_analysis.png", dpi=100, bbox_inches='tight')
                        plt.close()
                        
                        # 读取并提供下载
                        with open(f"{stock_code}_{strategy_filename}_comprehensive_analysis.png", "rb") as f:
                            comprehensive_png = f.read()
                        b64 = base64.b64encode(comprehensive_png).decode()
                        href = f'<a href="data:image/png;base64,{b64}" download="{stock_code}_{strategy_filename}_comprehensive_analysis.png">下载{stock_display} - {strategy_name}综合分析PNG</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        # 计算月度数据并保存为单独的PNG
                        try:
                            # 创建月度分析图表
                            fig2, (ax7, ax8) = plt.subplots(2, 1, figsize=(14, 6))
                            
                            # 月度收益率
                            monthly_data = resample_monthly(strategy_data, {
                                'strategy_return': 'sum'
                            })
                            monthly_data['month'] = monthly_data.index.strftime('%Y-%m')
                            
                            colors = ['red' if x > 0 else 'green' for x in monthly_data['strategy_return']]
                            ax7.bar(monthly_data['month'], monthly_data['strategy_return'] * 100, color=colors, label='月度收益率')
                            ax7.set_title(f'{strategy_name} - 月度收益率分布')
                            ax7.set_xlabel('月份')
                            ax7.set_ylabel('收益率 (%)')
                            ax7.legend()
                            ax7.grid(True, alpha=0.3)
                            plt.setp(ax7.xaxis.get_majorticklabels(), rotation=45)
                            
                            # 交易频率分布
                            monthly_trades = resample_monthly(strategy_data, {
                                'signal': lambda x: sum(abs(s) for s in x if s != 0)
                            })
                            monthly_trades['month'] = monthly_trades.index.strftime('%Y-%m')
                            
                            ax8.bar(monthly_trades['month'], monthly_trades['signal'], color='blue', label='交易次数')
                            ax8.set_title(f'{strategy_name} - 月度交易频率分布')
                            ax8.set_xlabel('月份')
                            ax8.set_ylabel('交易次数')
                            ax8.legend()
                            ax8.grid(True, alpha=0.3)
                            plt.setp(ax8.xaxis.get_majorticklabels(), rotation=45)
                            
                            # 调整布局
                            plt.tight_layout()
                            
                            # 保存图片
                            plt.savefig(f"{stock_code}_{strategy_filename}_monthly_analysis.png", dpi=100, bbox_inches='tight')
                            plt.close()
                            
                            # 读取并提供下载
                            with open(f"{stock_code}_{strategy_filename}_monthly_analysis.png", "rb") as f:
                                monthly_png = f.read()
                            b64 = base64.b64encode(monthly_png).decode()
                            href = f'<a href="data:image/png;base64,{b64}" download="{stock_code}_{strategy_filename}_monthly_analysis.png">下载{stock_display} - {strategy_name}月度分析PNG</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"生成月度分析PNG失败: {str(e)}")
                        
                        st.success("PNG图片生成成功！")
                    except Exception as e:
                        st.error(f"生成PNG失败: {str(e)}")
            
            # 如果有多个股票，生成比较图表
            if len(stock_codes) > 1:
                st.header("多股票比较")
                
                # 生成收益率比较图表
                comparison_fig = go.Figure()
                for stock_code in stock_codes:
                    # 对于每个股票，获取其策略数据
                    for strategy_name in strategies:
                        if strategy_name in all_data[stock_code]:
                            data = all_data[stock_code][strategy_name]
                            comparison_fig.add_trace(go.Scatter(
                                x=data.index,
                                y=(data['cumulative_return'] - 1) * 100,
                                mode='lines',
                                name=f'{stock_code} - {strategy_name}'
                            ))
                
                comparison_fig.update_layout(
                    title='多股票策略收益率对比',
                    xaxis_title='日期',
                    yaxis_title='收益率 (%)',
                    hovermode='x unified',
                    height=400,
                    xaxis=dict(
                        type="date",
                        tickformat="%Y-%m",  # 只显示年月
                        tickangle=45,  # 旋转标签避免重叠
                        nticks=20  # 限制显示的刻度数量
                    ),
                    # 启用缩放和平移工具
                    dragmode="zoom",
                    # 添加工具栏
                    modebar=dict(
                        orientation="h",
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        activecolor="#007bff"
                    )
                )
                
                st.plotly_chart(comparison_fig, use_container_width=True)
                
                # 生成性能指标比较表格
                comparison_data = []
                for result in all_results:
                    comparison_data.append({
                        '股票代码': result['stock_code'],
                        '策略': result['strategy'],
                        '总收益率': f"{result['metrics']['total_return']:.2%}",
                        '年化收益率': f"{result['metrics']['annual_return']:.2%}",
                        '最大回撤': f"{result['metrics']['max_drawdown']:.2%}",
                        '夏普比率': f"{result['metrics']['sharpe_ratio']:.2f}",
                        '总盈利（元）': f"{result['metrics']['total_profit']:.2f}",
                        '胜率': f"{result['metrics']['win_rate']:.2%}"
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                st.table(comparison_df)
            
            # 如果有多个策略，生成策略对比图表
            if len(strategies) > 1:
                st.header("策略对比")
                
                # 为每个股票生成策略对比
                for stock_code in stock_codes:
                    if stock_code in all_data:
                        stock_name = get_stock_name(stock_code)
                        stock_display = f"{stock_code} - {stock_name}" if stock_name else stock_code
                        
                        st.subheader(f"{stock_display} 策略对比")
                        
                        # 生成策略净值对比图表
                        strategy_compare_fig = go.Figure()
                        for strategy_name in strategies:
                            if strategy_name in all_data[stock_code]:
                                data = all_data[stock_code][strategy_name]
                                strategy_compare_fig.add_trace(go.Scatter(
                                    x=data.index,
                                    y=data['cumulative_return'],
                                    mode='lines',
                                    name=strategy_name
                                ))
                        
                        strategy_compare_fig.add_hline(y=1, line_dash="dash", line_color="gray", name="基准线")
                        strategy_compare_fig.update_layout(
                            title=f'{stock_display} 策略净值对比',
                            xaxis_title='日期',
                            yaxis_title='净值',
                            hovermode='x unified',
                            height=400,
                            xaxis=dict(
                                type="category",
                                tickmode="array",
                                tickvals=data.index[::max(1, len(data)//20)],
                                ticktext=data.index[::max(1, len(data)//20)].strftime('%Y-%m'),
                                tickangle=45
                            )
                        )
                        st.plotly_chart(strategy_compare_fig, use_container_width=True)
                        
                        # 生成策略性能指标对比表格
                        strategy_comparison_data = []
                        for strategy_name in strategies:
                            if strategy_name in all_data[stock_code]:
                                # 找到对应的结果
                                for result in all_results:
                                    if result['stock_code'] == stock_code and result['strategy'] == strategy_name:
                                        metrics = result['metrics']
                                        break
                                strategy_comparison_data.append({
                                    '策略': strategy_name,
                                    '总收益率': f"{metrics['total_return']:.2%}",
                                    '年化收益率': f"{metrics['annual_return']:.2%}",
                                    '最大回撤': f"{metrics['max_drawdown']:.2%}",
                                    '夏普比率': f"{metrics['sharpe_ratio']:.2f}",
                                    '胜率': f"{metrics['win_rate']:.2%}",
                                    '总交易次数': f"{metrics['total_trades']}"
                                })
                        
                        if strategy_comparison_data:
                            strategy_comparison_df = pd.DataFrame(strategy_comparison_data)
                            st.table(strategy_comparison_df)
            
            st.success("回测完成！")
            
        except Exception as e:
            st.error(f"回测过程中出现错误: {str(e)}")

if __name__ == '__main__':
    main()
