import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
import os
import re

# ============================================================================
# 1. CONFIGURACIÓN E IDENTIDAD VISUAL
# ============================================================================
st.set_page_config(page_title="Seguimiento Operativo | Carmencita", page_icon="🐝", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FAFAFA; }
    [data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #2E59A7; }
    h1 { color: #2E59A7 !important; font-weight: bold !important; }
    h2, h3 { color: #F1C40F !important; font-weight: bold !important; }
    div[data-testid="stMetric"] { background-color: #111111; border: 1px solid #2E59A7; border-radius: 10px; padding: 15px; }
    .footer-style { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #111111; color: #FAFAFA; text-align: center; padding: 10px; border-top: 2px solid #2E59A7; font-size: 12px; z-index: 999; }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# 2. SEGURIDAD
# ============================================================================
def safe_image(file_path, width=200):
    if os.path.exists(file_path): st.image(file_path, width=width)
    else: st.caption(f"[{file_path} no cargado]")

def check_password():
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            safe_image("logo.png", width=200)
            st.title("Acceso Inteligencia Carmencita")
            pwd = st.text_input("Clave de Seguridad", type="password")
            if st.button("Ingresar"):
                if pwd == st.secrets.get("APP_PASSWORD", "Felicidad2011"):
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# ============================================================================
# 3. MOTOR DE DATOS (FILTRADO DE FILAS VACÍAS)
# ============================================================================
def normalize_text(text):
    if pd.isna(text) or text == "": return "S/I"
    text = str(text).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def clean_val(val):
    if pd.isna(val): return ""
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
        if header_idx is None: return None
        df = pd.read_csv(url, skiprows=header_idx)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except: return None

@st.cache_data(ttl=60)
def load_data():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url).group(1)
        url_p = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=PLANIFICACION"
        url_r = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=REAL"
        
        df_p = process_sheet_auto(url_p)
        df_r = process_sheet_auto(url_r)
        if df_p is None or df_r is None: return pd.DataFrame()

        def get_col_exact(df, key):
            for c in df.columns:
                if key == c: return c
            for c in df.columns:
                if key in c: return c
            return None

        # Columnas de Identidad
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

                # --- FILTRO CRÍTICO: SOLO GUARDAR SI HAY ACTIVIDAD ---
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
# 4. FUNCIONES DE VISUALIZACIÓN
# ============================================================================
def crear_tema_plotly():
    """Configuración visual oscura para gráficos Plotly"""
    return dict(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(17,17,17,1)',
        font=dict(color='#FAFAFA', family='Arial, sans-serif'),
        title_font=dict(color='#F1C40F', size=16),
        legend=dict(bgcolor='rgba(17,17,17,0.8)', bordercolor='#2E59A7', borderwidth=1)
    )

def grafico_cumplimiento_por_programa(df):
    """Gráfico de barras horizontales: Meta vs Real por Programa"""
    if df.empty:
        return None
    
    agrupado = df.groupby('ASESORÍA').agg({'META': 'sum', 'REAL': 'sum'}).reset_index()
    agrupado['CUMPLIMIENTO %'] = (agrupado['REAL'] / agrupado['META'] * 100).fillna(0).round(1)
    agrupado = agrupado.sort_values('REAL', ascending=True)
    
    fig = go.Figure()
    
    # Barras de Meta (transparentes con borde)
    fig.add_trace(go.Bar(
        y=agrupado['ASESORÍA'],
        x=agrupado['META'],
        name='Meta Planificada',
        orientation='h',
        marker=dict(color='rgba(46, 89, 167, 0.3)', line=dict(color='#2E59A7', width=2)),
        text=agrupado['META'],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>Meta: %{x}<extra></extra>'
    ))
    
    # Barras de Real (sólidas)
    fig.add_trace(go.Bar(
        y=agrupado['ASESORÍA'],
        x=agrupado['REAL'],
        name='Real Ejecutado',
        orientation='h',
        marker=dict(color='#F1C40F', line=dict(color='#F1C40F', width=1)),
        text=agrupado['REAL'],
        textposition='outside',
        textfont=dict(color='#F1C40F', size=12),
        hovertemplate='<b>%{y}</b><br>Real: %{x}<br>Cumplimiento: %{customdata}%<extra></extra>',
        customdata=agrupado['CUMPLIMIENTO %']
    ))
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title="Avance por Programa de Asesoría",
        xaxis_title="N° de Visitas",
        yaxis_title="",
        barmode='overlay',
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7'),
        yaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7')
    )
    
    return fig

def grafico_evolucion_mensual(df):
    """Gráfico de líneas: Evolución de visitas a lo largo del año"""
    if df.empty:
        return None
    
    meses_orden = ['MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
    evolucion = df.groupby('MES').agg({'META': 'sum', 'REAL': 'sum'}).reindex(meses_orden).fillna(0)
    
    fig = go.Figure()
    
    # Línea de Meta
    fig.add_trace(go.Scatter(
        x=evolucion.index,
        y=evolucion['META'],
        mode='lines+markers+text',
        name='Meta Acumulada',
        line=dict(color='#2E59A7', width=3, dash='dash'),
        marker=dict(size=8, symbol='diamond'),
        text=evolucion['META'].astype(int),
        textposition='top center',
        hovertemplate='%{x}<br>Meta: %{y}<extra></extra>'
    ))
    
    # Línea de Real
    fig.add_trace(go.Scatter(
        x=evolucion.index,
        y=evolucion['REAL'],
        mode='lines+markers+text',
        name='Real Ejecutado',
        line=dict(color='#F1C40F', width=4),
        marker=dict(size=10, symbol='circle'),
        text=evolucion['REAL'].astype(int),
        textposition='bottom center',
        textfont=dict(color='#F1C40F'),
        fill='tozeroy',
        fillcolor='rgba(241, 196, 15, 0.1)',
        hovertemplate='%{x}<br>Real: %{y}<extra></extra>'
    ))
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title="Evolución Mensual de Visitas",
        xaxis_title="Mes",
        yaxis_title="N° de Visitas",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7'),
        yaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', zerolinecolor='#2E59A7'),
        hovermode='x unified'
    )
    
    return fig

def grafico_distribucion_estados(df):
    """Gráfico circular: Distribución de estados (Cumplida/Pendiente/Extra-plan)"""
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
        textfont=dict(size=14, color='#FAFAFA'),
        hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
    )])
    
    # Agregar total en el centro
    total = estados.sum()
    fig.add_annotation(
        text=f"<b>{total}</b><br>Total",
        showarrow=False,
        font=dict(size=20, color='#F1C40F'),
        x=0.5, y=0.5
    )
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title="Distribución de Estados",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True
    )
    
    return fig

