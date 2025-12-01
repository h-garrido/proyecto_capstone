#------------------------
# Importación de Librerías
#------------------------
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from plotly.subplots import make_subplots
import re
import os
import sys
#------------------------
# Fin de Importación de Librerías
#------------------------


#------------------------
# Funciones de Utilidad
#------------------------
def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo"""
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def format_time_from_minutes(minutes):
    """Convierte minutos a un string en formato hh:mm:ss."""
    if pd.isna(minutes) or not np.isfinite(minutes):
        return "00:00:00"
    
    td = pd.to_timedelta(minutes, unit='m')
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    mins, secs = divmod(remainder, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"
#------------------------
# Fin de Funciones de Utilidad
#------------------------


#------------------------
# Funciones Específicas de la App
#------------------------
def month_to_spanish(month_num):
    """Convierte el número del mes a su nombre en español."""
    return {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }.get(month_num, "Mes Desconocido")

#------------------------
# Fin de Funciones Específicas de la App
#------------------------


#------------------------
# Definición de Constantes y Nombres de Columnas
#------------------------
COL_T_REAL_MIN = "T_Real_min"
COL_T_ESPERA_MIN = "T_Espera_min"
COL_T_ACUMULADO = "T_Real_Acumulado" 
COL_LEAD_TIME_MIN = 'Lead_Time_min' 
#------------------------
# Fin de Definición de Constantes y Nombres de Columnas
#------------------------


#------------------------
# Carga y Pre-procesamiento de Datos
#------------------------
@st.cache_data
def load_data():
    data_path = resource_path("Datos_Banos.xlsx")
    df = pd.read_excel(data_path, engine="openpyxl")

    # PRE-PROCESAMIENTO DE DATOS
    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=False, errors="coerce")

    # Crear la columna 'Tipo_bano_agrupado' para el filtro agrupado
    df['Tipo_bano_agrupado'] = df['Tipo_bano'].apply(lambda x: re.match(r'B\d+', x).group(0) if re.match(r'B\d+', x) else x)

    # Operarios concatenados
    df["Operarios_list"] = df[["Operario_1","Operario_2","Operario_3"]].apply(
        lambda x: [p.strip() for p in x if isinstance(p,str) and p.strip() != ""], axis=1
    )
    df["Operarios"] = df["Operarios_list"].apply(lambda x: ", ".join(x))
    
    # --- Asignación de Tiempos en Horas y Minutos ---
    # Se asignan las columnas de horas desde el Excel a los nombres usados en el app
    df['T_Real_hr'] = df['T_Real_horas']
    df['T_Espera_hr'] = df['T_Espera_horas']

    # Calcular el Lead Time (Ciclo) por Baño en MINUTOS
    df_max_corr_min = df.groupby('Cod_bano')[COL_T_ACUMULADO].max().reset_index()
    df_max_corr_min.columns = ['Cod_bano', COL_LEAD_TIME_MIN]
    df = pd.merge(df, df_max_corr_min, on='Cod_bano', how='left')

    # Calcular el Lead Time (Ciclo) por Baño en HORAS
    df_max_corr_hr = df.groupby('Cod_bano')['T_Real_Acumulado_horas'].max().reset_index()
    df_max_corr_hr.columns = ['Cod_bano', 'Lead_Time_hr']
    df = pd.merge(df, df_max_corr_hr, on='Cod_bano', how='left')

    # Columnas numéricas para análisis de cumplimiento
    df['Cumple_Num'] = df['Cumple_TT'].astype(int)

    return df

df = load_data()
#------------------------
# Fin de Carga y Pre-procesamiento de Datos
#------------------------


#------------------------
# Configuración de la Página Streamlit y Encabezado
#------------------------
st.set_page_config(page_title="Dashboard Productividad Baños", layout="wide", initial_sidebar_state="collapsed")

# --- HEADER ---
col1, col2 = st.columns([1, 5])
with col1:
    logo_path = resource_path("resources/axis_logo.jpg")
    st.image(logo_path, width=200)
with col2:
    st.title("Dashboard Productividad en Procesos - Baños")

st.markdown("---")
#------------------------
# Fin de Configuración de la Página Streamlit y Encabezado
#------------------------


#------------------------
# Barra Lateral y Filtros
#------------------------
# Preparar meses_map antes de la barra lateral para inicialización de session_state
df['AñoMes'] = df['Fecha'].dt.strftime('%Y-%m')
unique_months = sorted(df["AñoMes"].unique(), reverse=True)
meses_map = {
    f"{month_to_spanish(int(ym.split('-')[1]))}, {ym.split('-')[0]}": ym
    for ym in unique_months
}

with st.sidebar:
    st.header("Filtros de Análisis")

    # Initialize session state for filters to avoid warnings
    if 'tipo_analisis_temporal' not in st.session_state:
        st.session_state.tipo_analisis_temporal = 'Análisis Completo (Todos los Meses)'
    if 'meses_sel' not in st.session_state:
        st.session_state.meses_sel = list(meses_map.keys())
    if 'correlativos_sel' not in st.session_state:
        st.session_state.correlativos_sel = []
    if 'tipo_bano_agrupado_sel' not in st.session_state:
        st.session_state.tipo_bano_agrupado_sel = "Todos"

    # --- Filtro Temporal Refinado ---
    # meses_map ya definido arriba

    # --- Lógica para el botón de reseteo ---
    def reset_filters():
        st.session_state.meses_sel = list(meses_map.keys())
        st.session_state.correlativos_sel = []
        st.session_state.tipo_bano_agrupado_sel = "Todos"
        st.session_state.tipo_analisis_temporal = 'Análisis Completo (Todos los Meses)'

    tipo_analisis_temporal = st.radio(
        "Seleccione el tipo de análisis temporal",
        ('Análisis Completo (Todos los Meses)', 'Selección por Mes Específico'),
        key='tipo_analisis_temporal'
    )

    if tipo_analisis_temporal == 'Selección por Mes Específico':
        meses_sel_display = st.multiselect(
            "Seleccione Mes(es) de Ciclo",
            options=list(meses_map.keys()),
            key='meses_sel'
        )
        meses_sel = [meses_map[m] for m in meses_sel_display]
    else:
        meses_sel = []

    # --- Otros Filtros ---
    # Correlativo
    unique_vals = df["Correlativo"].dropna().unique().tolist()

    def _sort_key(v):
        try:
            return (0, float(v))
        except Exception:
            return (1, str(v))

    todos_correlativos = [str(v) for v in sorted(unique_vals, key=_sort_key)]
    correlativos_sel = st.multiselect("Correlativo(s)", todos_correlativos, key='correlativos_sel')

    # Tipo de Baño (Agrupado)
    grouped_bano_options = ["Todos"] + sorted(df["Tipo_bano_agrupado"].unique().tolist())
    tipo_bano_agrupado_sel = st.selectbox("Tipo baño (Agrupado)", grouped_bano_options, key='tipo_bano_agrupado_sel')

    # --- Botón de Reseteo ---
    st.markdown("---")
    st.button("Restablecer Filtros", on_click=reset_filters, use_container_width=True)

#------------------------
# FIN Barra Lateral y Filtros
#------------------------


#------------------------
# Aplicación de Filtros al DataFrame
#------------------------
    df_filt = df.copy()

    # Filtro por meses
    if tipo_analisis_temporal == 'Selección por Mes Específico' and len(meses_sel) > 0:
        df_filt = df_filt[df_filt["AñoMes"].isin(meses_sel)]

    # Filtro por correlativo
    if len(correlativos_sel) > 0:
        df_filt = df_filt[df_filt["Correlativo"].astype(str).isin(correlativos_sel)]

    # Filtro por tipo de baño agrupado
    if tipo_bano_agrupado_sel != "Todos":
        df_filt = df_filt[df_filt["Tipo_bano_agrupado"] == tipo_bano_agrupado_sel]

#------------------------
# FIN Aplicación de filtros
#------------------------


#------------------------
# Configuración de Unidades de Tiempo
#------------------------
    COL_T_REAL_UNIT = COL_T_REAL_MIN
    COL_T_ESPERA_UNIT = COL_T_ESPERA_MIN
    COL_LEAD_TIME_UNIT = COL_LEAD_TIME_MIN
    COL_DIFERENCIA_TT_UNIT = "Diferencia_TT"
    UNIT_LABEL = "minutos"
#------------------------
# Fin Configuración de Unidades de Tiempo
#------------------------


#------------------------
# Cálculo de Métricas Clave (usando DataFrame filtrado)
#------------------------
    banos_terminados = df_filt['Cod_bano'].nunique()

    if banos_terminados > 0:
        avg_lead_time = df_filt.drop_duplicates(subset='Cod_bano')[COL_LEAD_TIME_UNIT].mean()
        avg_procesos_por_bano = len(df_filt) / banos_terminados
    else:
        avg_lead_time = 0
        avg_procesos_por_bano = 0

    avg_t_real = df_filt[COL_T_REAL_UNIT].mean() if len(df_filt) > 0 else 0
    avg_pct_cumple = df_filt['Cumple_Num'].mean() * 100 if len(df_filt) > 0 else 0
#------------------------
# FIN Cálculo de Métricas Clave
#------------------------


#------------------------
# Visualización de Métricas Clave
#------------------------
st.header("Métricas Clave de Productividad")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Baños Terminados", banos_terminados)
col2.metric("Tiempo promedio de fabricación", format_time_from_minutes(avg_lead_time),
            help="Tiempo promedio que tarda en completarse un baño (desde el inicio hasta su finalización).")
col3.metric("Procesos Promedio por Baño", f"{avg_procesos_por_bano:.1f}",
            help="Cantidad promedio de procesos necesarios para completar un baño.")
col4.metric("Tiempo Promedio de Proceso", format_time_from_minutes(avg_t_real))
col5.metric("Tasa de Cumplimiento General", f"{avg_pct_cumple:.1f}%",
            help="Porcentaje promedio de procesos que cumplen con el Takt Time en los baños filtrados.")

st.markdown("---")
#------------------------
# FIN Visualización de Métricas Clave
#------------------------


#------------------------
# Creación de Pestañas (Tabs)
#------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Cronología y Distribución", "Análisis por Correlativo", "Análisis por Proceso", "Análisis por Operario", "Evolución Temporal", "Eficiencia Operarios"
])
#------------------------
# Fin de Creación de Pestañas (Tabs)
#------------------------


#------------------------
# Aplicación de Filtros al DataFrame para tab1
#------------------------
df_tab1_filtered = df.copy()

if st.session_state.tipo_analisis_temporal == 'Selección por Mes Específico':
    if meses_sel:
        df_tab1_filtered = df_tab1_filtered[df_tab1_filtered['AñoMes'].isin(meses_sel)]
    else:
        df_tab1_filtered = df_tab1_filtered.iloc[0:0]

    if st.session_state.correlativos_sel:
        df_tab1_filtered = df_tab1_filtered[df_tab1_filtered["Correlativo"].astype(str).isin(st.session_state.correlativos_sel)]

    if st.session_state.tipo_bano_agrupado_sel != "Todos": # Usar la clave correcta del session_state
        # Filtrar por el grupo seleccionado
        df_tab1_filtered = df_tab1_filtered[df_tab1_filtered["Tipo_bano_agrupado"] == st.session_state.tipo_bano_agrupado_sel]

if df_tab1_filtered.empty:
    st.warning("No hay datos con los filtros seleccionados para 'Cronología y Distribución'. Ajuste los filtros.")
    # No st.stop() aquí para permitir que otras pestañas se carguen con el df completo
#------------------------
# Fin de Aplicación de Filtros al DataFrame para tab1
#------------------------


#------------------------
# Pestaña 1: Dashboard Principal
#------------------------
with tab1:
    #------------------------
    # Pestaña 1 - Gráfico Gantt
    #------------------------
    st.subheader("Cronología General de Baños (Gantt)")

    gantt_df = df_tab1_filtered.groupby('Correlativo').agg(
        Inicio=('Fecha', 'min'),
        Término=('Fecha', 'max'),
        Tipo_bano=('Tipo_bano', 'first')
    ).reset_index()

    gantt_df['Correlativo_num'] = pd.to_numeric(gantt_df['Correlativo'], errors='coerce')
    gantt_df.dropna(subset=['Correlativo_num'], inplace=True)
    gantt_df.sort_values('Correlativo_num', inplace=True)
    
    gantt_df['Correlativo_str'] = gantt_df['Correlativo_num'].astype(int).astype(str)

    if not gantt_df.empty:
        fig_gantt = px.timeline(
            gantt_df,
            x_start="Inicio",
            x_end="Término",
            y="Correlativo_str",
            title="Línea de Tiempo de Fabricación por Baño",
            color="Correlativo_str",
            hover_data=['Tipo_bano']
        )

        # ---- FONDO ALTERNADO POR MES (blanco / gris) ----
        min_date = gantt_df['Inicio'].min().replace(day=1)
        max_date = gantt_df['Término'].max().replace(day=1) + pd.offsets.MonthEnd(1)

        month_edges = pd.date_range(min_date, max_date, freq='MS')

        shapes = []
        toggle = True  # alternador blanco/gris

        for i in range(len(month_edges)-1):
            start_m = month_edges[i]
            end_m = month_edges[i+1]

            shapes.append(dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=start_m,
                x1=end_m,
                y0=0,
                y1=1,
                fillcolor="white" if toggle else "LightGray",
                opacity=0.4,
                layer="below",
                line_width=0
            ))
            
            toggle = not toggle  # alterna colores

        fig_gantt.update_layout(shapes=shapes)
        # ---- FIN FONDO POR MES ----
        
        fig_gantt.update_yaxes(autorange="reversed", title="Correlativo")
        fig_gantt.update_layout(
            xaxis_title="Fecha",
            height=max(500, len(gantt_df) * 10),
            plot_bgcolor='white',
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray'),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray')
        )
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("No hay datos de correlativos para mostrar en el gráfico Gantt.")
    #------------------------
    # Fin Pestaña 1 - Gráfico Gantt
    #------------------------


    #------------------------
    # Pestaña 1 - Gráfico de Torta
    #------------------------
    st.markdown("---")
    st.subheader("Distribución por Tipo de Baño")
    
        # Selector de modo de visualización
    display_mode = st.radio(
        "Mostrar en:",
        ('Cantidad', 'Porcentaje'),
        index=0
    )

    # Procesamiento de datos
    tipo_bano_counts = (
        df_tab1_filtered.drop_duplicates(subset='Cod_bano')['Tipo_bano']
        .value_counts()
        .reset_index()
    )
    tipo_bano_counts.columns = ['Tipo_bano', 'Cantidad']

    total = tipo_bano_counts['Cantidad'].sum()
    tipo_bano_counts['Porcentaje'] = tipo_bano_counts['Cantidad'] / total

    # Orden natural B1, B1a, B2, B2a, ...
    def natural_sort_key(s):
        match = re.match(r'B(\d+)([a-zA-Z]*)', str(s))
        return (int(match.group(1)), match.group(2)) if match else (float('inf'), str(s))

    sorted_categories = sorted(tipo_bano_counts['Tipo_bano'], key=natural_sort_key)

    # Configuración según modo seleccionado
    if display_mode == 'Cantidad':
        values_col = 'Cantidad'
        chart_title = 'Cantidad de Baños Fabricados por Tipo'
        text_info = 'label+value'
        hover_template = "<b>%{label}</b><br>Cantidad: %{value}<extra></extra>"
    else:
        values_col = 'Porcentaje'
        chart_title = 'Distribución Porcentual de Baños Fabricados por Tipo'
        text_info = 'label+percent'
        hover_template = "<b>%{label}</b><br>Porcentaje: %{percent:.1%}<extra></extra>"

    # Paleta elegida: tonos sobrios y profesionales
    colors = px.colors.qualitative.Set2

    # Creación del gráfico
    fig_pie = px.pie(
        tipo_bano_counts,
        names='Tipo_bano',
        values=values_col,
        title=chart_title,
        color='Tipo_bano',
        category_orders={'Tipo_bano': sorted_categories},
        color_discrete_sequence=colors
    )

    # Estética general
    fig_pie.update_traces(
        textinfo=text_info,
        textposition='outside',
        pull=0.05,               # Separación ligera entre porciones
        hovertemplate=hover_template,
        rotation=90,              # Alineación inicial más estética
        textfont_size=16
    )

    fig_pie.update_layout(
        width=600,
        height=600,
        title_font_size=26,
        legend_title_text="Tipo de Baño",
        legend_font_size=16,
        margin=dict(t=90, b=50, l=10, r=10),
    )

    # Render en Streamlit
    st.plotly_chart(fig_pie, use_container_width=True)

    #------------------------
    # Fin Pestaña 1 - Gráfico de Torta
    #------------------------
#------------------------
# Fin Pestaña 1: Dashboard Principal
#------------------------


#------------------------
# Pestaña 2: Análisis por Correlativo
#------------------------
with tab2:
    st.header("Análisis Individual por Correlativo")

    correlativos_disponibles = sorted(df["Correlativo"].dropna().unique().tolist())
    
    if not correlativos_disponibles:
        st.warning("No hay Correlativos disponibles con los filtros actuales.")
        st.stop()

    correlativo_sel_ind = st.selectbox(
        "Seleccione un Correlativo para analizar",
        correlativos_disponibles
    )

    if correlativo_sel_ind:
        d_corr = df[df["Correlativo"] == correlativo_sel_ind].copy()
        d_corr = d_corr.sort_values('Fecha')

        #------------------------
        # Pestaña 2 - Métricas Individuales
        #------------------------
        st.markdown(f"### Métricas para el Correlativo: **{correlativo_sel_ind}**")

        tipo_bano_corr = d_corr['Tipo_bano'].iloc[0]
        fecha_inicio = d_corr['Fecha'].min().date()
        fecha_fin = d_corr['Fecha'].max().date()
        tiempo_real_total = d_corr[COL_T_REAL_UNIT].sum()
        tiempo_espera_total = d_corr[COL_T_ESPERA_UNIT].sum()
        num_procesos = len(d_corr)
        
        operarios_corr_set = {op for ops_list in d_corr['Operarios_list'] for op in ops_list}
        operarios_corr = ", ".join(sorted(list(operarios_corr_set)))

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Tipo de Baño", tipo_bano_corr)
        col_m2.metric("Fecha de Inicio", str(fecha_inicio))
        col_m3.metric("Fecha de Fin", str(fecha_fin))

        col_m4, col_m5, col_m6 = st.columns(3)
        col_m4.metric("Tiempo Real Total", format_time_from_minutes(tiempo_real_total))
        col_m5.metric("Tiempo de Espera Total", format_time_from_minutes(tiempo_espera_total))
        col_m6.metric("Número de Procesos", num_procesos)

        st.markdown(f"**Operarios Involucrados:** {operarios_corr}")
        st.markdown("---")
        #------------------------
        # Fin Pestaña 2 - Métricas Individuales
        #------------------------


        #------------------------
        # Pestaña 2 - Tabla de Secuencia de Procesos
        #------------------------
        st.subheader("Secuencia de Procesos")
        
        df_display = d_corr[[
            'Fecha', 'Proceso', COL_T_REAL_UNIT, COL_T_ESPERA_UNIT, 
            'TT', 'Cumple_TT', 'Operarios'
        ]].copy()

        df_display['Fecha'] = df_display['Fecha'].dt.date

        df_display['T. Real'] = df_display[COL_T_REAL_UNIT].apply(format_time_from_minutes)
        df_display['T. Espera'] = df_display[COL_T_ESPERA_UNIT].apply(format_time_from_minutes)
        df_display['Takt Time'] = df_display['TT'].apply(format_time_from_minutes)
        
        df_display_final = df_display[[
            'Fecha', 'Proceso', 'T. Real', 'T. Espera', 
            'Takt Time', 'Cumple_TT', 'Operarios'
        ]]

        # ======== ESTILO PARA COLOREAR FILAS COMPLETAS ========
        def style_rows(row):
            espera_val = int(row["T. Espera"].split(":")[0]) * 60 + int(row["T. Espera"].split(":")[1])  # convertir h:m a minutos
            cumple = row["Cumple_TT"]

            # Colores base
            if cumple:
                base_color = "#c8f7c5"   # verde claro
                dark_color = "#a1d89a"   # verde oscuro
            else:
                base_color = "#f7c5c5"   # rojo claro
                dark_color = "#d89a9a"   # rojo oscuro

            # Si T. Espera > 0 oscurecer la fila
            if espera_val > 0:
                color = dark_color
            else:
                color = base_color

            return [f"background-color: {color}"] * len(row)


        styled_df = df_display_final.style.apply(style_rows, axis=1)

        st.dataframe(styled_df, use_container_width=True)
        #------------------------
        # Fin Pestaña 2 - Tabla de Secuencia de Procesos
        #------------------------

        
        #------------------------
        # Pestaña 2 - Diagrama de Flujo (Gantt)
        #------------------------
        st.subheader("Diagrama de Flujo de Procesos (Gantt)")

        d_corr_sorted = d_corr.sort_values(by='Fecha').reset_index()

        gantt_data = []
        current_duration_minutes = 0

        for index, row in d_corr_sorted.iterrows():
            if index > 0:
                wait_minutes = row['T_Espera_min']
                current_duration_minutes += wait_minutes

            start_duration = current_duration_minutes
            process_duration = row['T_Real_min']
            end_duration = start_duration + process_duration

            gantt_data.append(dict(
                Proceso=row['Proceso'],
                Inicio_Duracion=start_duration,
                Fin_Duracion=end_duration,
                Operarios=row['Operarios'],
                T_Real_Unit=row[COL_T_REAL_UNIT],
                T_Espera_Unit=row[COL_T_ESPERA_MIN]
            ))

            current_duration_minutes = end_duration

        gantt_df = pd.DataFrame(gantt_data)
        
        # Crear colores dinámicos para Operarios
        unique_operarios = gantt_df['Operarios'].unique()
        # Puedes elegir una paleta de colores de Plotly o definir la tuya
        colors = px.colors.qualitative.Plotly # O cualquier otra paleta

        color_map = {operario: colors[i % len(colors)] for i, operario in enumerate(unique_operarios)}


        fig_gantt = go.Figure()

        # Agrupar por operario para una leyenda unificada
        for operario in unique_operarios:
            df_operario = gantt_df[gantt_df['Operarios'] == operario]
            
            # Crear hovertext para todos los procesos de este operario
            hovertexts = []
            for idx, row in df_operario.iterrows():
                hovertexts.append(
                    f"Proceso: {row['Proceso']}<br>"
                    f"Operarios: {row['Operarios']}<br>"
                    f"Inicio (min): {row['Inicio_Duracion']:.1f}<br>"
                    f"Fin (min): {row['Fin_Duracion']:.1f}<br>"
                    f"Duración Real: {format_time_from_minutes(row['T_Real_Unit'])}<br>"
                    f"Tiempo de Espera: {format_time_from_minutes(row['T_Espera_Unit'])}"
                )

            fig_gantt.add_trace(go.Bar(
                y=df_operario['Proceso'],
                x=df_operario['Fin_Duracion'] - df_operario['Inicio_Duracion'],
                base=df_operario['Inicio_Duracion'],
                orientation='h',
                name=operario, # Nombre del operario para la leyenda
                legendgroup=operario, # Agrupar elementos en la leyenda
                showlegend=True, # Mostrar en la leyenda
                marker_color=color_map[operario],
                hoverinfo='text',
                hovertext=hovertexts
            ))
        
        # Función para formatear el eje X en hh:mm:ss
        def format_minutes_to_hms(minutes_val):
            total_seconds = int(minutes_val * 60)
            hours, remainder = divmod(total_seconds, 3600)
            mins, secs = divmod(remainder, 60)
            return f"{hours:02d}:{mins:02d}:{secs:02d}"

        # Determinar tickvals para el eje X
        max_duration = gantt_df['Fin_Duracion'].max()
        
        # Calcular los intervalos de 10 horas para el sombreado (en minutos)
        # 10 horas = 600 minutos
        hour_interval_minutes = 600
        
        shapes = []
        toggle = True # alternador blanco/gris
        
        # Iterar en intervalos de 10 horas
        current_time_minutes = 0
        while current_time_minutes < max_duration:
            start_hour_block = current_time_minutes
            end_hour_block = current_time_minutes + hour_interval_minutes
            
            # Solo añadir el rectángulo si toggle es True (para alternar los colores)
            if toggle:
                shapes.append(dict(
                    type="rect",
                    xref="x",
                    yref="paper",
                    x0=start_hour_block,
                    x1=end_hour_block,
                    y0=0,
                    y1=1,
                    fillcolor="LightGray", # Color gris claro
                    opacity=0.4,
                    layer="below",
                    line_width=0
                ))
            toggle = not toggle # Alternar para el siguiente bloque

            current_time_minutes = end_hour_block
            

        # Asegura que el intervalo de ticks sea al menos 1 para evitar divisiones por cero o ticks excesivamente pequeños
        tick_interval = max(1, int(max_duration / 10)) 
        tick_values = list(range(0, int(max_duration * 1.1) + tick_interval, tick_interval))

        # Obtener el orden de los procesos tal como aparecen en gantt_df
        # Esto asegura que el gráfico se dibuje del primer proceso al último
        process_order = [p for p in d_corr_sorted['Proceso'].unique()]

        fig_gantt.update_layout(
            title=f"Cronología de Procesos (Duración) para Correlativo {correlativo_sel_ind}",
            xaxis_title="Duración (hh:mm:ss)",
            yaxis_title="Proceso",
            barmode='stack',
            height=max(500, len(process_order) * 25), # Ajustar altura dinámicamente
            showlegend=True,
            plot_bgcolor='white',
            shapes=shapes, # Añadir los shapes al layout del gráfico
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGray',
                tickmode='array',
                tickvals=tick_values,
                ticktext=[format_minutes_to_hms(val) for val in tick_values]
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGray',
                categoryorder='array', # Usar el orden del array
                categoryarray=process_order # El array con el orden de los procesos
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_gantt, use_container_width=True)
        #------------------------
        # Fin Pestaña 2 - Diagrama de Flujo (Gantt)
        #------------------------
#------------------------
# Fin Pestaña 2: Análisis por Correlativo
#------------------------


#------------------------
# Pestaña 3: Análisis por Proceso
#------------------------
with tab3:
    #------------------------
    # Métricas Generales por Proceso
    #------------------------
    st.subheader("Métricas Generales por Proceso")
    cumplimiento_proceso_general = (
        df
        .groupby('Proceso')
        .agg({
            'Cumple_TT': ['mean', 'count'],
            COL_T_REAL_MIN: 'mean',
            'TT': 'mean'
        })
        .round(1)
    )
    cumplimiento_proceso_general.columns = ['Tasa_Cumplimiento', 'Cantidad', 'Tiempo_Promedio', 'TT_Promedio']
    cumplimiento_proceso_general = cumplimiento_proceso_general.sort_values('Tasa_Cumplimiento', ascending=True)
    if not cumplimiento_proceso_general.empty:
        # Crear tabla para mostrar la información
        df_display_general = cumplimiento_proceso_general.reset_index().copy()

        def style_rows_proceso_general(row):
            tasa = row["Tasa_Cumplimiento"]
            if tasa < 0.5:
                color = "#f7c5c5"  # rojo claro
            elif tasa < 0.8:
                color = "#fff3cc"  # amarillo claro
            else:
                color = "#c8f7c5"  # verde claro
            return [f"background-color: {color}"] * len(row)

        styled_df_proceso_general = df_display_general.style.apply(style_rows_proceso_general, axis=1)

        # Formatear columnas para mejor visualización
        styled_df_proceso_general = styled_df_proceso_general.format({
            'Tasa_Cumplimiento': lambda x: f"{x * 100:.1f}%",
            'Tiempo_Promedio': lambda x: format_time_from_minutes(x),
            'TT_Promedio': lambda x: format_time_from_minutes(x)
        }).set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center')]},
            {'selector': 'td', 'props': [('text-align', 'center')]},
        ])

        # Crear gráfico circular para porcentaje de cumplimiento
        cumplimiento_proceso_general['Categoria'] = cumplimiento_proceso_general['Tasa_Cumplimiento'].apply(
            lambda x: 'Bajo (<50%)' if x < 0.5 else 'Medio (50-80%)' if x < 0.8 else 'Alto (>80%)'
        )
        cumplimiento_counts_general = cumplimiento_proceso_general['Categoria'].value_counts()
        cumplimiento_counts_general = cumplimiento_counts_general.reindex(['Bajo (<50%)', 'Medio (50-80%)', 'Alto (>80%)'], fill_value=0)

        fig_pie_cumplimiento_general = go.Figure(data=[go.Pie(
            labels=cumplimiento_counts_general.index,
            values=cumplimiento_counts_general.values,
            marker_colors=['#f7c5c5', '#fff3cc', '#c8f7c5'],
            title="Distribución de Cumplimiento (General)"
        )])

        fig_pie_cumplimiento_general.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        # Usar columnas para layout
        col_table_general, col_pie_general = st.columns([2, 1])

        with col_table_general:
            st.dataframe(styled_df_proceso_general, use_container_width=True)

        with col_pie_general:
            st.plotly_chart(fig_pie_cumplimiento_general, use_container_width=True)

    #------------------------
    # Fin Métricas Generales por Proceso
    #------------------------

    tipos_bano = sorted(df['Tipo_bano'].unique())
    for tipo in tipos_bano:
        df_tipo = df[df['Tipo_bano'] == tipo]
        if df_tipo.empty:
            st.subheader(f"{tipo}: No hay datos")
            continue
        st.subheader(f"Análisis de Cumplimiento por Proceso - Tipo {tipo}")
        cumplimiento_proceso = (
            df_tipo
            .groupby('Proceso')
            .agg({
                'Cumple_TT': ['mean', 'count'],
                COL_T_REAL_MIN: 'mean',
                'TT': 'mean'
            })
            .round(1)
        )
        cumplimiento_proceso.columns = ['Tasa_Cumplimiento', 'Cantidad', 'Tiempo_Promedio', 'TT_Promedio']
        cumplimiento_proceso = cumplimiento_proceso.sort_values('Tasa_Cumplimiento', ascending=True)
        if not cumplimiento_proceso.empty:
            # Crear tabla para mostrar la información
            df_display = cumplimiento_proceso.reset_index().copy()

            def style_rows_proceso(row):
                tasa = row["Tasa_Cumplimiento"]
                if tasa < 0.5:
                    color = "#f7c5c5"  # rojo claro
                elif tasa < 0.8:
                    color = "#fff3cc"  # amarillo claro
                else:
                    color = "#c8f7c5"  # verde claro
                return [f"background-color: {color}"] * len(row)

            styled_df_proceso = df_display.style.apply(style_rows_proceso, axis=1)

            # Formatear columnas para mejor visualización
            styled_df_proceso = styled_df_proceso.format({
                'Tasa_Cumplimiento': lambda x: f"{x * 100:.1f}%",
                'Tiempo_Promedio': lambda x: format_time_from_minutes(x),
                'TT_Promedio': lambda x: format_time_from_minutes(x)
            }).set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center')]},
                {'selector': 'td', 'props': [('text-align', 'center')]},
            ])

            # Crear gráfico circular para porcentaje de cumplimiento
            cumplimiento_proceso['Categoria'] = cumplimiento_proceso['Tasa_Cumplimiento'].apply(
                lambda x: 'Bajo (<50%)' if x < 0.5 else 'Medio (50-80%)' if x < 0.8 else 'Alto (>80%)'
            )
            cumplimiento_counts = cumplimiento_proceso['Categoria'].value_counts()
            cumplimiento_counts = cumplimiento_counts.reindex(['Bajo (<50%)', 'Medio (50-80%)', 'Alto (>80%)'], fill_value=0)

            fig_pie_cumplimiento = go.Figure(data=[go.Pie(
                labels=cumplimiento_counts.index,
                values=cumplimiento_counts.values,
                marker_colors=['#f7c5c5', '#fff3cc', '#c8f7c5'],
                title=f"Distribución de Cumplimiento ({tipo})"
            )])

            fig_pie_cumplimiento.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
            )

            # Usar columnas para layout
            col_table, col_pie = st.columns([2, 1])

            with col_table:
                st.dataframe(styled_df_proceso, use_container_width=True)

            with col_pie:
                st.plotly_chart(fig_pie_cumplimiento, use_container_width=True)
#------------------------
# Fin Pestaña 3: Análisis por Proceso
#------------------------


#------------------------
# Pestaña 4: Análisis por Operario
#------------------------
with tab4:
    st.subheader("Análisis de Participación por Operario")

    # Selector de tipo de agrupación
    agrupacion = st.radio(
        "Agrupar por:",
        ("Correlativo", "Tipo de Baño"),
        index=0
    )

    if agrupacion == "Correlativo":
        correlativos_disponibles_op = sorted(df["Correlativo"].dropna().unique().tolist())
        if not correlativos_disponibles_op:
            st.warning("No hay correlativos disponibles.")
        else:
            correlativo_sel_op = st.selectbox("Seleccione un Correlativo", correlativos_disponibles_op, key="correlativo_sel_op")
            df_group = df[df["Correlativo"] == correlativo_sel_op].copy()
            titulo = f"Participación en Correlativo {correlativo_sel_op}"
    else:  # Tipo de Baño
        tipos_bano_disponibles = sorted(df["Tipo_bano"].unique())
        if not tipos_bano_disponibles:
            st.warning("No hay tipos de baño disponibles.")
        else:
            tipo_bano_sel_op = st.selectbox("Seleccione un Tipo de Baño", tipos_bano_disponibles, key="tipo_bano_sel_op")
            df_group = df[df["Tipo_bano"] == tipo_bano_sel_op].copy()
            titulo = f"Participación en Tipo de Baño {tipo_bano_sel_op}"

    # Si hay datos
    if not df_group.empty:
        # Contar operarios por proceso
        operarios_count = {}
        total_procesos = len(df_group)

        for _, row in df_group.iterrows():
            for op in row["Operarios_list"]:
                if op in operarios_count:
                    operarios_count[op] += 1
                else:
                    operarios_count[op] = 1

        # Crear DataFrame
        df_participacion = pd.DataFrame(list(operarios_count.items()), columns=["Operario", "Participaciones"])
        df_participacion["Porcentaje"] = (df_participacion["Participaciones"] / total_procesos * 100).round(1)

        # Ordenar por porcentaje descendente
        df_participacion = df_participacion.sort_values("Porcentaje", ascending=False).reset_index(drop=True)

        st.markdown(f"### {titulo}")
        st.markdown(f"**Total de Procesos:** {total_procesos}")
        st.markdown("---")

        # Crear mapa de colores consistente para cada operario
        operarios_unicos = sorted(df_participacion['Operario'].unique())
        colores_operarios_part = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
        color_map_part = {op: colores_operarios_part[i % len(colores_operarios_part)]
                          for i, op in enumerate(operarios_unicos)}

        col_part, col_pct = st.columns(2)

        with col_part:
            fig_part = go.Figure()
            for operario in df_participacion['Operario']:
                data_op = df_participacion[df_participacion['Operario'] == operario]
                fig_part.add_trace(go.Bar(
                    x=data_op['Participaciones'],
                    y=data_op['Operario'],
                    orientation='h',
                    name=operario,
                    marker_color=color_map_part[operario],
                    text=[f"{int(val)}" for val in data_op['Participaciones']],
                    textposition='outside',
                    showlegend=True
                ))

            fig_part.update_layout(
                title="Número de Participaciones por Operario",
                xaxis_title="Número de Participaciones",
                yaxis_title="Operario",
                yaxis={'categoryorder':'total ascending'},
                height=max(400, len(df_participacion) * 30),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02
                )
            )
            fig_part.update_xaxes(tickformat="d")
            st.plotly_chart(fig_part, use_container_width=True)

        with col_pct:
            # Pie chart for percentage
            fig_pie = px.pie(
                df_participacion,
                names="Operario",
                values="Participaciones",
                title="Porcentaje de Participación por Operario",
                hole=0.3,
                color="Operario",
                color_discrete_sequence=colores_operarios_part
            )
            fig_pie.update_traces(textinfo='percent', textfont_size=14)
            st.plotly_chart(fig_pie, use_container_width=True)

        # Chart for process breakdown per operario
        st.markdown("---")
        st.subheader("Desglose de Procesos por Operario")

        # Count processes per operario
        process_count = {}
        for _, row in df_group.iterrows():
            for op in row["Operarios_list"]:
                if op not in process_count:
                    process_count[op] = {}
                proceso = row['Proceso']
                process_count[op][proceso] = process_count[op].get(proceso, 0) + 1

        # Get unique processes
        procesos_unicos = sorted(set(proceso for ops in process_count.values() for proceso in ops))

        # Palette for processes
        colores_procesos = px.colors.qualitative.Prism
        color_map_procesos = {proc: colores_procesos[i % len(colores_procesos)] for i, proc in enumerate(procesos_unicos)}

        fig_procesos = go.Figure()

        for operario in df_participacion['Operario']:
            counts = process_count.get(operario, {})
            cumulative = 0
            for proceso in procesos_unicos:
                count = counts.get(proceso, 0)
                if count > 0:
                    fig_procesos.add_trace(go.Bar(
                        x=[operario],
                        y=[count],
                        name=proceso,
                        marker_color=color_map_procesos[proceso],
                        offsetgroup=cumulative,  # No offset for stacking
                        base=cumulative,
                        showlegend=True if operario == df_participacion['Operario'].iloc[0] else False  # Legend only for first operario
                    ))
                    cumulative += count

        fig_procesos.update_layout(
            title="Desglose de Procesos Participados por Operario",
            xaxis_title="Operario",
            yaxis_title="Número de Participaciones",
            barmode='stack',
            template="simple_white"
        )
        st.plotly_chart(fig_procesos, use_container_width=True)

#------------------------
# Fin Pestaña 4: Análisis por Operario
#------------------------


#------------------------
# Pestaña 5: Evolución Temporal
#------------------------
with tab5:
    st.subheader("Evolución de Productividad y Ciclo")

    # ============================
    # PRODUCTIVIDAD (BAÑOS/MES)
    # ============================

    df['Mes'] = df['Fecha'].dt.to_period('M')
    banos_por_mes = df.drop_duplicates(subset='Cod_bano') \
        .groupby('Mes')['Cod_bano'] \
        .count().reset_index()

    banos_por_mes['Mes'] = banos_por_mes['Mes'].astype(str)

    # ---- Promedio móvil 3 meses ----
    banos_por_mes["PM3"] = banos_por_mes["Cod_bano"].rolling(3).mean()

    # ---- Regresión lineal ----
    banos_por_mes["Mes_num"] = range(len(banos_por_mes))
    coef = np.polyfit(banos_por_mes["Mes_num"], banos_por_mes["Cod_bano"], 1)
    banos_por_mes["Tendencia"] = coef[0] * banos_por_mes["Mes_num"] + coef[1]


    fig_unidades = go.Figure()

    # Línea real
    fig_unidades.add_trace(go.Scatter(
        x=banos_por_mes["Mes"],
        y=banos_por_mes["Cod_bano"],
        mode="lines+markers",
        name="Baños Terminados",
        line=dict(width=2)
    ))

    # Promedio móvil
    fig_unidades.add_trace(go.Scatter(
        x=banos_por_mes["Mes"],
        y=banos_por_mes["PM3"],
        mode="lines",
        name="Promedio Móvil (3M)",
        line=dict(width=2, dash="dash")
    ))

    # Tendencia lineal
    fig_unidades.add_trace(go.Scatter(
        x=banos_por_mes["Mes"],
        y=banos_por_mes["Tendencia"],
        mode="lines",
        name="Tendencia Lineal",
        line=dict(width=2, dash="dot")
    ))

    fig_unidades.update_layout(
        title="Unidades Producidas (Baños Terminados) por Mes",
        xaxis_title="Mes",
        yaxis_title="Baños Terminados",
        template="simple_white"
    )

    st.plotly_chart(fig_unidades, use_container_width=True)


    # ============================
    # LEAD TIME PROMEDIO (DIARIO)
    # ============================

    lead_time_diario = df.drop_duplicates(subset='Cod_bano') \
        .groupby(df["Fecha"].dt.date)[COL_LEAD_TIME_UNIT] \
        .mean().reset_index()

    lead_time_diario.rename(columns={"Fecha": "Fecha_diaria"}, inplace=True)

    # ---- Promedio móvil de 7 días ----
    lead_time_diario["PM7"] = lead_time_diario[COL_LEAD_TIME_UNIT].rolling(7).mean()

    # ---- Tendencia lineal ----
    lead_time_diario["Dia_num"] = range(len(lead_time_diario))
    coef2 = np.polyfit(lead_time_diario["Dia_num"], lead_time_diario[COL_LEAD_TIME_UNIT], 1)
    lead_time_diario["Tendencia"] = coef2[0] * lead_time_diario["Dia_num"] + coef2[1]

    # ---- Promedio general ----
    promedio_general = lead_time_diario[COL_LEAD_TIME_UNIT].mean()


    fig_lead = go.Figure()

    # Línea real
    fig_lead.add_trace(go.Scatter(
        x=lead_time_diario["Fecha_diaria"],
        y=lead_time_diario[COL_LEAD_TIME_UNIT],
        mode="lines+markers",
        name="Lead Time Promedio Diario",
        line=dict(width=2)
    ))

    # Promedio móvil
    fig_lead.add_trace(go.Scatter(
        x=lead_time_diario["Fecha_diaria"],
        y=lead_time_diario["PM7"],
        mode="lines",
        name="Promedio Móvil (7 días)",
        line=dict(width=2, dash="dash")
    ))

    # Tendencia lineal
    fig_lead.add_trace(go.Scatter(
        x=lead_time_diario["Fecha_diaria"],
        y=lead_time_diario["Tendencia"],
        mode="lines",
        name="Tendencia Lineal",
        line=dict(width=2, dash="dot")
    ))

    # Línea horizontal de referencia
    fig_lead.add_hline(
        y=promedio_general,
        line=dict(width=2, dash="dot", color="gray"),
        annotation_text=f"Promedio General: {promedio_general:.1f} {UNIT_LABEL}",
        annotation_position="top left"
    )

    fig_lead.update_layout(
        title="Tiempo de Ciclo (Lead Time) Promedio Diario",
        xaxis_title="Fecha",
        yaxis_title=f"Lead Time Promedio ({UNIT_LABEL})",
        template="simple_white"
    )

    fig_lead.update_yaxes(tickformat=".1f")

    st.plotly_chart(fig_lead, use_container_width=True)

#------------------------
# Fin Pestaña 5: Evolución Temporal
#------------------------


#------------------------
# Pestaña 6: Eficiencia Operarios
#------------------------
with tab6:
    st.subheader("Análisis de Eficiencia por Operario")
    
    # Crear estructura de datos con Tipo_bano incluido
    operarios_flat = []
    for index, row in df.iterrows():
        for op in row["Operarios_list"]:
            operarios_flat.append({
                'Operario': op, 
                'T_Real_Unit': row[COL_T_REAL_UNIT], 
                'Cumple_TT': row['Cumple_TT'],
                'Tipo_bano': row['Tipo_bano']
            })
    df_op = pd.DataFrame(operarios_flat)
    
    # Crear mapa de colores consistente para cada operario
    operarios_unicos = sorted(df_op['Operario'].unique())
    colores_operarios = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    color_map_operarios = {op: colores_operarios[i % len(colores_operarios)] 
                           for i, op in enumerate(operarios_unicos)}
    
    # Obtener tipos de baño únicos
    tipos_bano = sorted(df_op['Tipo_bano'].unique())
    
    st.markdown("### Métricas Generales por Operario")
    st.markdown("---")
    
    # Métricas generales (sin separar por tipo de baño)
    op_metrics = df_op.groupby('Operario').agg(
        Total_Tareas=('Operario', 'count'),
        Avg_T_Real=('T_Real_Unit', 'mean'), 
        Pct_Cumple_TT=('Cumple_TT', lambda x: (x.astype(bool).mean() * 100))
    ).reset_index().sort_values('Avg_T_Real')
    
    colA, colB = st.columns(2)
    
    with colA:
        fig_real = go.Figure()
        for operario in op_metrics['Operario']:
            data_op = op_metrics[op_metrics['Operario'] == operario]
            fig_real.add_trace(go.Bar(
                x=data_op['Avg_T_Real'],
                y=data_op['Operario'],
                orientation='h',
                name=operario,
                marker_color=color_map_operarios[operario],
                text=[f"{val:.1f}" for val in data_op['Avg_T_Real']],
                textposition='outside',
                showlegend=True
            ))
        
        fig_real.update_layout(
            title=f"Tiempo Real Promedio por Operario ({UNIT_LABEL})",
            xaxis_title=f"Tiempo Real Promedio ({UNIT_LABEL})",
            yaxis_title="Operario",
            yaxis={'categoryorder':'total ascending'},
            height=max(400, len(op_metrics) * 30),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02
            )
        )
        fig_real.update_xaxes(tickformat=".1f")
        st.plotly_chart(fig_real, use_container_width=True)
    
    with colB:
        fig_tt = go.Figure()
        for operario in op_metrics['Operario']:
            data_op = op_metrics[op_metrics['Operario'] == operario]
            fig_tt.add_trace(go.Bar(
                x=data_op['Pct_Cumple_TT'],
                y=data_op['Operario'],
                orientation='h',
                name=operario,
                marker_color=color_map_operarios[operario],
                text=[f"{val:.1f}%" for val in data_op['Pct_Cumple_TT']],
                textposition='outside',
                showlegend=True
            ))
        
        fig_tt.update_layout(
            title="% Cumplimiento de Takt Time por Operario",
            xaxis_title="% Cumple TT",
            yaxis_title="Operario",
            xaxis_range=[0, 110],
            yaxis={'categoryorder':'total ascending'},
            height=max(400, len(op_metrics) * 30),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02
            )
        )
        fig_tt.update_xaxes(tickformat=".1f")
        st.plotly_chart(fig_tt, use_container_width=True)
    
    # Análisis por Tipo de Baño
    st.markdown("---")
    st.markdown("### Métricas por Tipo de Baño")
    
    for tipo in tipos_bano:
        st.markdown(f"#### Tipo de Baño: **{tipo}**")
        
        # Filtrar datos por tipo de baño
        df_op_tipo = df_op[df_op['Tipo_bano'] == tipo]
        
        if len(df_op_tipo) == 0:
            st.info(f"No hay datos disponibles para el tipo de baño {tipo}")
            continue
        
        # Calcular métricas por operario para este tipo de baño
        op_metrics_tipo = df_op_tipo.groupby('Operario').agg(
            Total_Tareas=('Operario', 'count'),
            Avg_T_Real=('T_Real_Unit', 'mean'), 
            Pct_Cumple_TT=('Cumple_TT', lambda x: (x.astype(bool).mean() * 100))
        ).reset_index().sort_values('Avg_T_Real')
        
        colC, colD = st.columns(2)
        
        with colC:
            fig_real_tipo = go.Figure()
            for operario in op_metrics_tipo['Operario']:
                data_op = op_metrics_tipo[op_metrics_tipo['Operario'] == operario]
                fig_real_tipo.add_trace(go.Bar(
                    x=data_op['Avg_T_Real'],
                    y=data_op['Operario'],
                    orientation='h',
                    name=operario,
                    marker_color=color_map_operarios[operario],
                    text=[f"{val:.1f} ({n} tareas)" for val, n in zip(data_op['Avg_T_Real'], data_op['Total_Tareas'])],
                    textposition='outside',
                    showlegend=True
                ))
            
            fig_real_tipo.update_layout(
                title=f"Tiempo Real Promedio - {tipo} ({UNIT_LABEL})",
                xaxis_title=f"Tiempo Real Promedio ({UNIT_LABEL})",
                yaxis_title="Operario",
                yaxis={'categoryorder':'total ascending'},
                height=max(350, len(op_metrics_tipo) * 30),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02
                )
            )
            fig_real_tipo.update_xaxes(tickformat=".1f")
            st.plotly_chart(fig_real_tipo, use_container_width=True)
        
        with colD:
            fig_tt_tipo = go.Figure()
            for operario in op_metrics_tipo['Operario']:
                data_op = op_metrics_tipo[op_metrics_tipo['Operario'] == operario]
                fig_tt_tipo.add_trace(go.Bar(
                    x=data_op['Pct_Cumple_TT'],
                    y=data_op['Operario'],
                    orientation='h',
                    name=operario,
                    marker_color=color_map_operarios[operario],
                    text=[f"{val:.1f}%" for val in data_op['Pct_Cumple_TT']],
                    textposition='outside',
                    showlegend=True
                ))
            
            fig_tt_tipo.update_layout(
                title=f"% Cumplimiento TT - {tipo}",
                xaxis_title="% Cumple TT",
                yaxis_title="Operario",
                xaxis_range=[0, 110],
                yaxis={'categoryorder':'total ascending'},
                height=max(350, len(op_metrics_tipo) * 30),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02
                )
            )
            fig_tt_tipo.update_xaxes(tickformat=".1f")
            st.plotly_chart(fig_tt_tipo, use_container_width=True)
        
        st.markdown("---")
#------------------------
# Fin Pestaña 6: Eficiencia Operarios
#------------------------
