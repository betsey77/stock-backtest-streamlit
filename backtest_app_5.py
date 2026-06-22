import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import plotly.graph_objects as go
ef = None  # efinance is disabled on Streamlit Cloud because it writes inside site-packages.
import yfinance as yf
import io
import base64
import os
import sys
import time
import random
import requests
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Fix Windows GBK console encoding — prevents emoji crash in TickFlow
if sys.platform == 'win32':
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

from tickflow import TickFlow

LUXE_ALPHA_LOGO_SVG = """
<svg class="lux-alpha-logo" viewBox="0 0 120 120" role="img" aria-label="77 stock strategy logo" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="mark77-frame" x1="10" y1="10" x2="110" y2="110" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FFE9A6"/>
      <stop offset="0.48" stop-color="#C99A3A"/>
      <stop offset="1" stop-color="#8F6A1F"/>
    </linearGradient>
    <filter id="mark77-lift" x="-18%" y="-18%" width="136%" height="136%">
      <feDropShadow dx="0" dy="7" stdDeviation="7" flood-color="#3B2A10" flood-opacity="0.14"/>
    </filter>
  </defs>
  <rect x="8" y="8" width="104" height="104" rx="24" fill="#FFFEFB" stroke="url(#mark77-frame)" stroke-width="2.8" filter="url(#mark77-lift)"/>
  <g fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M28 34H61L34 88" stroke="#E8578B" stroke-width="11"/>
    <path d="M58 34H91L64 88" stroke="#4A90D9" stroke-width="11"/>
    <path d="M28 34H61" stroke="#D9A441" stroke-width="11"/>
    <path d="M58 34H91" stroke="#202532" stroke-width="11"/>
    <path d="M35 88L49 59" stroke="#7B61C9" stroke-width="11"/>
    <path d="M64 88L78 59" stroke="#7DCB6D" stroke-width="11"/>
    <path d="M30 78C45 69 64 72 88 52" stroke="#2EA7A0" stroke-width="3.2"/>
  </g>
  <circle cx="28" cy="34" r="2.5" fill="#E8578B"/>
  <circle cx="61" cy="34" r="2.5" fill="#4A90D9"/>
  <circle cx="91" cy="34" r="2.5" fill="#7DCB6D"/>
  <circle cx="88" cy="52" r="2.5" fill="#F0985C"/>
  <path d="M96 18l3 7 7 3-7 3-3 7-3-7-7-3 7-3z" fill="#D9A441"/>
  <path d="M20 91l2.5 5.5 5.5 2.5-5.5 2.5L20 108l-2.5-5.5L12 100l5.5-2.5z" fill="#7B61C9"/>
</svg>
"""

BACKGROUND_77_PATTERN_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
  <rect width="960" height="540" fill="#FBFAF7"/>
  <g opacity="0.28" fill="none" stroke="#D8BE78" stroke-width="1.1">
    <path d="M20 42c48-18 92-18 142 0M260 42c48-18 92-18 142 0M500 42c48-18 92-18 142 0M740 42c48-18 92-18 142 0"/>
    <path d="M20 162c48-18 92-18 142 0M260 162c48-18 92-18 142 0M500 162c48-18 92-18 142 0M740 162c48-18 92-18 142 0"/>
    <path d="M20 282c48-18 92-18 142 0M260 282c48-18 92-18 142 0M500 282c48-18 92-18 142 0M740 282c48-18 92-18 142 0"/>
    <path d="M20 402c48-18 92-18 142 0M260 402c48-18 92-18 142 0M500 402c48-18 92-18 142 0M740 402c48-18 92-18 142 0"/>
  </g>
  <g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.72">
    <path d="M74 64h30L80 116" stroke="#E8578B" stroke-width="10"/>
    <path d="M104 64h30l-24 52" stroke="#4A90D9" stroke-width="10"/>
    <path d="M74 64h30" stroke="#D9A441" stroke-width="10"/>
    <path d="M104 64h30" stroke="#202532" stroke-width="10"/>
    <path d="M84 104c24-15 44-12 64-31" stroke="#2EA7A0" stroke-width="3"/>

    <path d="M442 64h30l-24 52" stroke="#7B61C9" stroke-width="10"/>
    <path d="M472 64h30l-24 52" stroke="#7DCB6D" stroke-width="10"/>
    <path d="M442 64h30" stroke="#A58FE8" stroke-width="10"/>
    <path d="M472 64h30" stroke="#2EA7A0" stroke-width="10"/>
    <path d="M452 104c24-15 44-12 64-31" stroke="#2EA7A0" stroke-width="3"/>

    <path d="M714 304h30l-24 52" stroke="#B88928" stroke-width="10"/>
    <path d="M744 304h30l-24 52" stroke="#E8578B" stroke-width="10"/>
    <path d="M714 304h30" stroke="#202532" stroke-width="10"/>
    <path d="M744 304h30" stroke="#7DCB6D" stroke-width="10"/>
    <path d="M724 344c24-15 44-12 64-31" stroke="#2EA7A0" stroke-width="3"/>
  </g>
  <g opacity="0.50">
    <circle cx="260" cy="84" r="4" fill="#E8578B"/><circle cx="286" cy="84" r="4" fill="#4A90D9"/><circle cx="286" cy="110" r="4" fill="#2EA7A0"/><circle cx="260" cy="110" r="4" fill="#D9A441"/>
    <circle cx="654" cy="90" r="4" fill="#F0985C"/><circle cx="680" cy="90" r="4" fill="#7B61C9"/><circle cx="680" cy="116" r="4" fill="#7DCB6D"/><circle cx="654" cy="116" r="4" fill="#4A90D9"/>
    <circle cx="204" cy="330" r="4" fill="#4A90D9"/><circle cx="230" cy="330" r="4" fill="#E8578B"/><circle cx="230" cy="356" r="4" fill="#F0985C"/><circle cx="204" cy="356" r="4" fill="#2EA7A0"/>
    <path d="M842 78l7 15 15 7-15 7-7 15-7-15-15-7 15-7z" fill="#D9A441"/>
    <path d="M352 302l7 15 15 7-15 7-7 15-7-15-15-7 15-7z" fill="#E8578B"/>
    <path d="M542 392l7 15 15 7-15 7-7 15-7-15-15-7 15-7z" fill="#4A90D9"/>
  </g>