def grafico_top_asesores(df):
    """Gráfico de barras verticales: Top asesores por cumplimiento"""
    if df.empty:
        return None
    
    asesores = df.groupby('ASESOR').agg({
        'META': 'sum',
        'REAL': 'sum',
        'RUT': 'nunique'
    }).reset_index()
    asesores['CUMPLIMIENTO %'] = (asesores['REAL'] / asesores['META'] * 100).fillna(0).round(1)
    asesores = asesores.sort_values('CUMPLIMIENTO %', ascending=False).head(10)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=asesores['ASESOR'],
        y=asesores['CUMPLIMIENTO %'],
        marker=dict(
            color=asesores['CUMPLIMIENTO %'],
            colorscale=[[0, '#b71c1c'], [50, '#f57f17'], [100, '#1b5e20']],
            line=dict(color='#2E59A7', width=1)
        ),
        text=asesores['CUMPLIMIENTO %'].astype(str) + '%',
        textposition='outside',
        textfont=dict(color='#FAFAFA'),
        hovertemplate='<b>%{x}</b><br>Cumplimiento: %{y}%<br>Real: %{customdata[0]} / Meta: %{customdata[1]}<br>Apicultores: %{customdata[2]}<extra></extra>',
        customdata=asesores[['REAL', 'META', 'RUT']].values
    ))
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title="Top Asesores - % de Cumplimiento",
        xaxis_title="",
        yaxis_title="% Cumplimiento",
        height=400,
        margin=dict(l=20, r=20, t=50, b=100),
        xaxis=dict(tickangle=-45, gridcolor='rgba(46, 89, 167, 0.2)'),
        yaxis=dict(gridcolor='rgba(46, 89, 167, 0.2)', range=[0, 110]),
        showlegend=False
    )
    
    return fig

