import pandas as pd
import smtplib
import os
import re
import unicodedata
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.image import MimeImage
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio

# CONFIGURACIÓN
EMAIL_DESTINO = "ruizalonso804@gmail.com"
MESES = ['MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']

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

def load_data_from_sheets():
    """Carga datos desde Google Sheets"""
    try:
        # Intentar obtener desde secrets de Streamlit o variables de entorno
        try:
            import streamlit as st
            sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        except:
            sheet_url = os.environ.get("SHEET_URL")
        
        if not sheet_url:
            raise ValueError("No se encontró URL del sheet")
        
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

        col_rut_p = get_col_exact(df_p, "RUT")
        col_rut_r = get_col_exact(df_r, "RUT")
        col_nom = get_col_exact(df_p, "NOMBRE")
        col_tel = get_col_exact(df_p, "TELEFONO")
        col_com = get_col_exact(df_p, "COMUNA")
        col_sec = get_col_exact(df_p, "SECTOR")
        col_prog = get_col_exact(df_p, "ASESORÍA")
        col_ase = get_col_exact(df_p, "ASESOR")

        df_p = df_p[pd.to_numeric(df_p.iloc[:, 0], errors='coerce').notnull()]
        df_r = df_r[pd.to_numeric(df_r.iloc[:, 0], errors='coerce').notnull()]

        consolidado = []

        for _, row in df_p.iterrows():
            rut_val = clean_val(row[col_rut_p])
            row_real = df_r[df_r[col_rut_r].apply(clean_val) == rut_val]
            
            for mes in MESES:
                col_m_p = get_col_exact(df_p, mes)
                col_m_r = get_col_exact(df_r, mes)
                meta = pd.to_numeric(row.get(col_m_p, 0), errors='coerce') if col_m_p else 0
                real = 0
                if not row_real.empty and col_m_r:
                    real = pd.to_numeric(row_real.iloc[0].get(col_m_r, 0), errors='coerce')
                
                meta = 0 if pd.isna(meta) else int(meta)
                real = 0 if pd.isna(real) else int(real)

                if meta >= 1 or real >= 1:
                    if meta >= 1 and real >= 1: 
                        est, emo, color = "CUMPLIDA", "✅", "#1b5e20"
                    elif meta >= 1 and real == 0: 
                        est, emo, color = "PENDIENTE", "❌", "#b71c1c"
                    else: 
                        est, emo, color = "EXTRA-PLAN", "⚠️", "#f57f17"
                    
                    consolidado.append({
                        'USUARIO': normalize_text(row.get(col_nom, 'SIN NOMBRE')),
                        'RUT': rut_val,
                        'TELEFONO': str(row.get(col_tel, 'S/I')),
                        'COMUNA': normalize_text(row.get(col_com, 'S/I')),
                        'SECTOR': normalize_text(row.get(col_sec, 'S/I')),
                        'ASESORÍA': normalize_text(row.get(col_prog, 'S/I')),
                        'ASESOR': normalize_text(row.get(col_ase, 'S/I')),
                        'MES': mes,
                        'META': meta, 
                        'REAL': real,
                        'ESTADO': est, 
                        'EMOJI': emo
                    })
        
        return pd.DataFrame(consolidado)
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return pd.DataFrame()

def crear_grafico_resumen(df):
    """Crea gráfico de barras para el email"""
    if df.empty:
        return None
    
    resumen = df.groupby('MES').agg({
        'META': 'sum',
        'REAL': 'sum'
    }).reindex(MESES).fillna(0)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=resumen.index,
        y=resumen['META'],
        name='Meta Planificada',
        marker_color='#2E59A7'
    ))
    
    fig.add_trace(go.Bar(
        x=resumen.index,
        y=resumen['REAL'],
        name='Real Ejecutado',
        marker_color='#F1C40F'
    ))
    
    fig.update_layout(
        title='Resumen de Visitas 2026',
        barmode='group',
        template='plotly_white',
        height=400,
        width=700,
        yaxis_title='N° de Visitas',
        xaxis_title='Mes'
    )
    
    return fig

