import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
import os
import re

# ============================================================================
# 1. CONFIGURACIÓN E IDENTIDAD VISUAL (OPTIMIZADO MÓVIL)
# ============================================================================
st.set_page_config(
    page_title="Seguimiento Operativo | Carmencita", 
    page_icon="🐝", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Responsive Mejorado
st.markdown("""
    <style>
    * { box-sizing: border-box; }
    
    .stApp { background-color: #000000; color: #FAFAFA; }
    
    [data-testid="stSidebar"] { 
        background-color: #111111 !important; 
        border-right: 1px solid #2E59A7; 
    }
    
    h1 { 
        color: #2E59A7 !important; 
        font-weight: bold !important;
        font-size: clamp(1.5rem, 5vw, 2.5rem) !important;
    }
    
    h2 { 
        color: #F1C40F !important; 
        font-weight: bold !important;
        font-size: clamp(1.2rem, 4vw, 1.8rem) !important;
    }
    
    h3 { 
        color: #F1C40F !important; 
        font-weight: bold !important;
        font-size: clamp(1rem, 3.5vw, 1.4rem) !important;
    }
    
    div[data-testid="stMetric"] { 
        background-color: #111111; 
        border: 1px solid #2E59A7; 
        border-radius: 10px; 
        padding: 10px;
    }
    
    @media (max-width: 640px) {
        div[data-testid="stMetric"] { padding: 8px; }
        div[data-testid="stMetric"] label { font-size: 0.75rem !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    }
    
    .stButton > button {
        width: 100%;
        background-color: #2E59A7;
        color: #FAFAFA;
        border: none;
        padding: 12px;
        border-radius: 8px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        background-color: #F1C40F;
        color: #000;
    }
    
    .logo-container {
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
        padding: 10px;
    }
    
    @media (max-width: 480px) {
        .logo-container { max-width: 250px; }
    }
    
    .footer-container {
        background: linear-gradient(90deg, #111111 0%, #1a1a1a 100%);
        color: #FAFAFA;
        border-top: 3px solid #2E59A7;
        padding: 20px 15px;
        margin-top: 30px;
    }
    
    .footer-content {
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
        text-align: center;
    }
    
    @media (min-width: 640px) {
        .footer-content {
            flex-direction: row;
            justify-content: center;
            text-align: left;
            gap: 30px;
        }
    }
    
    .footer-info {
        font-size: clamp(0.75rem, 2.5vw, 0.9rem);
        line-height: 1.6;
    }
    
    .footer-info .nombre {
        color: #F1C40F;
        font-weight: bold;
        font-size: clamp(0.9rem, 3vw, 1.1rem);
    }
    
    .footer-info .cargo { color: #2E59A7; font-weight: bold; }
    .footer-info a { color: #F1C40F; text-decoration: none; }
    .footer-info a:hover { text-decoration: underline; }
    
    .footer-perfil {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        border: 3px solid #2E59A7;
        object-fit: cover;
    }
    
    @media (min-width: 640px) {
        .footer-perfil { width: 100px; height: 100px; }
    }
    
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    @media (min-width: 768px) {
        .block-container {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    }
    
    @media (max-width: 640px) {
        [data-testid="column"] {
            width: 100% !important;
            flex: 0 0 100% !important;
            margin-bottom: 10px;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# 2. SEGURIDAD
# ============================================================================
def safe_image(file_path, width=200):
    if os.path.exists(file_path): 
        st.image(file_path, width=width)
        return True
    else: 
        st.caption(f"[{file_path} no cargado]")
        return False

def check_password():
    if "password_correct" not in st.session_state: 
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            safe_image("logo.png", width=280)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; font-size: 1.5rem;'>Acceso Registro de Visitas Carmencita</h1>", unsafe_allow_html=True)
            pwd = st.text_input("Clave de Seguridad", type="password", placeholder="Ingrese contraseña")
            if st.button("Ingresar", use_container_width=True):
                if pwd == st.secrets.get("APP_PASSWORD", "Felicidad2011"):
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: 
                    st.error("❌ Clave incorrecta")
        return False
    return True

# ============================================================================
# 3. MOTOR DE DATOS
# ============================================================================
def normalize_text(text):
    if pd.isna(text) or text == "": 
        return "S/I"
    text = str(text).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def clean_val(val):
    if pd.isna(val): 
        return ""
    return str(val).replace(".", "").replace("-", "").strip().upper()

def process_sheet_auto(url):
    try:
        df_raw = pd.read_csv(url, header=None, nrows=25)
        header_idx = None
        for i, row in df_raw.iterrows():
            row_str = " ".join(row.astype(str).tolist()).upper()
            if "RUT" in row_str and "NOMBRE" in row_str:
                header_idx = i
                break
        if header_idx is None: 
            return None
        df = pd.read_csv(url, skiprows=header_idx)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except: 
        return None

@st.cache_data(ttl=60)
def load_data():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url).group(1)
        url_p = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=PLANIFICACION"
        url_r = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=REAL"
        
        df_p = process_sheet_auto(url_p)
        df_r = process_sheet_auto(url_r)
        if df_p is None or df_r is None: 
            return pd.DataFrame()

        def get_col_exact(df, key):
            for c in df.columns:
                if key == c: 
                    return c
            for c in df.columns:
                if key in c: 
                    return c
            return None

        col_rut_p, col_rut_r = get_col_exact(df_p, "RUT"), get_col_exact(df_r, "RUT")
        col_nom = get_col_exact(df_p, "NOMBRE")
        col_tel = get_col_exact(df_p, "TELEFONO")
        col_com = get_col_exact(df_p, "COMUNA")
        col_sec = get_col_exact(df_p, "SECTOR")
        col_prog = get_col_exact(df_p, "ASESORÍA")
        col_ase = get_col_exact(df_p, "ASESOR")

        df_p = df_p[pd.to_numeric(df_p.iloc[:, 0], errors='coerce').notnull()]
        df_r = df_r[pd.to_numeric(df_r.iloc[:, 0], errors='coerce').notnull()]

        meses = ['MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
        consolidado = []

        for _, row in df_p.iterrows():
            rut_val = clean_val(row[col_rut_p])
            row_real = df_r[df_r[col_rut_r].apply(clean_val) == rut_val]
            
            for mes in meses:
                col_m_p, col_m_r = get_col_exact(df_p, mes), get_col_exact(df_r, mes)
                meta = pd.to_numeric(row.get(col_m_p, 0), errors='coerce') if col_m_p else 0
                real = 0
                if not row_real.empty and col_m_r:
                    real = pd.to_numeric(row_real.iloc[0].get(col_m_r, 0), errors='coerce')
                
                meta = 0 if pd.isna(meta) else int(meta)
                real = 0 if pd.isna(real) else int(real)

                if meta >= 1 or real >= 1:
                    if meta >= 1 and real >= 1: 
                        est, emo, color = "CUMPLIDA", "✅", "background-color: #1b5e20"
                    elif meta >= 1 and real == 0: 
                        est, emo, color = "PENDIENTE", "❌", "background-color: #b71c1c"
                    elif meta == 0 and real >= 1: 
                        est, emo, color = "EXTRA-PLAN", "⚠️", "background-color: #f57f17"
                    
                    consolidado.append({
                        'USUARIO': normalize_text(row.get(col_nom, 'SIN NOMBRE')),
                        'RUT': rut_val,
                        'TELEFONO': str(row.get(col_tel, 'S/I')),
                        'COMUNA': normalize_text(row.get(col_com, 'S/I')),
                        'SECTOR': normalize_text(row.get(col_sec, 'S/I')),
                        'ASESORÍA': normalize_text(row.get(col_prog, 'S/I')),
                        'ASESOR': normalize_text(row.get(col_ase, 'S/I')),
                        'MES': mes,
                        'META': meta, 'REAL': real,
                        'ESTADO': est, 'EMOJI': emo, 'COLOR': color
                    })
        return pd.DataFrame(consolidado)
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# ============================================================================
# 4. FUNCIONES DE VISUALIZACIÓN (CORREGIDAS)
# ============================================================================
def crear_tema_plotly():
    """Configuración visual oscura base para gráficos Plotly"""
    return dict(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(17,17,17,1)',
        font=dict(color='#FAFAFA', family='Arial, sans-serif', size=10),
        title_font=dict(color='#F1C40F', size=14),
        margin=dict(l=10, r=10, t=40, b=10)
    )

def grafico_cumplimiento_por_programa(df):
    if df.empty:
        return None
    
    agrupado = df.groupby('ASESORÍA').agg({'META': 'sum', 'REAL': 'sum'}).reset_index()
    agrupado['CUMPLIMIENTO %'] = (agrupado['REAL'] / agrupado['META'] * 100).fillna(0).round(1)
    agrupado = agrupado.sort_values('REAL', ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=agrupado['ASESORÍA'],
        x=agrupado['META'],
        name='Meta Planificada',
        orientation='h',
        marker=dict(color='rgba(46, 89, 167, 0.3)', line=dict(color='#2E59A7', width=2)),
        text=agrupado['META'],
        textposition='inside',
        textfont=dict(size=9),
        hovertemplate='<b>%{y}</b><br>Meta: %{x}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        y=agrupado['ASESORÍA'],
        x=agrupado['REAL'],
        name='Real Ejecutado',
        orientation='h',
        marker=dict(color='#F1C40F', line=dict(color='#F1C40F', width=1)),
        text=agrupado['REAL'],
        textposition='outside',
        textfont=dict(color='#F1C40F', size=10),
        hovertemplate='<b>%{y}</b><br>Real: %{x}<br>Cumplimiento: %{customdata}%<extra></extra>',
        customdata=agrupado['CUMPLIMIENTO %']
    ))
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title=dict(text="Avance por Programa", font=dict(size=14)),
        xaxis_title="N° Visitas",
        yaxis_title="",
        barmode='overlay',
        height=350,
        legend=dict(
            bgcolor='rgba(17,17,17,0.8)', 
            bordercolor='#2E59A7', 
            borderwidth=1,
            font=dict(size=9)
        ),
        xaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7', tickfont=dict(size=9)),
        yaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7', tickfont=dict(size=9))
    )
    
    return fig

def grafico_evolucion_mensual(df):
    if df.empty:
        return None
    
    meses_orden = ['MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
    evolucion = df.groupby('MES').agg({'META': 'sum', 'REAL': 'sum'}).reindex(meses_orden).fillna(0)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=evolucion.index,
        y=evolucion['META'],
        mode='lines+markers+text',
        name='Meta',
        line=dict(color='#2E59A7', width=2, dash='dash'),
        marker=dict(size=6, symbol='diamond'),
        text=evolucion['META'].astype(int),
        textposition='top center',
        textfont=dict(size=8),
        hovertemplate='%{x}<br>Meta: %{y}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=evolucion.index,
        y=evolucion['REAL'],
        mode='lines+markers+text',
        name='Real',
        line=dict(color='#F1C40F', width=3),
        marker=dict(size=8, symbol='circle'),
        text=evolucion['REAL'].astype(int),
        textposition='bottom center',
        textfont=dict(color='#F1C40F', size=9),
        fill='tozeroy',
        fillcolor='rgba(241, 196, 15, 0.1)',
        hovertemplate='%{x}<br>Real: %{y}<extra></extra>'
    ))
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title=dict(text="Evolución Mensual", font=dict(size=14)),
        xaxis_title="Mes",
        yaxis_title="Visitas",
        height=350,
        legend=dict(
            bgcolor='rgba(17,17,17,0.8)', 
            bordercolor='#2E59A7', 
            borderwidth=1,
            font=dict(size=9)
        ),
        xaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7', tickfont=dict(size=9)),
        yaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7', tickfont=dict(size=9)),
        hovermode='x unified'
    )
    
    return fig

def grafico_distribucion_estados(df):
    """Gráfico circular: Distribución de estados (CORREGIDO)"""
    if df.empty:
        return None
    
    estados = df['ESTADO'].value_counts()
    colores = {'CUMPLIDA': '#1b5e20', 'PENDIENTE': '#b71c1c', 'EXTRA-PLAN': '#f57f17'}
    
    fig = go.Figure(data=[go.Pie(
        labels=estados.index,
        values=estados.values,
        hole=0.6,
        marker=dict(
            colors=[colores.get(e, '#2E59A7') for e in estados.index],
            line=dict(color='#000000', width=2)
        ),
        textinfo='label+percent',
        textfont=dict(size=11, color='#FAFAFA'),
        hovertemplate='<b>%{label}</b><br>Cant: %{value}<br>%{percent}<extra></extra>'
    )])
    
    total = estados.sum()
    fig.add_annotation(
        text=f"<b>{total}</b><br>Total",
        showarrow=False,
        font=dict(size=16, color='#F1C40F'),
        x=0.5, y=0.5
    )
    
    # CORRECCIÓN: No usar **tema aquí, definir layout manualmente para evitar conflicto con legend
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(17,17,17,1)',
        font=dict(color='#FAFAFA', family='Arial, sans-serif', size=10),
        title=dict(text="Distribución Estados", font=dict(size=14, color='#F1C40F')),
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=True,
        legend=dict(
            bgcolor='rgba(17,17,17,0.8)', 
            bordercolor='#2E59A7', 
            borderwidth=1,
            font=dict(size=9)
        )
    )
    
    return fig

def grafico_top_asesores(df):
    if df.empty:
        return None
    
    asesores = df.groupby('ASESOR').agg({
        'META': 'sum',
        'REAL': 'sum',
        'RUT': 'nunique'
    }).reset_index()
    asesores['CUMPLIMIENTO %'] = (asesores['REAL'] / asesores['META'] * 100).fillna(0).round(1)
    asesores = asesores.sort_values('CUMPLIMIENTO %', ascending=False).head(8)
    
    def get_color(pct):
        if pct >= 80: return '#1b5e20'
        elif pct >= 50: return '#f57f17'
        else: return '#b71c1c'
    
    asesores['COLOR'] = asesores['CUMPLIMIENTO %'].apply(get_color)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=asesores['ASESOR'],
        y=asesores['CUMPLIMIENTO %'],
        marker=dict(color=asesores['COLOR'], line=dict(color='#2E59A7', width=1)),
        text=asesores['CUMPLIMIENTO %'].astype(str) + '%',
        textposition='outside',
        textfont=dict(color='#FAFAFA', size=9),
        hovertemplate='<b>%{x}</b><br>%{y}%<br>Real: %{customdata[0]}/Meta: %{customdata[1]}<extra></extra>',
        customdata=asesores[['REAL', 'META']].values
    ))
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title=dict(text="Top Asesores %", font=dict(size=14)),
        xaxis_title="",
        yaxis_title="% Cumplimiento",
        height=350,
        showlegend=False,
        xaxis=dict(tickangle=-45, tickfont=dict(size=8), gridcolor='rgba(46, 89, 167, 0.2)'),
        yaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', range=[0, 110], tickfont=dict(size=9))
    )
    
    return fig

def grafico_mapa_calor_comuna(df):
    if df.empty:
        return None
    
    pivot = df.pivot_table(values='REAL', index='COMUNA', columns='MES', aggfunc='sum', fill_value=0)
    
    if pivot.empty:
        return None
    
    meses_orden = ['MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
    pivot = pivot.reindex(columns=[m for m in meses_orden if m in pivot.columns])
    
    if pivot.empty or len(pivot.columns) == 0:
        return None
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=list(pivot.columns),
        y=list(pivot.index),
        colorscale=[[0, '#111111'], [0.5, '#2E59A7'], [1, '#F1C40F']],
        showscale=True,
        text=pivot.values,
        texttemplate="%{text}",
        textfont={"size": 9, "color": "white"},
        hovertemplate='<b>%{y}</b><br>%{x}: %{z} visitas<extra></extra>'
    ))
    
    fig.update_traces(
        colorbar=dict(
            title=dict(text="Visitas", font=dict(color='#FAFAFA', size=10)),
            tickfont=dict(color='#FAFAFA', size=9),
            bgcolor='rgba(17,17,17,0.8)',
            bordercolor='#2E59A7',
            borderwidth=1,
            thickness=15,
            len=0.5
        )
    )
    
    fig.update_layout(
        title=dict(text="Mapa Calor: Comuna/Mes", font=dict(size=14, color='#F1C40F')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(17,17,17,1)',
        font=dict(color='#FAFAFA', family='Arial, sans-serif', size=10),
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(side='bottom', tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9))
    )
    
    return fig

# ============================================================================
# 5. COMPONENTES UI
# ============================================================================
def render_logo():
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.markdown("""
                <div style="text-align: center; padding: 15px; border: 2px dashed #2E59A7; border-radius: 10px; margin: 10px 0;">
                    <h2 style="color: #2E59A7; margin: 0; font-size: 1.5rem;">🐝 CARMENCITA</h2>
                    <p style="color: #F1C40F; margin: 5px 0 0 0; font-size: 0.9rem;">Sistema de Seguimiento</p>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def render_footer():
    perfil_html = ""
    if os.path.exists("perfil.jpg"):
        import base64
        with open("perfil.jpg", "rb") as f:
            img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode()
        perfil_html = f'<img src="data:image/jpeg;base64,{img_b64}" class="footer-perfil" alt="Perfil">'
    else:
        perfil_html = '<div style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid #2E59A7; background: #2E59A7; display: flex; align-items: center; justify-content: center; font-size: 30px; margin: 0 auto;">👤</div>'
    
    footer_html = f"""
    <div class="footer-container">
        <div class="footer-content">
            <div class="footer-info">
                <span class="nombre">CLAUDIO RUIZ O.</span> | <span class="cargo">Gerente Regional Sur</span> | CARMENCITA export<br>
                Ingeniero Comercial / MBA / Diplomado Estrategia UC<br>
                <b>T:</b> <a href="tel:+56752323539">+56 75 232 3539</a> | <b>M:</b> <a href="tel:+56996091936">+56 9 9609 1936</a><br>
                <b>E:</b> <a href="mailto:claudioruiz@carmencita.cl">claudioruiz@carmencita.cl</a><br>
                <b>Web:</b> <a href="https://www.carmencita.cl" target="_blank">carmencita.cl</a>
            </div>
            <div>{perfil_html}</div>
        </div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

# ============================================================================
# 6. DASHBOARD
# ============================================================================
def main():
    if not check_password(): 
        return
    
    render_logo()
    df = load_data()
    
    with st.sidebar:
        st.markdown("---")
        if st.button("🔄 Sincronizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.header("Filtros")
        sel_mes = st.selectbox("Mes", ["AÑO COMPLETO", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"])
        
        if not df.empty:
            with st.expander("Filtros Avanzados", expanded=False):
                sel_comuna = st.multiselect("Comuna", sorted(df['COMUNA'].unique()), max_selections=3)
                sel_prog = st.multiselect("Asesoría", sorted(df['ASESORÍA'].unique()), max_selections=3)
                sel_ase = st.multiselect("Asesor", sorted(df['ASESOR'].unique()), max_selections=3)
        else:
            sel_comuna, sel_prog, sel_ase = [], [], []

    # Filtros
    df_f = df.copy()
    if sel_mes != "AÑO COMPLETO":
        df_f = df_f[df_f['MES'] == sel_mes]
    if sel_comuna: 
        df_f = df_f[df_f['COMUNA'].isin(sel_comuna)]
    if sel_prog: 
        df_f = df_f[df_f['ASESORÍA'].isin(sel_prog)]
    if sel_ase: 
        df_f = df_f[df_f['ASESOR'].isin(sel_ase)]

    st.title("📊 Seguimiento Operativo 2026")
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    m_t, r_t = df_f['META'].sum(), df_f['REAL'].sum()
    
    with c1:
        st.metric("% CUMPLIMIENTO", f"{(r_t/m_t*100 if m_t > 0 else 0):.1f}%")
    with c2:
        st.metric("REALIZADAS", int(r_t))
    with c3:
        st.metric("PENDIENTES", int(max(0, m_t - r_t)))
    with c4:
        st.metric("USUARIOS", df_f['RUT'].nunique())

    # Gráficos
    if not df_f.empty:
        st.markdown("---")
        st.subheader("📈 Análisis Visual")
        
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            fig_prog = grafico_cumplimiento_por_programa(df_f)
            if fig_prog:
                st.plotly_chart(fig_prog, use_container_width=True, config={'displayModeBar': False}, key="prog_chart")
        with col_graf2:
            fig_evo = grafico_evolucion_mensual(df_f)
            if fig_evo:
                st.plotly_chart(fig_evo, use_container_width=True, config={'displayModeBar': False}, key="evo_chart")
        
        col_graf3, col_graf4 = st.columns(2)
        with col_graf3:
            fig_estado = grafico_distribucion_estados(df_f)
            if fig_estado:
                st.plotly_chart(fig_estado, use_container_width=True, config={'displayModeBar': False}, key="estado_chart")
        with col_graf4:
            fig_asesores = grafico_top_asesores(df_f)
            if fig_asesores:
                st.plotly_chart(fig_asesores, use_container_width=True, config={'displayModeBar': False}, key="asesores_chart")
        
        if sel_mes == "AÑO COMPLETO" and not sel_comuna:
            fig_heatmap = grafico_mapa_calor_comuna(df_f)
            if fig_heatmap:
                st.plotly_chart(fig_heatmap, use_container_width=True, config={'displayModeBar': False}, key="heatmap_chart")
    
    st.markdown("---")
    st.subheader(f"📋 Registro: {sel_mes}")
    
    if not df_f.empty:
        cols_mostrar = ['USUARIO', 'RUT', 'TELEFONO', 'COMUNA', 'SECTOR', 'ASESORÍA', 'ASESOR', 'MES', 'ESTADO', 'EMOJI', 'COLOR']
        df_tabla = df_f[cols_mostrar]
        
        def style_rows(row):
            return [row['COLOR']] * len(row)

        st.dataframe(
            df_tabla.style.apply(style_rows, axis=1),
            column_config={"COLOR": None}, 
            use_container_width=True,
            height=400,
            hide_index=True
        )
    else:
        st.info("No hay actividad registrada para los filtros seleccionados.")

    render_footer()

if __name__ == "__main__":
    main()