def grafico_mapa_calor_comuna(df):
    """Heatmap de actividad por Comuna y Mes"""
    if df.empty or sel_mes != "AÑO COMPLETO":
        return None
    
    pivot = df.pivot_table(
        values='REAL',
        index='COMUNA',
        columns='MES',
        aggfunc='sum',
        fill_value=0
    )
    
    # Ordenar meses correctamente
    meses_orden = ['MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
    pivot = pivot.reindex(columns=[m for m in meses_orden if m in pivot.columns])
    
    fig = px.imshow(
        pivot,
        labels=dict(x="Mes", y="Comuna", color="Visitas Realizadas"),
        color_continuous_scale=['#111111', '#2E59A7', '#F1C40F'],
        aspect='auto'
    )
    
    fig.update_traces(
        hovertemplate='<b>%{y}</b><br>Mes: %{x}<br>Visitas: %{z}<extra></extra>',
        text=pivot.values,
        texttemplate="%{z}",
        textfont=dict(size=10, color='#FAFAFA')
    )
    
    tema = crear_tema_plotly()
    fig.update_layout(
        **tema,
        title="Mapa de Calor: Visitas por Comuna y Mes",
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(side='bottom'),
        coloraxis_colorbar=dict(
            title="Visitas",
            tickfont=dict(color='#FAFAFA'),
            titlefont=dict(color='#FAFAFA')
        )
    )
    
    return fig

# ============================================================================
# 5. DASHBOARD
# ============================================================================
def main():
    if not check_password(): return
    df = load_data()
    
    with st.sidebar:
        safe_image("perfil.jpg", width=120)
        if st.button("🔄 Sincronizar Datos"):
            st.cache_data.clear()
            st.rerun()
        st.header("Filtros")
        global sel_mes
        sel_mes = st.selectbox("Mes de Seguimiento", ["AÑO COMPLETO", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"])
        if not df.empty:
            sel_comuna = st.multiselect("Filtrar Comuna", sorted(df['COMUNA'].unique()))
            sel_prog = st.multiselect("Filtrar Asesoría", sorted(df['ASESORÍA'].unique()))
            sel_ase = st.multiselect("Filtrar Asesor", sorted(df['ASESOR'].unique()))
        else:
            sel_comuna, sel_prog, sel_ase = [], [], []

    # Filtros Dinámicos
    df_f = df.copy()
    if sel_mes != "AÑO COMPLETO":
        df_f = df_f[df_f['MES'] == sel_mes]
    
    if sel_comuna: df_f = df_f[df_f['COMUNA'].isin(sel_comuna)]
    if sel_prog: df_f = df_f[df_f['ASESORÍA'].isin(sel_prog)]
    if sel_ase: df_f = df_f[df_f['ASESOR'].isin(sel_ase)]

    st.title("📊 Seguimiento Operativo 2026")
    
    # --- KPIs CORREGIDOS ---
    c1, c2, c3, c4 = st.columns(4)
    m_t, r_t = df_f['META'].sum(), df_f['REAL'].sum()
    c1.metric("% CUMPLIMIENTO", f"{(r_t/m_t*100 if m_t > 0 else 0):.1f}%")
    c2.metric("REALIZADAS", int(r_t))
    c3.metric("BRECHA PENDIENTE", int(max(0, m_t - r_t)))
    # Cuenta RUTs únicos para no inflar la cantidad de personas
    c4.metric("USUARIOS ATENDIDOS", df_f['RUT'].nunique())

    # --- SECCIÓN DE GRÁFICOS ---
    if not df_f.empty:
        st.markdown("---")
        st.subheader("📈 Análisis Visual del Avance")
        
        # Fila 1: Gráficos principales
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            fig_prog = grafico_cumplimiento_por_programa(df_f)
            if fig_prog:
                st.plotly_chart(fig_prog, use_container_width=True, key="prog_chart")
        
        with col_graf2:
            fig_evo = grafico_evolucion_mensual(df_f)
            if fig_evo:
                st.plotly_chart(fig_evo, use_container_width=True, key="evo_chart")
        
        # Fila 2: Gráficos secundarios
        col_graf3, col_graf4 = st.columns(2)
        
        with col_graf3:
            fig_estado = grafico_distribucion_estados(df_f)
            if fig_estado:
                st.plotly_chart(fig_estado, use_container_width=True, key="estado_chart")
        
        with col_graf4:
            fig_asesores = grafico_top_asesores(df_f)
            if fig_asesores:
                st.plotly_chart(fig_asesores, use_container_width=True, key="asesores_chart")
        
        # Fila 3: Mapa de calor (solo si es año completo y hay datos)
        if sel_mes == "AÑO COMPLETO" and not sel_comuna:
            fig_heatmap = grafico_mapa_calor_comuna(df_f)
            if fig_heatmap:
                st.plotly_chart(fig_heatmap, use_container_width=True, key="heatmap_chart")
    
    st.markdown("---")

    # --- TABLA OPERATIVA ACOTRADA ---
    st.subheader(f"📋 Registro de Visitas: {sel_mes}")
    
    if not df_f.empty:
        cols_mostrar = ['USUARIO', 'RUT', 'TELEFONO', 'COMUNA', 'SECTOR', 'ASESORÍA', 'ASESOR', 'MES', 'ESTADO', 'EMOJI', 'COLOR']
        df_tabla = df_f[cols_mostrar]
        
        def style_rows(row):
            return [row['COLOR']] * len(row)

        st.dataframe(
            df_tabla.style.apply(style_rows, axis=1),
            column_config={"COLOR": None}, 
            use_container_width=True,
            height=600
        )
    else:
        st.info(f"No hay actividad registrada para los filtros seleccionados.")

    st.markdown('<div class="footer-style"><b>Claudio Ruiz O.</b> | Senior Developer | © 2026 Carmencita</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