</svg>
"""

BACKGROUND_77_PATTERN_URI = "data:image/svg+xml;base64," + base64.b64encode(
    BACKGROUND_77_PATTERN_SVG.encode("utf-8")
).decode("ascii")

pattern_file = Path(__file__).with_name("background_77_multicolor_pattern.svg")
if pattern_file.exists():
    BACKGROUND_77_PATTERN_SVG = pattern_file.read_text(encoding="utf-8")
    BACKGROUND_77_PATTERN_URI = "data:image/svg+xml;base64," + base64.b64encode(
        BACKGROUND_77_PATTERN_SVG.encode("utf-8")
    ).decode("ascii")

def asset_data_uri(relative_path, mime_type):
    asset_path = Path(__file__).resolve().parent / relative_path
    if not asset_path.exists():
        return None
    return "data:{mime};base64,{payload}".format(
        mime=mime_type,
        payload=base64.b64encode(asset_path.read_bytes()).decode("ascii"),
    )

SIDEBAR_MEDALLION_URI = asset_data_uri("assets/brand/sidebar_medallion.png", "image/png")
HERO_ALPHA_BADGE_URI = asset_data_uri("assets/brand/hero_alpha_badge.png", "image/png")
AGENT_ANALYST_PATH = Path(__file__).resolve().parent / "assets/brand/agent_analyst.png"
CLOSING_BANNER_PATH = Path(__file__).resolve().parent / "assets/brand/closing_banner.png"
CLOSING_WORDMARK_EN_PATH = Path(__file__).resolve().parent / "assets/brand/closing_wordmark_en.png"
CLOSING_WORDMARK_CN_PATH = Path(__file__).resolve().parent / "assets/brand/closing_wordmark_cn.png"
BRAND_BACKGROUND_CSS = f'url("{BACKGROUND_77_PATTERN_URI}")'
SIDEBAR_MEDALLION_HTML = (
    f'<img class="lux-alpha-sidebar-medallion" src="{SIDEBAR_MEDALLION_URI}" alt="77 AIpha Atelier medallion">'
    if SIDEBAR_MEDALLION_URI
    else LUXE_ALPHA_LOGO_SVG
)
HERO_ALPHA_BADGE_HTML = (
    f'<img class="lux-alpha-hero-badge" src="{HERO_ALPHA_BADGE_URI}" alt="77 AIpha Atelier badge">'
    if HERO_ALPHA_BADGE_URI
    else LUXE_ALPHA_LOGO_SVG
)

# 77 theme chart semantics: A-share convention uses red for rise, green for fall.
RISE_RED = "#E8578B"
RISE_RED_DARK = "#B91C4C"
RISE_RED_SOFT = "rgba(232,87,139,0.18)"
FALL_GREEN = "#2EA7A0"
FALL_GREEN_DARK = "#16766F"
FALL_GREEN_SOFT = "rgba(46,167,160,0.16)"
SIGNAL_BLUE = "#4A90D9"
SIGNAL_GOLD = "#D9A441"
SIGNAL_PURPLE = "#7B61C9"
SIGNAL_ORANGE = "#F0985C"
SIGNAL_LIME = "#7DCB6D"
NEUTRAL_INK = "#202532"
CHART_ACCENT_PALETTE = [
    RISE_RED, SIGNAL_BLUE, SIGNAL_LIME, SIGNAL_GOLD,
    NEUTRAL_INK, SIGNAL_PURPLE, SIGNAL_ORANGE, FALL_GREEN,
]

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
    """初始化 TickFlow 客户端（session 内只尝试一次，缓存结果）"""
    import contextlib

    # 已初始化过，直接返回缓存结果
    if "_tickflow_client" in st.session_state:
        return st.session_state["_tickflow_client"]

    stderr_discard = open(os.devnull, 'w', encoding='utf-8')
    client = None
    try:
        api_key = get_deploy_secret("TICKFLOW_API_KEY")
        if api_key:
            with contextlib.redirect_stderr(stderr_discard), contextlib.redirect_stdout(stderr_discard):
                client = TickFlow(api_key=api_key)
        else:
            with contextlib.redirect_stderr(stderr_discard), contextlib.redirect_stdout(stderr_discard):
                client = TickFlow.free()
    except Exception:
        # 静默失败，回退到 efinance / yfinance
        pass
    finally:
        stderr_discard.close()

    st.session_state["_tickflow_client"] = client
    return client

def configure_matplotlib_chinese_font():
    """Pick an installed CJK font so generated PNG charts keep Chinese labels."""
    candidates = [
        'Noto Sans CJK SC',
        'Noto Sans CJK JP',
        'Noto Sans CJK TC',
        'Source Han Sans SC',
        'Microsoft YaHei',
        'SimHei',
        'PingFang SC',
        'Arial Unicode MS',
    ]
    installed_fonts = {font.name for font in font_manager.fontManager.ttflist}
    available_fonts = [font for font in candidates if font in installed_fonts]
    return available_fonts + ['DejaVu Sans']


# Matplotlib 简约白色风格设置
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = configure_matplotlib_chinese_font()
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#F3F4F6'
plt.rcParams['axes.facecolor'] = '#FFFFFF'
plt.rcParams['axes.edgecolor'] = '#E5E7EB'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.25
plt.rcParams['grid.color'] = '#E5E7EB'
plt.rcParams['text.color'] = '#1F2937'
plt.rcParams['axes.labelcolor'] = '#6B7280'
plt.rcParams['xtick.color'] = '#6B7280'
plt.rcParams['ytick.color'] = '#6B7280'
plt.rcParams['font.size'] = 11
plt.rcParams['lines.linewidth'] = 1.5
plt.rcParams['lines.color'] = SIGNAL_BLUE

# 设置Streamlit主题
st.set_page_config(
    page_title="77股票交易策略回测工作台",
    page_icon="77",
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

# 根据主题获取颜色方案 - 白色基底 + 多色图表
def get_color_scheme():
    """返回白色卡片风格的 Plotly 图表颜色方案"""
    theme = get_theme_mode()
    if theme == 'dark':
        return {
            'bg_color': '#141722',
            'paper_color': '#1D2230',
            'text_color': '#F8F7F2',
            'text_secondary': '#B8BFD0',
            'grid_color': 'rgba(255,255,255,0.07)',
            'zero_line': 'rgba(255,255,255,0.12)',
            'border_color': 'rgba(216,190,120,0.18)',
            'hover_bg': 'rgba(29,34,48,0.97)',
            'hover_border': RISE_RED,
            'accent': RISE_RED,
        }
    else:
        return {
            'bg_color': '#FAF8F2',
            'paper_color': 'rgba(255,255,255,0.96)',
            'text_color': '#171923',
            'text_secondary': '#667085',
            'grid_color': 'rgba(143,106,31,0.10)',
            'zero_line': 'rgba(32,37,50,0.10)',
            'border_color': 'rgba(216,190,120,0.34)',
            'hover_bg': 'rgba(255,255,255,0.98)',
            'hover_border': RISE_RED,
            'accent': RISE_RED,
        }

# 统一的 Plotly 图表简约白色风格模板
def get_plotly_template(colors):
    """返回简约白色风格 Plotly layout 基础配置"""
    return dict(
        plot_bgcolor=colors['paper_color'],
        paper_bgcolor=colors['bg_color'],
        font=dict(
            color=colors['text_color'],
            size=12,
            family='"Inter", -apple-system, "PingFang SC", sans-serif'
        ),
        xaxis=dict(
            gridcolor=colors['grid_color'],
            zerolinecolor=colors['zero_line'],
            color=colors['text_secondary'],
            tickfont=dict(size=10),
            title_font=dict(size=11, color=colors['text_color']),
        ),
        yaxis=dict(
            gridcolor=colors['grid_color'],
            zerolinecolor=colors['zero_line'],
            color=colors['text_secondary'],
            tickfont=dict(size=10),
            title_font=dict(size=11, color=colors['text_color']),
        ),
        hoverlabel=dict(
            bgcolor=colors['hover_bg'],
            bordercolor=colors['hover_border'],
            font=dict(size=11, color=colors['text_color'], family='"JetBrains Mono", "SF Mono", monospace'),
            namelength=-1,
        ),
        legend=dict(
            bgcolor='rgba(255,255,255,0.0)',
            bordercolor='rgba(0,0,0,0)',
            font=dict(size=11, color=colors['text_secondary']),
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
        ),
        margin=dict(l=40, r=24, t=48, b=40),
        dragmode=False,
        modebar=dict(
            bgcolor='rgba(0,0,0,0)',
            color=colors['text_secondary'],
            activecolor=colors['accent'],
            orientation='h',
        ),
        colorway=CHART_ACCENT_PALETTE,
    )

CHART_RENDER_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
    "doubleClick": False,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d",
        "zoomIn2d", "zoomOut2d", "autoScale2d",
        "resetScale2d", "orbitRotation", "tableRotation",
    ],
}

KLINE_RENDER_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": True,
    "doubleClick": "reset",
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}

def render_chart(fig, key=None, config=None):
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=config or CHART_RENDER_CONFIG,
        key=key,
    )

def render_agent_analysis_card():
    if not AGENT_ANALYST_PATH.exists():
        return
    left, right = st.columns([1, 5])
    with left:
        st.image(str(AGENT_ANALYST_PATH), width=128)
    with right:
        st.markdown(
            "**77AIpha 智能体分析**  \n"
            "综合收益、回撤、夏普比率、胜率与交易频率，生成当前策略的智能评估结论。"
        )

def render_completion_brand_assets():
    brand_assets = [
        CLOSING_BANNER_PATH,
        CLOSING_WORDMARK_EN_PATH,
        CLOSING_WORDMARK_CN_PATH,
    ]
    existing_assets = [path for path in brand_assets if path.exists()]
    if not existing_assets:
        return
    st.markdown("---")
    for path in existing_assets:
        st.image(str(path), use_container_width=True)

def generate_strategy_metric_scatter(strategy_rows, stock_display):
    """Create a quadrant bubble chart for multi-strategy metric judgment."""
    if not strategy_rows:
        return None

    df = pd.DataFrame(strategy_rows)
    if df.empty:
        return None

    df["收益能力"] = df["annual_return"] * 100
    df["风险控制"] = (1 - df["max_drawdown"].abs()).clip(lower=0) * 100
    df["胜率"] = df["win_rate"] * 100
    df["回撤"] = df["max_drawdown"].abs() * 100
    df["夏普气泡"] = (df["sharpe_ratio"].clip(lower=0) + 0.35) * 28
    df["综合评分"] = (
        df["total_return"] * 30
        + df["annual_return"] * 25
        + (1 + df["max_drawdown"]) * 20
        + df["sharpe_ratio"] * 15
        + df["win_rate"] * 10
    )
    x_mid = float(df["收益能力"].median()) if len(df) > 1 else float(df["收益能力"].iloc[0])
    y_mid = float(df["风险控制"].median()) if len(df) > 1 else float(df["风险控制"].iloc[0])

    x_min = min(float(df["收益能力"].min()), x_mid) - 4
    x_max = max(float(df["收益能力"].max()), x_mid) + 4
    y_min = max(0, min(float(df["风险控制"].min()), y_mid) - 4)
    y_max = min(105, max(float(df["风险控制"].max()), y_mid) + 4)
    if x_min == x_max:
        x_min -= 5
        x_max += 5
    if y_min == y_max:
        y_min = max(0, y_min - 5)
        y_max = min(105, y_max + 5)

    colors = get_color_scheme()
    tpl = get_plotly_template(colors)
    fig = go.Figure()

    # Quadrant backgrounds: upper-right is the preferred region.
    fig.add_shape(type="rect", x0=x_min, x1=x_mid, y0=y_mid, y1=y_max,
                  fillcolor="rgba(74,144,217,0.09)", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=x_mid, x1=x_max, y0=y_mid, y1=y_max,
                  fillcolor="rgba(46,167,160,0.11)", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=x_min, x1=x_mid, y0=y_min, y1=y_mid,
                  fillcolor="rgba(232,87,139,0.09)", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=x_mid, x1=x_max, y0=y_min, y1=y_mid,
                  fillcolor="rgba(217,164,65,0.10)", line=dict(width=0), layer="below")

    fig.add_vline(x=x_mid, line_dash="dash", line_color="rgba(32,37,50,0.36)")
    fig.add_hline(y=y_mid, line_dash="dash", line_color="rgba(32,37,50,0.36)")

    fig.add_trace(go.Scatter(
        x=df["收益能力"],
        y=df["风险控制"],
        mode="markers+text",
        text=df["strategy"],
        textposition="top center",
        marker=dict(
            size=df["夏普气泡"],
            color=df["综合评分"],
            colorscale=[
                [0, RISE_RED],
                [0.5, SIGNAL_GOLD],
                [1, FALL_GREEN],
            ],
            showscale=True,
            colorbar=dict(title="综合评分", thickness=12),
            opacity=0.82,
            line=dict(color="rgba(255,255,255,0.88)", width=1.6),
        ),
        customdata=np.stack([
            df["total_return"] * 100,
            df["annual_return"] * 100,
            df["回撤"],
            df["sharpe_ratio"],
            df["胜率"],
            df["total_trades"],
            df["综合评分"],
        ], axis=-1),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "总收益率: %{customdata[0]:.2f}%<br>"
            "年化收益率: %{customdata[1]:.2f}%<br>"
            "最大回撤: %{customdata[2]:.2f}%<br>"
            "夏普比率: %{customdata[3]:.2f}<br>"
            "胜率: %{customdata[4]:.2f}%<br>"
            "交易次数: %{customdata[5]:.0f}<br>"
            "综合评分: %{customdata[6]:.2f}<extra></extra>"
        ),
    ))

    annotations = [
        (x_min + (x_mid - x_min) * 0.5, y_mid + (y_max - y_mid) * 0.88, "稳健保守"),
        (x_mid + (x_max - x_mid) * 0.5, y_mid + (y_max - y_mid) * 0.88, "高效优选"),
        (x_min + (x_mid - x_min) * 0.5, y_min + (y_mid - y_min) * 0.12, "待优化"),
        (x_mid + (x_max - x_mid) * 0.5, y_min + (y_mid - y_min) * 0.12, "进攻高波动"),
    ]
    for x, y, label in annotations:
        fig.add_annotation(
            x=x,
            y=y,
            text=label,
            showarrow=False,
            bgcolor="rgba(255,255,255,0.72)",
            bordercolor="rgba(216,190,120,0.42)",
            borderwidth=1,
            font=dict(size=13, color=colors["text_color"]),
        )

    fig.update_layout(**tpl)
    fig.update_layout(
        title=f"{stock_display} 策略指标象限气泡图",
        height=560,
        xaxis=dict(
            title="收益能力：年化收益率 (%)，越右越强",
            range=[x_min, x_max],
            zeroline=True,
            zerolinecolor="rgba(32,37,50,0.16)",
        ),
        yaxis=dict(
            title="风险控制能力：1 - 最大回撤 (%)，越高越稳",
            range=[y_min, y_max],
            ticksuffix="%",
        ),
        showlegend=False,
        dragmode=False,
        margin=dict(l=56, r=32, t=72, b=58),
    )
    return fig

# 自定义CSS样式 - 白色基底 + 多色点缀卡片（v3 · cache-bust 2026-06-08）
st.markdown(
    f"""<style>:root {{ --pattern-77-bg: url("{BACKGROUND_77_PATTERN_URI}"); --brand-stage-bg: {BRAND_BACKGROUND_CSS}; --mx: 50vw; --my: 50vh; }}</style>""",
    unsafe_allow_html=True,
)

st.markdown("""
<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
    /* ═══════════════════════════════════════════════
     * Design Tokens — Luxe Alpha
     * Original white-gold financial atelier system · multi-accent signals
     * ═══════════════════════════════════════════════ */
    :root {
        --bg: #F6F7FA;
        --card: #FFFFFF;
        --text: #151922;
        --text-2: #667085;
        --text-3: #98A2B3;
        --ink: #12151C;
        --gold: #C99A3A;
        --gold-deep: #8F6A1F;
        --gold-soft: #F7E2A1;
        --accent-blue: #4A90D9;
        --accent-green: #2EA7A0;
        --accent-amber: #F0985C;
        --accent-purple: #8B6FC0;
        --accent-pink: #E87DA0;
        --accent-teal: #3BA99C;
        --border: #E4E7EE;
        --border-light: #F1F3F7;
        --shadow-card: 0 10px 30px rgba(18, 21, 28, 0.06), 0 1px 2px rgba(18, 21, 28, 0.04);
        --shadow-hover: 0 14px 44px rgba(18, 21, 28, 0.09);
        --radius: 8px;
        --radius-sm: 8px;
    }

    /* ── Global base · light gray canvas ── */
    .main {
        background-color: #F6F7FA !important;
        color: #151922;
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    [data-testid="stApp"] {
        background:
            radial-gradient(circle at 14% 8%, rgba(201,154,58,0.13), transparent 24%),
            radial-gradient(circle at 92% 12%, rgba(74,144,217,0.12), transparent 22%),
            linear-gradient(135deg, #FAFBFD 0%, #F6F7FA 52%, #EEF1F6 100%) !important;
    }

    body {
        background: #F6F7FA !important;
        overflow-x: hidden;
    }
    .main .block-container {
        padding: 2rem 2.5rem 4rem 2.5rem;
        max-width: 1440px;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(255,255,255,0.98), rgba(251,252,255,0.96)),
            repeating-linear-gradient(135deg, rgba(201,154,58,0.05) 0 1px, transparent 1px 16px);
        border-right: 1px solid rgba(201,154,58,0.20);
        box-shadow: 12px 0 36px rgba(18,21,28,0.04);
    }
    [data-testid="stSidebar"] .block-container {
        padding: 1.5rem 1.25rem;
    }

    /* ── Typography ── */
    h1 {
        font-size: 2rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.025em !important;
        color: #151922 !important;
        margin-bottom: 0.25rem !important;
        line-height: 1.2 !important;
    }
    h2 {
        font-size: 1.35rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.018em !important;
        color: #151922 !important;
        line-height: 1.25 !important;
        margin-top: 1.5rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.012em !important;
        color: #151922 !important;
    }
    p, li, span, div { color: #151922; }

    /* ── Luxe Alpha brand system ── */
    .lux-alpha-hero {
        position: relative;
        overflow: hidden;
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: 1.15rem;
        align-items: center;
        min-height: 132px;
        padding: 1.2rem 1.35rem;
        margin: 0 0 1.25rem 0;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.98), rgba(247,248,251,0.94)),
            radial-gradient(circle at 80% 20%, rgba(201,154,58,0.18), transparent 26%);
        border: 1px solid rgba(201,154,58,0.26);
        border-radius: 8px;
        box-shadow: var(--shadow-card);
    }
    .lux-alpha-hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background-image:
            radial-gradient(circle, rgba(232,87,139,0.18) 0 2px, transparent 2.5px),
            radial-gradient(circle, rgba(74,144,217,0.16) 0 2px, transparent 2.5px),
            radial-gradient(circle, rgba(46,167,160,0.15) 0 2px, transparent 2.5px);
        background-size: 78px 78px, 96px 96px, 116px 116px;
        background-position: 22px 18px, 46px 40px, 76px 8px;
        opacity: 0.72;
        pointer-events: none;
    }
    .lux-alpha-hero > * { position: relative; z-index: 1; }
    .lux-alpha-logo {
        width: 86px;
        height: 86px;
        display: block;
    }
    .lux-alpha-kicker {
        color: #8F6A1F !important;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 0.28rem;
    }
    .lux-alpha-title {
        margin: 0;
        color: #12151C !important;
        font-size: 2rem;
        font-weight: 650;
        letter-spacing: 0 !important;
        line-height: 1.1;
    }
    .lux-alpha-subtitle {
        margin-top: 0.42rem;
        color: #667085 !important;
        font-size: 0.92rem;
        line-height: 1.6;
        max-width: 760px;
    }
    .lux-alpha-badges {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 0.45rem;
        min-width: 240px;
    }
    .lux-alpha-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.38rem;
        padding: 0.42rem 0.58rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.82);
        border: 1px solid rgba(201,154,58,0.22);
        color: #475467 !important;
        font-size: 0.75rem;
        font-weight: 600;
        box-shadow: 0 6px 16px rgba(18,21,28,0.04);
    }
    .lux-alpha-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }
    .lux-alpha-sidebar-brand {
        padding: 0.95rem 0.95rem 1rem;
        margin-bottom: 1rem;
        border-radius: 8px;
        background: linear-gradient(135deg, #FFFFFF, #F8FAFC);
        border: 1px solid rgba(201,154,58,0.24);
        box-shadow: 0 8px 24px rgba(18,21,28,0.05);
    }
    .lux-alpha-sidebar-brand .lux-alpha-logo {
        width: 46px;
        height: 46px;
        margin-bottom: 0.45rem;
    }
    .lux-alpha-sidebar-title {
        font-size: 1rem;
        font-weight: 700;
        color: #12151C !important;
        margin: 0;
    }
    .lux-alpha-sidebar-caption {
        color: #667085 !important;
        font-size: 0.75rem;
        margin: 0.12rem 0 0;
    }

    /* ── Accent color helpers ── */
    .accent-blue   { color: #4A90D9 !important; }
    .accent-green  { color: #2EA7A0 !important; }
    .accent-amber  { color: #F0985C !important; }
    .accent-purple { color: #8B6FC0 !important; }
    .accent-pink   { color: #E87DA0 !important; }
    .accent-teal   { color: #3BA99C !important; }
    .text-caption {
        color: #6B7280 !important;
        font-size: 0.8rem;
        letter-spacing: 0.015em;
    }
    .text-mono {
        font-family: "JetBrains Mono", "SF Mono", monospace !important;
        font-feature-settings: "tnum";
        font-variant-numeric: tabular-nums;
    }

    /* ── Divider ── */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(201,154,58,0.32), transparent);
        margin: 1.5rem 0;
    }

    /* ── Buttons · white cards with colored border on hover ── */
    .stButton > button {
        background: linear-gradient(180deg, #FFFFFF, #FAFBFD);
        color: #151922;
        border: 1px solid rgba(201,154,58,0.34);
        border-radius: 8px;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        box-shadow: 0 8px 20px rgba(18,21,28,0.05);
    }
    .stButton > button:hover {
        border-color: #C99A3A;
        color: #8F6A1F;
        background: #FFFCF4;
        box-shadow: 0 10px 28px rgba(201,154,58,0.14);
    }
    .stButton > button:active {
        transform: scale(0.985);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #12151C 0%, #2D3342 58%, #C99A3A 140%);
        color: #FFFFFF;
        border-color: #12151C;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #06080D 0%, #242A37 58%, #D9A441 135%);
        border-color: #C99A3A;
        color: #FFFFFF;
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > div {
        background: rgba(255,255,255,0.94);
        color: #151922;
        border: 1px solid #D8DEE8;
        border-radius: 8px;
        font-size: 0.875rem;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #C99A3A;
        box-shadow: 0 0 0 3px rgba(201,154,58,0.14);
        outline: none;
    }

    /* ── Cards: white + thin border + subtle shadow ── */
    .stPlotlyChart {
        background: #FFFFFF;
        border-radius: 8px;
        box-shadow: var(--shadow-card);
        border: 1px solid rgba(201,154,58,0.18);
        padding: 1rem;
        margin: 0.75rem 0;
    }

    /* ── DataFrame / Table cards ── */
    [data-testid="stTable"], [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: var(--shadow-card);
        border: 1px solid rgba(201,154,58,0.16);
        background: #FFFFFF;
    }
    .stTable thead th {
        background: #F9FAFB;
        color: #6B7280;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.65rem 1rem;
        border-bottom: 1px solid #E5E7EB;
    }
    .stTable tbody td {
        padding: 0.6rem 1rem;
        font-size: 0.875rem;
        border-bottom: 1px solid #F3F4F6;
        color: #1F2937;
    }
    .stTable tbody tr:last-child td { border-bottom: none; }
    .stTable tbody tr:nth-child(even) { background: #F9FAFB; }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: #FFFFFF;
        border-radius: 8px;
        border: 1px solid rgba(201,154,58,0.18);
        box-shadow: var(--shadow-card);
    }
    [data-testid="stExpander"] summary {
        padding: 0.75rem 1.25rem;
        font-weight: 600;
        font-size: 0.9rem;
        color: #1F2937;
    }

    /* ── Metrics · card with colored left border ── */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        box-shadow: var(--shadow-card);
        border: 1px solid rgba(201,154,58,0.18);
        border-left: 4px solid #C99A3A;
        transition: box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-hover);
    }
    [data-testid="stMetric"] label {
        color: #6B7280 !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        color: #151922 !important;
    }

    /* ── Metric color variants via nth-child ── */
    [data-testid="stMetric"]:nth-child(4n+1) { border-left-color: #C99A3A; }
    [data-testid="stMetric"]:nth-child(4n+2) { border-left-color: #2EA7A0; }
    [data-testid="stMetric"]:nth-child(4n+3) { border-left-color: #E8578B; }
    [data-testid="stMetric"]:nth-child(4n+0) { border-left-color: #4A90D9; }

    /* ── Alerts ── */
    [data-testid="stSuccess"] {
        background: #F0FDF6;
        border: 1px solid #BBF7D0;
        border-radius: 8px;
        color: #166534;
    }
    [data-testid="stWarning"] {
        background: #FFFBF0;
        border: 1px solid #FDE68A;
        border-radius: 8px;
        color: #92400E;
    }
    [data-testid="stError"] {
        background: #FEF2F2;
        border: 1px solid #FECACA;
        border-radius: 8px;
        color: #991B1B;
    }
    [data-testid="stInfo"] {
        background: #F0F6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        color: #1E40AF;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 20px; }
    ::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        border-radius: 8px;
        border: 1.5px dashed rgba(201,154,58,0.42);
        background:
            linear-gradient(135deg, rgba(255,255,255,0.92), rgba(248,250,252,0.86)),
            radial-gradient(circle at 18% 24%, rgba(232,87,139,0.08), transparent 20%);
    }

    /* ── Slider ── */
    .stSlider > div > div > div > div { background: #C99A3A; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #E5E7EB;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.6rem 1.25rem;
        font-weight: 500;
        color: #6B7280;
    }
    .stTabs [aria-selected="true"] {
        color: #8F6A1F;
        border-bottom: 2px solid #C99A3A;
    }

    /* ═══════════════════════════════════════════════
     * Dark mode
     * ═══════════════════════════════════════════════ */
    [data-theme="dark"] .main, [data-theme="dark"] [data-testid="stApp"] {
        background: #111827 !important;
        color: #F3F4F6;
    }
    [data-theme="dark"] body { background: #111827 !important; }
    [data-theme="dark"] [data-testid="stSidebar"] {
        background: #1F2937;
        border-right: 1px solid #374151;
    }
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3,
    [data-theme="dark"] h4, [data-theme="dark"] h5, [data-theme="dark"] h6,
    [data-theme="dark"] p, [data-theme="dark"] li, [data-theme="dark"] span, [data-theme="dark"] div {
        color: #F3F4F6;
    }
    [data-theme="dark"] .text-caption { color: #9CA3AF !important; }
    [data-theme="dark"] .stButton > button {
        background: #1F2937;
        color: #F3F4F6;
        border-color: #374151;
    }
    [data-theme="dark"] .stButton > button:hover {
        border-color: #4A90D9;
        color: #60A5FA;
        background: #1E3A5F;
    }
    [data-theme="dark"] .stTextInput > div > div > input,
    [data-theme="dark"] .stNumberInput > div > div > input {
        background: #1F2937;
        color: #F3F4F6;
        border-color: #374151;
    }
    [data-theme="dark"] .stPlotlyChart,
    [data-theme="dark"] [data-testid="stExpander"],
    [data-theme="dark"] [data-testid="stMetric"],
    [data-theme="dark"] [data-testid="stTable"],
    [data-theme="dark"] [data-testid="stDataFrame"] {
        background: #1F2937;
        border-color: #374151;
    }
    [data-theme="dark"] [data-testid="stMetric"] label { color: #9CA3AF !important; }
    [data-theme="dark"] [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #F3F4F6 !important; }
    [data-theme="dark"] .stTable thead th {
        background: #111827;
        color: #9CA3AF;
        border-bottom-color: #374151;
    }
    [data-theme="dark"] .stTable tbody td {
        color: #F3F4F6;
        border-bottom-color: #1F2937;
    }
    [data-theme="dark"] .stTable tbody tr:nth-child(even) { background: #111827; }
    [data-theme="dark"] hr { background: #374151; }

    /* ═══════════════════════════════════════════════
     * 77 Multicolor luxury refresh
     * ═══════════════════════════════════════════════ */
    :root {
        --bg: #FAF8F2;
        --card: rgba(255,255,255,0.92);
        --text: #171923;
        --text-2: #667085;
        --ink: #202532;
        --gold: #D9A441;
        --gold-deep: #8F6A1F;
        --pink: #E8578B;
        --blue: #4A90D9;
        --green: #7DCB6D;
        --teal: #2EA7A0;
        --purple: #7B61C9;
        --orange: #F0985C;
        --border: rgba(216,190,120,0.34);
        --shadow-card: 0 18px 50px rgba(43, 33, 12, 0.08), 0 2px 5px rgba(43, 33, 12, 0.04);
        --shadow-hover: 0 22px 60px rgba(43, 33, 12, 0.13);
    }

    [data-testid="stApp"] {
        background:
            linear-gradient(180deg, rgba(255,255,255,0.78), rgba(250,248,242,0.92)),
            var(--brand-stage-bg),
            radial-gradient(circle at 14% 8%, rgba(232,87,139,0.12), transparent 22%),
            radial-gradient(circle at 88% 6%, rgba(74,144,217,0.12), transparent 24%),
            #FAF8F2 !important;
        background-size: auto, cover, auto, auto, auto !important;
        background-position: center top, center top, center, center, center !important;
        background-attachment: fixed, fixed, fixed, fixed, fixed !important;
    }
    .main {
        background: transparent !important;
    }
    .main .block-container {
        padding-top: 1.75rem;
    }
    [data-testid="stHeader"] {
        background: rgba(255,255,255,0.72) !important;
        backdrop-filter: blur(14px);
        border-bottom: 1px solid rgba(216,190,120,0.22);
    }
    #bg-canvas {
        display: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    #interactive-77-bg {
        display: none !important;
    }
    #pattern-hover-layer {
        position: fixed;
        inset: 0;
        z-index: 0;
        pointer-events: none;
        background: var(--brand-stage-bg) center top / cover no-repeat;
        opacity: 0.52;
        filter: saturate(2.05) brightness(1.03);
        mix-blend-mode: multiply;
        -webkit-mask-image: radial-gradient(190px circle at var(--mx) var(--my), rgba(0,0,0,0.96), rgba(0,0,0,0.52) 38%, transparent 72%);
        mask-image: radial-gradient(190px circle at var(--mx) var(--my), rgba(0,0,0,0.96), rgba(0,0,0,0.52) 38%, transparent 72%);
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(255,255,255,0.94), rgba(250,248,242,0.96)),
            var(--brand-stage-bg) !important;
        background-size: auto, 520px 292px !important;
        background-position: center top !important;
        border-right: 1px solid rgba(216,190,120,0.36);
        box-shadow: 18px 0 60px rgba(43,33,12,0.08);
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #202532;
    }

    .lux-alpha-hero {
        grid-template-columns: auto minmax(0, 1fr) auto;
        min-height: 154px;
        padding: 1.45rem 1.6rem;
        margin-bottom: 1.45rem;
        background:
            linear-gradient(110deg, rgba(255,255,255,0.96), rgba(255,255,255,0.82));
        background-size: auto;
        background-position: center;
        border: 1px solid rgba(216,190,120,0.46);
        border-radius: 18px;
        box-shadow: 0 22px 70px rgba(43,33,12,0.12);
    }
    .lux-alpha-hero::before {
        background:
            linear-gradient(90deg, rgba(255,255,255,0.50), rgba(255,255,255,0.84)),
            radial-gradient(circle at 92% 28%, rgba(232,87,139,0.12), transparent 18%),
            radial-gradient(circle at 78% 70%, rgba(46,167,160,0.11), transparent 24%);
        opacity: 1;
    }
    .lux-alpha-logo {
        width: 92px;
        height: 92px;
    }
    .lux-alpha-hero-brand {
        display: grid;
        place-items: center;
        min-width: 190px;
    }
    .lux-alpha-hero-badge {
        width: 190px;
        height: 190px;
        object-fit: contain;
        filter:
            drop-shadow(0 12px 26px rgba(216,164,65,0.16))
            drop-shadow(0 20px 42px rgba(74,144,217,0.10));
    }
    .lux-alpha-logo-img {
        width: 92px;
        height: 92px;
        object-fit: contain;
        filter:
            drop-shadow(0 10px 22px rgba(216,164,65,0.18))
            drop-shadow(0 16px 34px rgba(74,144,217,0.10));
    }
    .lux-alpha-medallion {
        width: 66px;
        height: 66px;
        object-fit: cover;
        border-radius: 50%;
        margin-left: -26px;
        margin-bottom: -2px;
        border: 1px solid rgba(216,190,120,0.54);
        box-shadow:
            0 8px 22px rgba(43,33,12,0.13),
            0 0 0 4px rgba(255,255,255,0.50);
    }
    .lux-alpha-kicker {
        color: #8F6A1F !important;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.22em;
    }
    .lux-alpha-title {
        color: #171923 !important;
        font-size: 2.1rem;
        font-weight: 760;
    }
    .lux-alpha-subtitle {
        color: #667085 !important;
        font-size: 0.95rem;
        max-width: 820px;
    }
    .lux-alpha-badge {
        background: rgba(255,255,255,0.80);
        border-color: rgba(216,190,120,0.42);
        box-shadow: 0 8px 22px rgba(43,33,12,0.07);
    }
    .lux-alpha-sidebar-brand {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.96), rgba(255,255,255,0.76)),
            var(--brand-stage-bg);
        background-size: auto, 420px 236px;
        border: 1px solid rgba(216,190,120,0.44);
        border-radius: 16px;
        box-shadow: 0 14px 42px rgba(43,33,12,0.10);
    }
    .lux-alpha-sidebar-brand-top {
        display: grid;
        place-items: center;
        min-height: 98px;
        margin-bottom: 0.55rem;
    }
    .lux-alpha-sidebar-medallion {
        width: min(100%, 222px);
        height: 104px;
        object-fit: contain;
        filter:
            drop-shadow(0 10px 24px rgba(216,164,65,0.16))
            drop-shadow(0 18px 34px rgba(74,144,217,0.09));
    }
    .lux-alpha-avatar {
        width: 54px;
        height: 54px;
        object-fit: cover;
        border-radius: 50%;
        border: 1px solid rgba(216,190,120,0.58);
        box-shadow: 0 8px 24px rgba(43,33,12,0.13);
    }
    .lux-alpha-sidebar-brand .lux-alpha-logo {
        width: 76px;
        height: 54px;
        object-fit: contain;
    }
    .lux-alpha-sidebar-title {
        font-size: 1.05rem;
        letter-spacing: 0;
    }
    .lux-alpha-sidebar-caption {
        color: #7A6170 !important;
    }
    .stButton > button {
        min-height: 2.7rem;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,252,244,0.92));
        border: 1px solid rgba(216,190,120,0.52);
        border-radius: 14px;
        color: #202532;
        font-weight: 700;
        box-shadow: 0 12px 30px rgba(43,33,12,0.10);
    }
    .stButton > button:hover {
        background:
            linear-gradient(90deg, rgba(232,87,139,0.10), rgba(74,144,217,0.10), rgba(125,203,109,0.10)),
            #FFFFFF;
        color: #8F6A1F;
        border-color: #D9A441;
        box-shadow: 0 16px 42px rgba(216,164,65,0.18);
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > div {
        min-height: 2.55rem;
        background: rgba(255,255,255,0.90);
        border: 1px solid rgba(216,190,120,0.36);
        border-radius: 12px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stDateInput > div > div > input:focus {
        border-color: #E8578B;
        box-shadow: 0 0 0 3px rgba(232,87,139,0.12);
    }

    [data-testid="stFileUploader"] {
        border-radius: 16px;
        border: 1.5px dashed rgba(216,190,120,0.64);
        background:
            linear-gradient(135deg, rgba(255,255,255,0.86), rgba(255,252,244,0.76)),
            radial-gradient(circle at 16% 16%, rgba(232,87,139,0.12), transparent 22%),
            radial-gradient(circle at 88% 30%, rgba(74,144,217,0.10), transparent 18%);
    }
    [data-testid="stPlotlyChart"],
    [data-testid="stTable"],
    [data-testid="stDataFrame"],
    [data-testid="stExpander"],
    [data-testid="stMetric"] {
        background:
            linear-gradient(145deg, rgba(255,255,255,0.95), rgba(255,255,255,0.82));
        border: 1px solid rgba(216,190,120,0.30);
        border-radius: 16px;
        box-shadow: var(--shadow-card);
        backdrop-filter: blur(10px);
    }
    [data-testid="stMetric"] {
        border-left-width: 5px;
    }
    [data-testid="stMetric"]:nth-child(6n+1) { border-left-color: #E8578B; }
    [data-testid="stMetric"]:nth-child(6n+2) { border-left-color: #4A90D9; }
    [data-testid="stMetric"]:nth-child(6n+3) { border-left-color: #7DCB6D; }
    [data-testid="stMetric"]:nth-child(6n+4) { border-left-color: #D9A441; }
    [data-testid="stMetric"]:nth-child(6n+5) { border-left-color: #7B61C9; }
    [data-testid="stMetric"]:nth-child(6n+0) { border-left-color: #2EA7A0; }

    .stTabs [data-baseweb="tab-list"] {
        border-bottom-color: rgba(216,190,120,0.34);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px 12px 0 0;
        color: #667085;
    }
    .stTabs [aria-selected="true"] {
        color: #202532;
        border-bottom: 3px solid #E8578B;
        background: linear-gradient(90deg, rgba(232,87,139,0.08), rgba(74,144,217,0.08));
    }
    [data-testid="stAlert"] {
        border-radius: 18px;
        border: 1px solid rgba(216,164,65,0.32);
        box-shadow: 0 14px 42px rgba(43,33,12,0.08);
        backdrop-filter: blur(10px);
    }
    [data-testid="stSuccess"] {
        min-height: 4.8rem;
        align-items: center;
        background:
            linear-gradient(90deg, rgba(125,203,109,0.18), rgba(46,167,160,0.12), rgba(255,255,255,0.72)) !important;
        background-size: auto !important;
        border: 1px solid rgba(125,203,109,0.28) !important;
        border-radius: 18px !important;
        box-shadow: 0 16px 48px rgba(46,167,160,0.10);
        color: #172033 !important;
    }
    [data-testid="stSuccess"] div,
    [data-testid="stSuccess"] p {
        color: #172033 !important;
        font-size: 1.02rem;
        font-weight: 650;
    }
    [data-testid="stInfo"] {
        background:
            linear-gradient(90deg, rgba(74,144,217,0.14), rgba(255,255,255,0.74)) !important;
        background-size: auto !important;
        border-color: rgba(74,144,217,0.26) !important;
        border-radius: 18px !important;
    }
    [data-testid="stWarning"] {
        background:
            linear-gradient(90deg, rgba(217,164,65,0.18), rgba(255,255,255,0.74)) !important;
        background-size: auto !important;
        border-color: rgba(217,164,65,0.34) !important;
        border-radius: 18px !important;
    }
    [data-testid="stError"] {
        background:
            linear-gradient(90deg, rgba(232,87,139,0.16), rgba(255,255,255,0.74)) !important;
        background-size: auto !important;
        border-color: rgba(232,87,139,0.30) !important;
        border-radius: 18px !important;
    }
    [data-testid="stPlotlyChart"] {
        position: relative;
        padding: 1.1rem;
        overflow: hidden;
    }
    [data-testid="stPlotlyChart"]::before {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        border-radius: 16px;
        background:
            linear-gradient(90deg, rgba(232,87,139,0.05), transparent 30%, rgba(74,144,217,0.05));
        background-size: auto;
        opacity: 0.18;
    }
    [data-testid="stPlotlyChart"] > div {
        position: relative;
        z-index: 1;
    }
    [data-testid="stTable"],
    [data-testid="stDataFrame"] {
        border-radius: 18px !important;
        border: 1px solid rgba(216,164,65,0.32) !important;
        box-shadow: 0 16px 46px rgba(43,33,12,0.08) !important;
        background:
            linear-gradient(145deg, rgba(255,255,255,0.96), rgba(255,255,255,0.82)) !important;
    }
    .stTable thead th,
    [data-testid="stDataFrame"] thead th {
        background: linear-gradient(90deg, rgba(232,87,139,0.08), rgba(74,144,217,0.08), rgba(125,203,109,0.06)) !important;
        color: #202532 !important;
        border-bottom: 1px solid rgba(216,164,65,0.22) !important;
    }
    .stTable tbody tr:nth-child(even),
    [data-testid="stDataFrame"] tbody tr:nth-child(even) {
        background: rgba(250,248,242,0.55) !important;
    }
    .stTable tbody td,
    [data-testid="stDataFrame"] tbody td {
        border-bottom: 1px solid rgba(216,164,65,0.12) !important;
    }
    #interactive-77-bg {
        position: fixed;
        inset: 0;
        z-index: 0;
        pointer-events: none;
        overflow: hidden;
        --logo-x: 0px;
        --logo-y: 0px;
        --logo-spin: 0deg;
        --logo-hue: 0deg;
        --logo-energy: 0;
    }
    .interactive-77-core {
        position: absolute;
        left: 58%;
        top: 54%;
        width: clamp(220px, 24vw, 430px);
        height: clamp(220px, 24vw, 430px);
        transform:
            translate(calc(-50% + var(--logo-x)), calc(-50% + var(--logo-y)))
            rotate(var(--logo-spin))
            scale(calc(1 + var(--logo-energy) * 0.035));
        opacity: calc(0.13 + var(--logo-energy) * 0.13);
        filter:
            hue-rotate(var(--logo-hue))
            saturate(calc(1.02 + var(--logo-energy) * 0.9))
            drop-shadow(0 26px 46px rgba(216,164,65,0.12));
        transition: opacity 180ms ease;
        mix-blend-mode: multiply;
    }
    .interactive-77-core .split-a {
        transform: translate(calc(var(--logo-energy) * -9px), calc(var(--logo-energy) * 5px));
        transform-origin: 45% 50%;
    }
    .interactive-77-core .split-b {
        transform: translate(calc(var(--logo-energy) * 9px), calc(var(--logo-energy) * -4px));
        transform-origin: 55% 50%;
    }
    .interactive-77-orbit {
        position: absolute;
        width: 46px;
        height: 46px;
        opacity: calc(0.16 + var(--logo-energy) * 0.18);
        filter: hue-rotate(var(--logo-hue)) saturate(1.2);
        transform:
            translate(
                calc(var(--ox) + var(--logo-x) * var(--move)),
                calc(var(--oy) + var(--logo-y) * var(--move))
            )
            rotate(calc(var(--logo-spin) * var(--spin)))
            scale(calc(1 + var(--logo-energy) * 0.08));
        mix-blend-mode: multiply;
    }
    .interactive-77-orbit.o1 { left: 44%; top: 38%; --ox: -80px; --oy: -44px; --move: -0.42; --spin: 2.2; color: #E8578B; }
    .interactive-77-orbit.o2 { left: 66%; top: 38%; --ox: 86px; --oy: -36px; --move: 0.34; --spin: -1.8; color: #4A90D9; }
    .interactive-77-orbit.o3 { left: 45%; top: 69%; --ox: -92px; --oy: 54px; --move: 0.28; --spin: -1.4; color: #7DCB6D; }
    .interactive-77-orbit.o4 { left: 67%; top: 68%; --ox: 86px; --oy: 48px; --move: -0.36; --spin: 1.6; color: #D9A441; }
    @media (max-width: 768px) {
        .interactive-77-core {
            left: 58%;
            top: 58%;
            width: 240px;
            height: 240px;
            opacity: calc(0.08 + var(--logo-energy) * 0.10);
        }
        .interactive-77-orbit { display: none; }
    }
    hr {
        background: linear-gradient(90deg, transparent, rgba(216,164,65,0.34), rgba(232,87,139,0.20), rgba(74,144,217,0.18), transparent);
    }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem; }
        .stPlotlyChart { padding: 0.5rem; margin: 0.5rem 0; }
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.2rem !important; }
        .lux-alpha-hero {
            grid-template-columns: 1fr;
            padding: 1rem;
        }
        .lux-alpha-badges {
            justify-content: flex-start;
            min-width: 0;
        }
        .lux-alpha-title { font-size: 1.55rem; }
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div id="pattern-hover-layer" aria-hidden="true"></div>
<script>
(function(){
  if (window.__pattern77HoverInstalled) return;
  window.__pattern77HoverInstalled = true;
  function update(e) {
    var p = e.touches && e.touches[0] ? e.touches[0] : e;
    document.documentElement.style.setProperty("--mx", p.clientX + "px");
    document.documentElement.style.setProperty("--my", p.clientY + "px");
  }
  window.addEventListener("mousemove", update, {passive:true});
  window.addEventListener("touchmove", update, {passive:true});
})();
</script>
""", unsafe_allow_html=True)

st.markdown("""
<div id="interactive-77-bg" aria-hidden="true">
  <svg class="interactive-77-core" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="interactive-frame" x1="42" y1="42" x2="470" y2="470" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#FFE9A6"/>
        <stop offset="0.45" stop-color="#C99A3A"/>
        <stop offset="1" stop-color="#8F6A1F"/>
      </linearGradient>
    </defs>
    <rect x="42" y="42" width="428" height="428" rx="72" fill="#FFFFFF" stroke="url(#interactive-frame)" stroke-width="7"/>
    <g fill="none" stroke-linecap="round" stroke-linejoin="round">
      <g class="split-a">
        <path d="M126 142H258L148 370" stroke="#E8578B" stroke-width="44"/>
        <path d="M126 142H258" stroke="#D9A441" stroke-width="44"/>
        <path d="M148 370L206 250" stroke="#7B61C9" stroke-width="44"/>
      </g>
      <g class="split-b">
        <path d="M250 142H382L272 370" stroke="#4A90D9" stroke-width="44"/>
        <path d="M250 142H382" stroke="#202532" stroke-width="44"/>
        <path d="M272 370L326 258" stroke="#7DCB6D" stroke-width="44"/>
      </g>
      <path d="M126 142H258L148 370" stroke="#FFFFFF" stroke-width="16"/>
      <path d="M250 142H382L272 370" stroke="#FFFFFF" stroke-width="16"/>
      <path d="M146 318C204 284 276 294 360 222" stroke="#2EA7A0" stroke-width="10"/>
    </g>
    <circle cx="126" cy="142" r="9" fill="#E8578B"/>
    <circle cx="258" cy="142" r="9" fill="#4A90D9"/>
    <circle cx="382" cy="142" r="9" fill="#7DCB6D"/>
    <circle cx="360" cy="222" r="9" fill="#F0985C"/>
    <path d="M416 96l9 20 20 9-20 9-9 20-9-20-20-9 20-9z" fill="#D9A441"/>
    <path d="M96 380l8 18 18 8-18 8-8 18-8-18-18-8 18-8z" fill="#7B61C9"/>
  </svg>
  <svg class="interactive-77-orbit o1" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
    <path d="M60 16c10 18 10 30 0 44-10-14-10-26 0-44Z" fill="currentColor"/>
    <path d="M104 60c-18 10-30 10-44 0 14-10 26-10 44 0Z" fill="currentColor"/>
    <path d="M60 104c-10-18-10-30 0-44 10 14 10 26 0 44Z" fill="currentColor"/>
    <path d="M16 60c18-10 30-10 44 0-14 10-26 10-44 0Z" fill="currentColor"/>
  </svg>
  <svg class="interactive-77-orbit o2" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
    <circle cx="35" cy="35" r="8" fill="currentColor"/><circle cx="85" cy="35" r="8" fill="currentColor"/><circle cx="85" cy="85" r="8" fill="currentColor"/><circle cx="35" cy="85" r="8" fill="currentColor"/>
  </svg>
  <svg class="interactive-77-orbit o3" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
    <rect x="48" y="48" width="24" height="24" rx="8" fill="none" stroke="currentColor" stroke-width="7" transform="rotate(45 60 60)"/>
    <circle cx="28" cy="60" r="7" fill="currentColor"/><circle cx="60" cy="28" r="7" fill="currentColor"/><circle cx="92" cy="60" r="7" fill="currentColor"/><circle cx="60" cy="92" r="7" fill="currentColor"/>
  </svg>
  <svg class="interactive-77-orbit o4" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
    <path d="M60 14l12 32 34 14-34 14-12 32-12-32-34-14 34-14z" fill="currentColor"/>
  </svg>
</div>
<script>
(function(){
  if (window.__interactive77Installed) return;
  window.__interactive77Installed = true;
  var root = document.getElementById("interactive-77-bg") || document.documentElement;
  if (root && window.getComputedStyle(root).display === "none") return;
  var targetX = 0, targetY = 0, x = 0, y = 0, energy = 0, hue = 0;
  function updateTarget(clientX, clientY) {
    var vw = window.innerWidth || 1;
    var vh = window.innerHeight || 1;
    var cx = vw * 0.58;
    var cy = vh * 0.54;
    var dx = clientX - cx;
    var dy = clientY - cy;
    var dist = Math.sqrt(dx * dx + dy * dy);
    var radius = Math.max(260, Math.min(vw, vh) * 0.42);
    var pull = Math.max(0, 1 - dist / radius);
    targetX = Math.max(-28, Math.min(28, dx * 0.045));
    targetY = Math.max(-24, Math.min(24, dy * 0.04));
    energy = pull;
    hue = (clientX / vw * 88) - 28;
  }
  window.addEventListener("mousemove", function(e){ updateTarget(e.clientX, e.clientY); }, {passive:true});
  window.addEventListener("touchmove", function(e){
    if (e.touches && e.touches[0]) updateTarget(e.touches[0].clientX, e.touches[0].clientY);
  }, {passive:true});
  function tick() {
    x += (targetX - x) * 0.08;
    y += (targetY - y) * 0.08;
    var spin = (x * 0.18) + (y * -0.12);
    root.style.setProperty("--logo-x", x.toFixed(2) + "px");
    root.style.setProperty("--logo-y", y.toFixed(2) + "px");
    root.style.setProperty("--logo-spin", spin.toFixed(2) + "deg");
    root.style.setProperty("--logo-hue", hue.toFixed(2) + "deg");
    root.style.setProperty("--logo-energy", energy.toFixed(3));
    requestAnimationFrame(tick);
  }
  tick();
})();
</script>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# Interactive Canvas 2D background · subtle ambient sphere
# Zero external dependencies — works in China
# ═══════════════════════════════════════════════
st.markdown("""
<canvas id="bg-canvas" style="position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:0;display:block;pointer-events:auto;"></canvas>
<script>
(function(){
    var c = document.getElementById('bg-canvas');
    if (!c || window.getComputedStyle(c).display === "none") return;
    var ctx = c.getContext('2d');
    var W, H, cx, cy, R;
    var t = 0;
    var mouse = {x: -9999, y: -9999, active: false};
    var mouseSmooth = {x: -9999, y: -9999, active: 0};

    /* ── Simplex 3D noise (compact) ── */
    var grad3 = [[1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],[1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],[0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]];
    var perm = new Uint8Array(512);
    var p = [151,160,137,91,90,15,131,13,201,95,96,53,194,233,7,225,140,36,103,30,69,142,8,99,37,240,21,10,23,190,6,148,247,120,234,75,0,26,197,62,94,252,219,203,117,35,11,32,57,177,33,88,237,149,56,87,174,20,125,136,171,168,68,175,74,165,71,134,139,48,27,166,77,146,158,231,83,111,229,122,60,211,133,230,220,105,92,41,55,46,245,40,244,102,143,54,65,25,63,161,1,216,80,73,209,76,132,187,208,89,18,169,200,196,135,130,116,188,159,86,164,100,109,198,173,186,3,64,52,217,226,250,124,123,5,202,38,147,118,126,255,82,85,212,207,206,59,227,47,16,58,17,182,189,28,42,223,183,170,213,119,248,152,2,44,154,163,70,221,153,101,155,167,43,172,9,129,22,39,253,19,98,108,110,79,113,224,232,178,185,112,104,218,246,97,228,251,34,242,193,238,210,144,12,191,179,162,241,81,51,145,235,249,14,239,107,49,192,214,31,181,199,106,157,184,84,204,176,115,121,50,45,127,4,150,254,138,236,205,93,222,114,67,29,24,72,243,141,128,195,78,66,215,61,156,180];
    for(var i=0;i<512;i++){perm[i]=p[i&255];}
    function dot3(g,x,y,z){return g[0]*x+g[1]*y+g[2]*z;}
    function snoise(x,y,z){
        var X=Math.floor(x)&255,Y=Math.floor(y)&255,Z=Math.floor(z)&255;
        x-=Math.floor(x);y-=Math.floor(y);z-=Math.floor(z);
        var u=x*x*x*(x*(x*6-15)+10),v=y*y*y*(y*(y*6-15)+10),w=z*z*z*(z*(z*6-15)+10);
        var A=perm[X]+Y,AA=perm[A]+Z,AB=perm[A+1]+Z;
        var B=perm[X+1]+Y,BA=perm[B]+Z,BB=perm[B+1]+Z;
        return (1-u)*(1-v)*(1-w)*dot3(grad3[perm[AA]%12],x,y,z)+
               (1-u)*(1-v)*w*dot3(grad3[perm[AB]%12],x,y,z-1)+
               (1-u)*v*(1-w)*dot3(grad3[perm[AA+1]%12],x,y-1,z)+
               (1-u)*v*w*dot3(grad3[perm[AB+1]%12],x,y-1,z-1)+
               u*(1-v)*(1-w)*dot3(grad3[perm[BA]%12],x-1,y,z)+
               u*(1-v)*w*dot3(grad3[perm[BB]%12],x-1,y,z-1)+
               u*v*(1-w)*dot3(grad3[perm[BA+1]%12],x-1,y-1,z)+
               u*v*w*dot3(grad3[perm[BB+1]%12],x-1,y-1,z-1);
    }

    /* ── HSL → RGB ── */
    function hsl(h,s,l){
        var a=s*Math.min(l,1-l);
        var f=function(n){var k=(n+h/30)%12;return l-a*Math.max(Math.min(k-3,9-k,1),-1);};
        return [Math.round(f(0)*255),Math.round(f(8)*255),Math.round(f(4)*255)];
    }

    /* ── Offscreen noise texture (256×256) ── */
    var texSize = 256;
    var offC = document.createElement('canvas');
    offC.width = offC.height = texSize;
    var offX = offC.getContext('2d');
    var imgData = offX.createImageData(texSize, texSize);
    for(var iy=0;iy<texSize;iy++){
        for(var ix=0;ix<texSize;ix++){
            var n = snoise(ix*0.04, iy*0.04, 0)*0.5+0.5;
            var v = Math.floor(n*255);
            var idx = (iy*texSize+ix)*4;
            imgData.data[idx]=imgData.data[idx+1]=imgData.data[idx+2]=v;
            imgData.data[idx+3]=255;
        }
    }
    offX.putImageData(imgData,0,0);

    function resize(){
        W = c.width = window.innerWidth;
        H = c.height = window.innerHeight;
        cx = W/2; cy = H/2;
        R = Math.min(W, H) * 0.32;
    }
    resize();
    window.addEventListener('resize', resize);

    /* ── Mouse / touch ── */
    function onMove(e){
        mouse.x = e.clientX; mouse.y = e.clientY; mouse.active = true;
    }
    function onLeave(){ mouse.active = false; }
    function onTouch(e){
        if(e.touches.length>0){mouse.x=e.touches[0].clientX;mouse.y=e.touches[0].clientY;mouse.active=true;}
    }
    function onTouchEnd(){ mouse.active = false; }
    window.addEventListener('mousemove', onMove, {passive:true});
    window.addEventListener('mouseleave', onLeave);
    window.addEventListener('touchmove', onTouch, {passive:true});
    window.addEventListener('touchend', onTouchEnd);

    /* ── Ray-sphere intersection ── */
    function raySphere(mx, my){
        var dx = (mx - cx) / R;
        var dy = (my - cy) / R;
        var d2 = dx*dx + dy*dy;
        if(d2 <= 1.0){
            var dz = Math.sqrt(1.0 - d2);
            return {x: dx, y: dy, z: dz, hit: true};
        }
        // Find closest point on sphere
        var dist = Math.sqrt(d2);
        return {x: dx/dist, y: dy/dist, z: 0, hit: false};
    }

    function render(ts){
        t = ts * 0.001;
        ctx.clearRect(0, 0, W, H);

        /* Smooth mouse */
        var mx = mouseSmooth.x + (mouse.x - mouseSmooth.x) * 0.12;
        var my = mouseSmooth.y + (mouse.y - mouseSmooth.y) * 0.12;
        var ma = mouseSmooth.active + ((mouse.active?1:0) - mouseSmooth.active) * 0.08;
        mouseSmooth.x = mx; mouseSmooth.y = my; mouseSmooth.active = ma;

        var hit = raySphere(mx, my);

        /* ── Draw sphere ── */
        ctx.save();
        /* Subtle radial glow behind sphere */
        var glowGrad = ctx.createRadialGradient(cx, cy, R*0.88, cx, cy, R*1.25);
        var baseHue = 215 + Math.sin(t*0.12)*8 + Math.cos(t*0.17)*6;
        var glowRGB = hsl(baseHue%360, 0.40, 0.62);
        glowGrad.addColorStop(0, 'rgba('+glowRGB[0]+','+glowRGB[1]+','+glowRGB[2]+',0.08)');
        glowGrad.addColorStop(0.5, 'rgba('+glowRGB[0]+','+glowRGB[1]+','+glowRGB[2]+',0.03)');
        glowGrad.addColorStop(1, 'rgba('+glowRGB[0]+','+glowRGB[1]+','+glowRGB[2]+',0)');
        ctx.fillStyle = glowGrad;
        ctx.beginPath(); ctx.arc(cx, cy, R*1.25, 0, Math.PI*2); ctx.fill();

        /* Sphere body: noise-textured warm gradient */
        ctx.save();
        ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI*2); ctx.clip();

        /* Base gradient */
        var baseGrad = ctx.createRadialGradient(cx-R*0.3, cy-R*0.45, R*0.05, cx, cy, R*1.05);
        var h0 = (215 + Math.sin(t*0.12)*8)%360;
        var h1 = (225 + Math.cos(t*0.17)*6)%360;
        var c0 = hsl(h0, 0.35, 0.75);
        var c1 = hsl(h1, 0.30, 0.62);
        baseGrad.addColorStop(0, 'rgb('+c0[0]+','+c0[1]+','+c0[2]+')');
        baseGrad.addColorStop(0.45, 'rgb('+Math.floor((c0[0]+c1[0])/2)+','+Math.floor((c0[1]+c1[1])/2)+','+Math.floor((c0[2]+c1[2])/2)+')');
        baseGrad.addColorStop(1, 'rgb('+c1[0]+','+c1[1]+','+c1[2]+')');
        ctx.fillStyle = baseGrad;
        ctx.fillRect(cx-R, cy-R, R*2, R*2);

        /* Noise texture overlay */
        ctx.globalAlpha = 0.08;
        var pat = ctx.createPattern(offC, 'repeat');
        var noiseScale = 1.8 + Math.sin(t*0.08)*0.3;
        ctx.save();
        ctx.translate(cx, cy);
        ctx.scale(noiseScale, noiseScale);
        ctx.fillStyle = pat;
        ctx.fillRect(-R, -R, R*2, R*2);
        ctx.restore();
        ctx.globalAlpha = 1.0;

        /* ── Mouse turbulence region ── */
        if(ma > 0.01 && hit.hit){
            var ix = hit.x * R + cx;
            var iy = hit.y * R + cy;
            var turbGrad = ctx.createRadialGradient(ix, iy, 0, ix, iy, R*0.42*ma);
            var rainbowHue = ((t*25 + hit.x*150 + hit.y*100)%360 + 360)%360;
            var r0 = hsl(rainbowHue, 0.70, 0.80);
            var r1 = hsl((rainbowHue+25)%360, 0.65, 0.74);
            var r2 = hsl((rainbowHue-15)%360, 0.60, 0.70);
            turbGrad.addColorStop(0, 'rgba('+r0[0]+','+r0[1]+','+r0[2]+','+(0.40*ma)+')');
            turbGrad.addColorStop(0.35, 'rgba('+r1[0]+','+r1[1]+','+r1[2]+','+(0.22*ma)+')');
            turbGrad.addColorStop(0.7, 'rgba('+r2[0]+','+r2[1]+','+r2[2]+','+(0.08*ma)+')');
            turbGrad.addColorStop(1, 'rgba('+r2[0]+','+r2[1]+','+r2[2]+',0)');
            ctx.fillStyle = turbGrad;
            ctx.fillRect(cx-R, cy-R, R*2, R*2);

            /* Rainbow ring ripples */
            for(var ri=0;ri<3;ri++){
                var rad = (0.12+ri*0.18) * R;
                var alpha = (0.45-ri*0.14) * ma;
                ctx.strokeStyle = 'rgba('+r0[0]+','+r0[1]+','+r0[2]+','+alpha+')';
                ctx.lineWidth = 2.5-ri*0.6;
                ctx.beginPath(); ctx.arc(ix, iy, rad, 0, Math.PI*2); ctx.stroke();
            }
        }

        /* ── Surface detail: subtle radial gradients for 3D depth ── */
        /* Highlight */
        var hlGrad = ctx.createRadialGradient(cx-R*0.35, cy-R*0.45, R*0.02, cx, cy, R);
        hlGrad.addColorStop(0, 'rgba(255,255,255,0.14)');
        hlGrad.addColorStop(0.3, 'rgba(255,255,255,0.04)');
        hlGrad.addColorStop(1, 'rgba(0,0,0,0.08)');
        ctx.fillStyle = hlGrad;
        ctx.fillRect(cx-R, cy-R, R*2, R*2);

        /* Fresnel rim */
        var rimGrad = ctx.createRadialGradient(cx, cy, R*0.82, cx, cy, R*1.02);
        rimGrad.addColorStop(0, 'rgba(0,0,0,0)');
        rimGrad.addColorStop(0.7, 'rgba(0,0,0,0)');
        rimGrad.addColorStop(1, 'rgba(0,0,0,0.12)');
        ctx.fillStyle = rimGrad;
        ctx.fillRect(cx-R, cy-R, R*2, R*2);

        ctx.restore(); /* End sphere clip */

        /* ── Idle noise speckle particles (reduced) ── */
        for(var pi=0;pi<10;pi++){
            var angle = (pi/18)*Math.PI*2 + t*0.15;
            var dist = R*(0.92+0.08*Math.sin(pi*7.3+t*1.4));
            var sx = cx + Math.cos(angle)*dist;
            var sy = cy + Math.sin(angle)*dist*0.7;
            var speckleAlpha = 0.08+0.06*Math.sin(pi*3.7+t*2.1);
            var spHue = (h0+pi*30+Math.sin(t*0.5+pi)*12)%360;
            var spRGB = hsl(spHue, 0.35, 0.72);
            ctx.fillStyle = 'rgba('+spRGB[0]+','+spRGB[1]+','+spRGB[2]+','+speckleAlpha+')';
            ctx.beginPath(); ctx.arc(sx, sy, 2.2, 0, Math.PI*2); ctx.fill();
        }

        ctx.restore(); /* End main save */

        requestAnimationFrame(render);
    }
    requestAnimationFrame(render);
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
        
        # 如果是美股，跳过efinance（只支持A股）
        if not (stock_code.startswith('6') or stock_code.startswith('5') or 
                stock_code.startswith('0') or stock_code.startswith('3') or
                stock_code.startswith('8') or stock_code.startswith('4')):
            st.write("检测到非A股代码，跳过efinance")
        else:
            # 尝试使用efinance获取数据
            try:
                def fetch_efinance():
                    return ef.stock.get_quote_history(stock_code)
                
                data = retry_with_backoff(fetch_efinance)
                
                data['日期'] = pd.to_datetime(data['日期'])
                data = data[(data['日期'] >= start_date) & (data['日期'] <= end_date)]
                data.set_index('日期', inplace=True)
                
                data.rename(columns={
                    '收盘': 'close',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume'
                }, inplace=True)
                
                st.write(f"✓ 使用 efinance 获取到 {len(data)} 条数据")
                return data
            except Exception as e:
                st.write(f"✗ efinance 获取数据时出错: {str(e)[:100]}...")
        
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
        
        # 尝试使用 efinance
        try:
            def fetch_efinance():
                return ef.stock.get_quote_history('000001')
            
            data = retry_with_backoff(fetch_efinance)
            
            data['日期'] = pd.to_datetime(data['日期'])
            data = data[(data['日期'] >= start_date) & (data['日期'] <= end_date)]
            data.set_index('日期', inplace=True)
            
            data.rename(columns={'收盘': 'close'}, inplace=True)
            
            data['benchmark_return'] = data['close'].pct_change()
            data['cumulative_benchmark'] = (1 + data['benchmark_return']).cumprod()
            
            st.write(f"✓ 使用 efinance 获取到 {len(data)} 条上证指数数据")
            return data
        except Exception as e:
            st.write(f"✗ efinance 获取上证指数数据时出错: {str(e)[:100]}...")
        
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
        
        # 如果是A股，尝试使用 efinance
        if stock_code.startswith('6') or stock_code.startswith('5') or \
           stock_code.startswith('0') or stock_code.startswith('3') or \
           stock_code.startswith('8') or stock_code.startswith('4'):
            try:
                def fetch_efinance():
                    return ef.stock.get_quote_history(stock_code, klt=1)
                
                stock_info = retry_with_backoff(fetch_efinance)
                if not stock_info.empty:
                    stock_name = stock_info.get('股票名称', [''])[0] if '股票名称' in stock_info.columns else ""
                    if stock_name:
                        st.write(f"股票名称: {stock_name}")
                    return stock_name
            except Exception as e:
                st.write(f"✗ efinance 获取股票名称时出错: {str(e)[:100]}...")
        
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
    
    # Signal colors
    green = FALL_GREEN
    red = RISE_RED

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
        name='MA20', line=dict(color=SIGNAL_ORANGE, width=1.5),
    ))

    if show_ma5:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA5'], mode='lines',
            name='MA5', line=dict(color=SIGNAL_BLUE, width=1),
        ))
    if show_ma10:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA10'], mode='lines',
            name='MA10', line=dict(color=FALL_GREEN, width=1),
        ))
    if show_ma50:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA50'], mode='lines',
            name='MA50', line=dict(color=SIGNAL_PURPLE, width=1),
        ))
    if show_ma100:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA100'], mode='lines',
            name='MA100', line=dict(color='#A1A1A6', width=1),
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
            name='加仓', marker=dict(color=SIGNAL_ORANGE, size=10, symbol='cross',
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
            name='买回', marker=dict(color=FALL_GREEN, size=10, symbol='circle',
            line=dict(width=1, color='white')),
        ))
    if not stop_loss_signals.empty:
        fig.add_trace(go.Scatter(
            x=stop_loss_signals.index, y=stop_loss_signals['close'], mode='markers',
            name='止损', marker=dict(color=RISE_RED, size=10, symbol='x',
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

    data['color'] = [RISE_RED if close > open else FALL_GREEN for close, open in zip(data['close'], data['open'])]
    data['line_color'] = [RISE_RED_DARK if close > open else FALL_GREEN_DARK for close, open in zip(data['close'], data['open'])]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data.index, y=data['volume'], name='成交量',
        marker=dict(color=data['color'], opacity=0.34, line=dict(color=data['line_color'], width=0.35)),
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data['VMA5'], mode='lines', name='VMA5',
        line=dict(color=SIGNAL_BLUE, width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data['VMA60'], mode='lines', name='VMA60',
        line=dict(color=SIGNAL_ORANGE, width=1.5),
    ))

    fig.update_layout(**template)
    fig.update_layout(
        title='成交量和均量线',
        height=400,
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
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
        name='仓位 (%)', line=dict(color=FALL_GREEN, width=1.5), yaxis='y1',
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=(data['cumulative_return'] - 1) * 100, mode='lines',
        name='策略收益率 (%)', line=dict(color=SIGNAL_BLUE, width=1.5), yaxis='y2',
    ))

    fig.update_layout(**template)
    fig.update_layout(
        title='仓位和策略收益率',
        height=400,
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
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
            line=dict(color=SIGNAL_BLUE, width=1.5)
        ))

        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Signal'],
            mode='lines',
            name='Signal',
            line=dict(color=SIGNAL_ORANGE, width=1.5)
        ))

    # 添加RSI（如果存在）
    if has_rsi:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['RSI'],
            mode='lines',
            name='RSI',
            line=dict(color=SIGNAL_PURPLE, width=1.5),
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
            activecolor=RISE_RED,
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
        fig.add_hline(y=70, line_dash="dash", line_color=RISE_RED, name="超买线")
        fig.add_hline(y=30, line_dash="dash", line_color=FALL_GREEN, name="超卖线")
    
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
        line=dict(color=SIGNAL_BLUE, width=1.5)
    ), row=1, col=1)
    
    # 添加MA25（如果存在）
    if 'MA25' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MA25'],
            mode='lines',
            name='MA25',
            line=dict(color=SIGNAL_ORANGE, width=1.5)
        ), row=1, col=1)
    
    # 添加买卖信号标记
    if not buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=buy_signals.index,
            y=buy_signals['close'],
            mode='markers',
            name='买入',
            marker=dict(color=FALL_GREEN, size=10, symbol='triangle-up', line=dict(width=2, color='white'))
        ), row=1, col=1)

    if not add_signals.empty:
        fig.add_trace(go.Scatter(
            x=add_signals.index,
            y=add_signals['close'],
            mode='markers',
            name='加仓',
            marker=dict(color=SIGNAL_ORANGE, size=10, symbol='cross', line=dict(width=2, color='white'))
        ), row=1, col=1)

    if not sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=sell_signals.index,
            y=sell_signals['close'],
            mode='markers',
            name='卖出',
            marker=dict(color=RISE_RED, size=10, symbol='triangle-down', line=dict(width=2, color='white'))
        ), row=1, col=1)

    if not buyback_signals.empty:
        fig.add_trace(go.Scatter(
            x=buyback_signals.index,
            y=buyback_signals['close'],
            mode='markers',
            name='买回',
            marker=dict(color=FALL_GREEN, size=10, symbol='circle', line=dict(width=2, color='white'))
        ), row=1, col=1)

    if not stop_loss_signals.empty:
        fig.add_trace(go.Scatter(
            x=stop_loss_signals.index,
            y=stop_loss_signals['close'],
            mode='markers',
            name='止损',
            marker=dict(color=RISE_RED, size=10, symbol='x', line=dict(width=2, color='white'))
        ), row=1, col=1)
    
    # 第二行：成交量和均量线
    # 计算均量线
    data['VMA5'] = data['volume'].rolling(window=5).mean()
    data['VMA60'] = data['volume'].rolling(window=60).mean()
    
    # 计算涨跌颜色
    data['color'] = [RISE_RED if close > open else FALL_GREEN for close, open in zip(data['close'], data['open'])]
    
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
        line=dict(color=SIGNAL_BLUE, width=1.5)
    ), row=2, col=1)
    
    # 添加VMA60
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['VMA60'],
        mode='lines',
        name='VMA60',
        line=dict(color=SIGNAL_ORANGE, width=1.5)
    ), row=2, col=1)
    
    # 第三行：仓位和策略收益率
    # 添加仓位
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['position'] * 100,
        mode='lines',
        name='仓位 (%)',
        line=dict(color=FALL_GREEN, width=1.5)
    ), row=3, col=1)
    
    # 添加策略收益率
    fig.add_trace(go.Scatter(
        x=data.index,
        y=(data['cumulative_return'] - 1) * 100,
        mode='lines',
        name='策略收益率 (%)',
        line=dict(color=SIGNAL_BLUE, width=1.5)
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
        # 保持阅读型图表，避免滚轮和拖拽影响页面翻页
        dragmode=False,
        # 添加工具栏
        modebar=dict(
            orientation="h",
            bgcolor=colors['hover_bg'],
            activecolor=RISE_RED,
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
        line=dict(width=2, color=SIGNAL_BLUE),
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
        line=dict(width=1.5, color=FALL_GREEN),
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
    colors = [RISE_RED, SIGNAL_BLUE, SIGNAL_LIME, SIGNAL_GOLD, SIGNAL_PURPLE, FALL_GREEN]
    
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

    bar_colors = [RISE_RED if x > 0 else FALL_GREEN for x in monthly_returns['strategy_return']]
    bar_line_colors = [RISE_RED_DARK if x > 0 else FALL_GREEN_DARK for x in monthly_returns['strategy_return']]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_returns['month'], y=monthly_returns['strategy_return'] * 100,
        name='月度收益率', marker=dict(color=bar_colors, opacity=0.82, line=dict(color=bar_line_colors, width=0.8)),
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
            color = [RISE_RED, SIGNAL_BLUE, SIGNAL_LIME, SIGNAL_GOLD, SIGNAL_PURPLE, FALL_GREEN][i % 6]
            
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
        # 保持阅读型图表，避免拖拽影响页面翻页
        dragmode=False,
        # 添加工具栏
        modebar=dict(
            orientation="h",
            bgcolor=colors['hover_bg'],
            activecolor=RISE_RED,
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
    st.markdown(
        f"""<section class="lux-alpha-hero">
<div class="lux-alpha-hero-brand">{HERO_ALPHA_BADGE_HTML}</div>
<div>
<div class="lux-alpha-kicker">77 MULTICOLOR STRATEGY ATELIER</div>
<h1 class="lux-alpha-title">77股票交易策略回测工作台</h1>
<p class="lux-alpha-subtitle">以多策略回测、风险曲线与交易信号为核心，构建清晰、克制、可复盘的策略判断流程。</p>
</div>
<div class="lux-alpha-badges">
<span class="lux-alpha-badge"><span class="lux-alpha-dot" style="background:#E8578B"></span>收益复盘</span>
<span class="lux-alpha-badge"><span class="lux-alpha-dot" style="background:#4A90D9"></span>策略对比</span>
<span class="lux-alpha-badge"><span class="lux-alpha-dot" style="background:#7DCB6D"></span>风险曲线</span>
</div>
</section>""",
        unsafe_allow_html=True,
    )
    
    # 侧边栏输入参数
    with st.sidebar:
        st.markdown(
            f"""<div class="lux-alpha-sidebar-brand">
<div class="lux-alpha-sidebar-brand-top">{SIDEBAR_MEDALLION_HTML}</div>
<p class="lux-alpha-sidebar-title">77 参数工作台</p>
<p class="lux-alpha-sidebar-caption">Stock · Risk · Signal · Discipline</p>
</div>""",
            unsafe_allow_html=True,
        )
        
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
            "启动回测",
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
                    blocked_imports = ("import efinance", "from efinance")
                    if any(blocked in strategy_code for blocked in blocked_imports):
                        st.error(
                            f"策略 {i+1} 包含 efinance 依赖。Streamlit Cloud 环境不支持 efinance，"
                            "请删除策略文件里的 import efinance / from efinance 后重新上传。"
                        )
                        continue
                    # 创建独立的命名空间
                    strategy_namespace = {}
                    # 执行上传的策略代码
                    try:
                        exec(strategy_code, strategy_namespace)
                    except Exception as e:
                        st.error(f"策略 {i+1} 加载失败：{str(e)[:160]}")
                        continue
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
                        render_chart(benchmark_fig, key=f"benchmark_{stock_code}_{strategy_name}")
                
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
                            render_chart(benchmark_fig, key=f"benchmark_compare_{stock_code}_{strategy_name}")
                            
                            # 生成月度收益率分析图
                            monthly_fig = generate_monthly_returns_chart(strategy_data)
                            render_chart(monthly_fig, key=f"monthly_returns_{stock_code}_{strategy_name}")
                    
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
                        render_chart(net_value_compare_fig, key=f"net_value_compare_{stock_code}")

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
                        render_chart(drawdown_compare_fig, key=f"drawdown_compare_{stock_code}")
                    
                    # 策略性能指标雷达图对比
                    st.subheader("策略性能指标雷达图对比")
                    radar_colors_s = get_color_scheme()
                    apple_colors = [SIGNAL_BLUE, RISE_RED, FALL_GREEN, SIGNAL_ORANGE, FALL_GREEN, SIGNAL_PURPLE]
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
                        render_chart(radar_compare_fig, key=f"radar_compare_{stock_code}")
                        
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
                                render_chart(fig_3d, key=f"3d_strategy_compare_{stock_code}")
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
                        mp_colors = [SIGNAL_BLUE, RISE_RED, FALL_GREEN, SIGNAL_ORANGE, FALL_GREEN, SIGNAL_PURPLE]
                        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
                        
                        # 第一个子图：净值对比
                        ax1 = axes[0, 0]
                        for i, strategy_name in enumerate(strategies):
                            if strategy_name in all_data[stock_code]:
                                strategy_data = all_data[stock_code][strategy_name]
                                ax1.plot(strategy_data.index, strategy_data['cumulative_return'], 
                                         label=strategy_name, color=mp_colors[i % len(mp_colors)], linewidth=2)
                        ax1.axhline(y=1, linestyle='--', color='#A79B83')
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
                    render_agent_analysis_card()
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
                        kline_fig.update_layout(
                            height=680,
                            dragmode="zoom",
                            title=f"{stock_display} - {strategy_name} 价格走势和交易信号（可滚轮缩放 / 框选放大 / 双击复位）",
                        )
                        render_chart(kline_fig, key=f"kline_{stock_code}_{strategy_name}", config=KLINE_RENDER_CONFIG)
                        
                        # 成交量和均量线图表
                        st.subheader(f"{strategy_name} - 成交量和均量线")
                        volume_fig = generate_volume_chart(strategy_data, time_frame)
                        render_chart(volume_fig, key=f"volume_{stock_code}_{strategy_name}")
                        
                        # 仓位和策略收益率图表
                        st.subheader(f"{strategy_name} - 仓位和策略收益率")
                        position_fig = generate_position_chart(strategy_data, time_frame)
                        render_chart(position_fig, key=f"position_{stock_code}_{strategy_name}")
                        

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
                            line=dict(color=RISE_RED, width=1.5),
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
                        render_chart(drawdown_fig, key=f"drawdown_{stock_code}_{strategy_name}")
                        
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
                            line=dict(color=SIGNAL_BLUE, width=2),
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
                        render_chart(radar_fig, key=f"radar_{stock_code}_{strategy_name}")
                        
                        # 月度收益率
                        st.subheader(f"{strategy_name} - 月度收益率")
                        monthly_data = resample_monthly(strategy_data, {'strategy_return': 'sum'})
                        monthly_data['month'] = monthly_data.index.strftime('%Y-%m')
                        m_colors_inline = get_color_scheme()
                        m_tpl = get_plotly_template(m_colors_inline)
                        bar_colors_m = [RISE_RED if x > 0 else FALL_GREEN for x in monthly_data['strategy_return']]
                        bar_line_colors_m = [RISE_RED_DARK if x > 0 else FALL_GREEN_DARK for x in monthly_data['strategy_return']]
                        monthly_fig = go.Figure()
                        monthly_fig.add_trace(go.Bar(
                            x=monthly_data['month'], y=monthly_data['strategy_return'] * 100,
                            name='月度收益率', marker=dict(color=bar_colors_m, opacity=0.82, line=dict(color=bar_line_colors_m, width=0.8)),
                        ))
                        monthly_fig.add_hline(y=0, line_dash="dot", line_color=m_colors_inline['text_secondary'], opacity=0.4)
                        monthly_fig.update_layout(**m_tpl)
                        monthly_fig.update_layout(
                            title=f"{strategy_name} - 月度收益率分布", height=380,
                            xaxis=dict(tickangle=0), yaxis=dict(title='收益率 (%)'),
                        )
                        render_chart(monthly_fig, key=f"monthly_{stock_code}_{strategy_name}")

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
                            name='交易次数', marker=dict(color=SIGNAL_BLUE, opacity=0.76, line=dict(color="#2E6FA9", width=0.8)),
                        ))
                        trade_freq_fig.update_layout(**tf_tpl)
                        trade_freq_fig.update_layout(
                            title=f"{strategy_name} - 月度交易频率分布", height=380,
                            xaxis=dict(tickangle=0), yaxis=dict(title='交易次数'),
                        )
                        render_chart(trade_freq_fig, key=f"trade_freq_{stock_code}_{strategy_name}")
                    
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
                        ax1.plot(strategy_data.index, strategy_data['close'], color=SIGNAL_BLUE, label='收盘价', linewidth=1)
                        # 检查MA25列是否存在
                        if 'MA25' in strategy_data.columns:
                            ax1.plot(strategy_data.index, strategy_data['MA25'], color=SIGNAL_ORANGE, label='MA25', linewidth=1.5)
                        
                        # 标记买卖信号
                        buy_signals = strategy_data[strategy_data.get('signal', 0) == 1]
                        add_signals = strategy_data[strategy_data.get('signal', 0) == 2]
                        sell_signals = strategy_data[strategy_data.get('signal', 0) == -1]
                        buyback_signals = strategy_data[strategy_data.get('signal', 0) == 3]
                        stop_loss_signals = strategy_data[strategy_data.get('signal', 0) == 4]
                        
                        if not buy_signals.empty:
                            ax1.scatter(buy_signals.index, buy_signals['close'], color=FALL_GREEN, marker='^', s=50, label='买入')
                        if not add_signals.empty:
                            ax1.scatter(add_signals.index, add_signals['close'], color=SIGNAL_ORANGE, marker='x', s=50, label='加仓')
                        if not sell_signals.empty:
                            ax1.scatter(sell_signals.index, sell_signals['close'], color=RISE_RED, marker='v', s=50, label='卖出')
                        if not buyback_signals.empty:
                            ax1.scatter(buyback_signals.index, buyback_signals['close'], color=FALL_GREEN, marker='o', s=50, label='买回')
                        if not stop_loss_signals.empty:
                            ax1.scatter(stop_loss_signals.index, stop_loss_signals['close'], color=RISE_RED, marker='x', s=50, label='止损')
                        
                        ax1.set_title(f'{stock_display} - {strategy_name} 价格走势和交易信号')
                        ax1.set_ylabel('价格')
                        ax1.legend(loc='upper left')
                        ax1.grid(True, alpha=0.3)
                        
                        # 设置日期格式
                        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 2. 策略净值曲线
                        ax2.plot(strategy_data.index, strategy_data['cumulative_return'], color=SIGNAL_BLUE, label='策略净值', linewidth=2)
                        ax2.axhline(y=1, linestyle='--', color='#A79B83', label='基准线')
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
                        strategy_data['color'] = [RISE_RED if close > open else FALL_GREEN for close, open in zip(strategy_data['close'], strategy_data['open'])]
                        
                        # 绘制成交量柱体
                        for i, (date, row) in enumerate(strategy_data.iterrows()):
                            ax3.bar(date, row['volume'], color=row['color'], alpha=0.3)
                        
                        # 绘制均量线
                        ax3.plot(strategy_data.index, strategy_data['VMA5'], color=SIGNAL_BLUE, label='VMA5', linewidth=1)
                        ax3.plot(strategy_data.index, strategy_data['VMA60'], color=SIGNAL_ORANGE, label='VMA60', linewidth=1)
                        
                        ax3.set_title('成交量和均量线')
                        ax3.set_ylabel('成交量')
                        ax3.legend(loc='upper left')
                        ax3.grid(True, alpha=0.3)
                        
                        # 设置日期格式
                        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 4. 回撤曲线
                        ax4.plot(strategy_data.index, strategy_data['drawdown'] * 100, color=RISE_RED, label='回撤 (%)', linewidth=2)
                        ax4.fill_between(strategy_data.index, 0, strategy_data['drawdown'] * 100, color=RISE_RED, alpha=0.15)
                        ax4.set_title(f'{strategy_name} - 策略回撤情况')
                        ax4.set_ylabel('回撤 (%)')
                        ax4.legend(loc='upper left')
                        ax4.grid(True, alpha=0.3)
                        
                        # 设置日期格式
                        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
                        
                        # 5. 仓位和策略收益率
                        ax5.plot(strategy_data.index, strategy_data['position'] * 100, color=FALL_GREEN, label='仓位 (%)', linewidth=1)
                        ax5.set_ylabel('仓位 (%)', color=FALL_GREEN)
                        ax5.tick_params(axis='y', labelcolor=FALL_GREEN)
                        ax5.set_ylim(0, 100)

                        # 创建第二个y轴用于策略收益率
                        ax5_right = ax5.twinx()
                        ax5_right.plot(strategy_data.index, (strategy_data['cumulative_return'] - 1) * 100, color=SIGNAL_BLUE, label='策略收益率 (%)', linewidth=1)
                        ax5_right.set_ylabel('策略收益率 (%)', color=SIGNAL_BLUE)
                        ax5_right.tick_params(axis='y', labelcolor=SIGNAL_BLUE)
                        
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
                            
                            colors = [RISE_RED if x > 0 else FALL_GREEN for x in monthly_data['strategy_return']]
                            edge_colors = [RISE_RED_DARK if x > 0 else FALL_GREEN_DARK for x in monthly_data['strategy_return']]
                            ax7.bar(monthly_data['month'], monthly_data['strategy_return'] * 100, color=colors, edgecolor=edge_colors, linewidth=0.7, label='月度收益率')
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
                            
                            ax8.bar(monthly_trades['month'], monthly_trades['signal'], color=SIGNAL_BLUE, edgecolor='#2E6FA9', linewidth=0.7, label='交易次数')
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
                    # 保持阅读型图表，避免滚轮和拖拽影响页面翻页
                    dragmode=False,
                    # 添加工具栏
                    modebar=dict(
                        orientation="h",
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        activecolor=RISE_RED
                    )
                )
                
                render_chart(comparison_fig)
                
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
                        
                        strategy_compare_fig.add_hline(y=1, line_dash="dash", line_color="#A79B83", name="基准线")
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
                        render_chart(strategy_compare_fig)

                        strategy_scatter_rows = []
                        for strategy_name in strategies:
                            if strategy_name in all_data[stock_code]:
                                matched_result = next(
                                    (
                                        result for result in all_results
                                        if result['stock_code'] == stock_code and result['strategy'] == strategy_name
                                    ),
                                    None,
                                )
                                if matched_result:
                                    metrics = matched_result['metrics']
                                    strategy_scatter_rows.append({
                                        "strategy": strategy_name,
                                        "total_return": metrics['total_return'],
                                        "annual_return": metrics['annual_return'],
                                        "max_drawdown": metrics['max_drawdown'],
                                        "sharpe_ratio": metrics['sharpe_ratio'],
                                        "win_rate": metrics['win_rate'],
                                        "total_trades": metrics['total_trades'],
                                    })

                        strategy_metric_scatter = generate_strategy_metric_scatter(
                            strategy_scatter_rows,
                            stock_display,
                        )
                        if strategy_metric_scatter is not None:
                            st.subheader(f"{stock_display} 策略指标象限气泡图")
                            st.caption("横轴衡量收益能力，纵轴衡量风险控制能力；气泡越大代表夏普比率越高，颜色越绿代表综合评分越强。")
                            render_chart(
                                strategy_metric_scatter,
                                key=f"strategy_metric_scatter_{stock_code}",
                            )
                        
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
            render_completion_brand_assets()
            
        except Exception as e:
            st.error(f"回测过程中出现错误: {str(e)}")

if __name__ == '__main__':
    main()