def generar_reporte_html(df, es_corte_15=False):
    """Genera el HTML del reporte"""
    
    hoy = datetime.now()
    mes_num = hoy.month
    mes_actual = MESES[mes_num - 3] if mes_num >= 3 else 'MAR'
    
    # Determinar mes actual basado en datos
    meses_con_datos = df[df['REAL'] > 0]['MES'].unique()
    if len(meses_con_datos) > 0:
        mes_actual = meses_con_datos[-1]
    
    mes_nombre = {
        'MAR': 'Marzo', 'ABR': 'Abril', 'MAY': 'Mayo', 'JUN': 'Junio',
        'JUL': 'Julio', 'AGO': 'Agosto', 'SEP': 'Septiembre', 'OCT': 'Octubre',
        'NOV': 'Noviembre', 'DIC': 'Diciembre'
    }.get(mes_actual, mes_actual)
    
    # Filtrar por mes actual
    df_mes = df[df['MES'] == mes_actual] if mes_actual in df['MES'].values else df
    
    # KPIs
    total_meta = df_mes['META'].sum()
    total_real = df_mes['REAL'].sum()
    cumplimiento = (total_real/total_meta*100) if total_meta > 0 else 0
    pendientes_df = df_mes[df_mes['ESTADO'] == 'PENDIENTE']
    total_pendientes = len(pendientes_df)
    
    # Tabla de asesores pendientes
    tabla_alertas = ""
    if not pendientes_df.empty:
        asesores_pend = pendientes_df.groupby('ASESOR').agg({
            'USUARIO': 'count',
            'META': 'sum'
        }).reset_index().sort_values('USUARIO', ascending=False)
        
        tabla_alertas = """
        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px;">
            <h3 style="color: #856404; margin-top: 0;">⚠️ Alerta: Asesores con Visitas Pendientes</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr style="background: #856404; color: white;">
                    <th style="padding: 10px; text-align: left;">Asesor</th>
                    <th style="padding: 10px; text-align: center;">Visitas Pendientes</th>
                    <th style="padding: 10px; text-align: center;">Meta del Mes</th>
                </tr>
        """
        
        for _, row in asesores_pend.head(10).iterrows():
            tabla_alertas += f"""
                <tr style="background: white;">
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{row['ASESOR']}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center; color: #d32f2f; font-weight: bold;">{int(row['USUARIO'])}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{int(row['META'])}</td>
                </tr>
            """
        tabla_alertas += "</table></div>"
    
    # Color según cumplimiento
    color_cumplimiento = '#28a745' if cumplimiento >= 80 else '#ffc107' if cumplimiento >= 50 else '#dc3545'
    estado_texto = '✅ Cumplimiento Óptimo' if cumplimiento >= 80 else '⚠️ Cumplimiento Regular - Requiere Atención' if cumplimiento >= 50 else '❌ Cumplimiento Bajo - Acción Inmediata'
    
    titulo = f"Reporte de Corte - 15 {mes_nombre}" if es_corte_15 else f"Reporte Final - {mes_nombre}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 20px; background-color: #f5f5f5; font-family: Arial, sans-serif;">
        <div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #2E59A7 0%, #1a1a2e 100%); padding: 30px; text-align: center;">
                <h1 style="color: #F1C40F; margin: 0; font-size: 28px;">🐝 CARMENCITA</h1>
                <p style="color: white; margin: 10px 0 0 0; font-size: 18px; font-weight: bold;">{titulo}</p>
                <p style="color: #bdc3c7; margin: 5px 0 0 0; font-size: 14px;">Sistema de Seguimiento Operativo</p>
            </div>
            
            <!-- Contenido -->
            <div style="padding: 30px;">
                
                <!-- KPIs Cards -->
                <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 30px;">
                    
                    <div style="flex: 1; min-width: 150px; background: {color_cumplimiento}15; border-left: 4px solid {color_cumplimiento}; padding: 20px; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">% Cumplimiento</p>
                        <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: {color_cumplimiento};">{cumplimiento:.1f}%</p>
                    </div>
                    
                    <div style="flex: 1; min-width: 150px; background: #e3f2fd; border-left: 4px solid #2196f3; padding: 20px; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">Realizadas</p>
                        <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #2196f3;">{int(total_real)}</p>
                    </div>
                    
                    <div style="flex: 1; min-width: 150px; background: #ffebee; border-left: 4px solid #f44336; padding: 20px; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">Pendientes</p>
                        <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #f44336;">{int(total_pendientes)}</p>
                    </div>
                    
                    <div style="flex: 1; min-width: 150px; background: #f3e5f5; border-left: 4px solid #9c27b0; padding: 20px; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">Usuarios</p>
                        <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: #9c27b0;">{df_mes['RUT'].nunique()}</p>
                    </div>
                </div>
                
                <!-- Estado General -->
                <div style="background: {color_cumplimiento}15; border: 1px solid {color_cumplimiento}; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                    <p style="margin: 0; font-size: 16px; font-weight: bold; color: {color_cumplimiento};">{estado_texto}</p>
                </div>
                
                {tabla_alertas}
                
                <!-- Detalle -->
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px;">
                    <h3 style="color: #2E59A7; margin-top: 0;">📊 Detalle del Mes</h3>
                    <table style="width: 100%; font-size: 14px;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Meta Planificada:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{int(total_meta)} visitas</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Visitas Ejecutadas:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{int(total_real)} visitas</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Diferencia:</strong></td>
                            <td style="padding: 8px 0; text-align: right; color: {'#dc3545' if total_real < total_meta else '#28a745'}; font-weight: bold;">
                                {int(total_real - total_meta)} visitas
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Efectividad:</strong></td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold;">{cumplimiento:.1f}%</td>
                        </tr>
                    </table>
                </div>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px; text-align: center;">
                    📅 Reporte generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}<br>
                    🐝 Sistema Carmencita 2026
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html, df_mes

def enviar_email_reporte(es_corte_15=False, email_user=None, email_pass=None):
    """Función principal para enviar el reporte"""
    
    # Obtener credenciales
    if email_user is None:
        email_user = os.environ.get("EMAIL_USER")
    if email_pass is None:
        email_pass = os.environ.get("EMAIL_PASS")
    
    if not email_user or not email_pass:
        raise ValueError("No se encontraron credenciales de email. Configura EMAIL_USER y EMAIL_PASS")
    
    print("📥 Cargando datos...")
    df = load_data_from_sheets()
    
    if df.empty:
        raise ValueError("No se pudieron cargar datos desde Google Sheets")
    
    print(f"✅ Datos cargados: {len(df)} registros")
    
    # Generar reporte
    print("📝 Generando reporte HTML...")
    html_content, df_mes = generar_reporte_html(df, es_corte_15)
    
    # Calcular métricas para el asunto
    total_meta = df_mes['META'].sum()
    total_real = df_mes['REAL'].sum()
    cumplimiento = (total_real/total_meta*100) if total_meta > 0 else 0
    
    # Crear mensaje
    msg = MimeMultipart('related')
    msg['From'] = email_user
    msg['To'] = EMAIL_DESTINO
    msg['Subject'] = f"🐝 Reporte {'Corte 15' if es_corte_15 else 'Final'} - Carmencita | Cumplimiento: {cumplimiento:.1f}%"
    
    # Adjuntar HTML
    msg.attach(MimeText(html_content, 'html'))
    
    # Crear y adjuntar gráfico
    print("📊 Generando gráfico...")
    fig = crear_grafico_resumen(df)
    if fig:
        img_bytes = pio.to_image(fig, format='png', scale=2)
        image = MimeImage(img_bytes)
        image.add_header('Content-ID', '<grafico>')
        image.add_header('Content-Disposition', 'inline', filename='grafico.png')
        msg.attach(image)
    
    # Enviar
    print("📧 Conectando a Gmail...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_user, email_pass)
    
    print("📤 Enviando email...")
    server.send_message(msg)
    server.quit()
    
    print(f"✅ Email enviado exitosamente a {EMAIL_DESTINO}")
    return True, cumplimiento, total_real, total_meta

# Para ejecución directa (GitHub Actions)
if __name__ == "__main__":
    import sys
    
    es_corte_15 = "--corte15" in sys.argv
    
    try:
        exito, cumpl, real, meta = enviar_email_reporte(es_corte_15)
        if exito:
            print(f"\n🎉 Reporte enviado correctamente")
            print(f"📊 Resumen: {cumpl:.1f}% de cumplimiento ({real}/{meta})")
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
