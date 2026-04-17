import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Balance de Riego", page_icon="💧", layout="wide")
st.title("Balance de Volumen en Riego - Cordoba")
st.markdown("**Cultivo: Naranjos | Suelo: Arcilloso 1m**")
st.markdown("---")

st.sidebar.header("Parametros del Suelo")
CC_vol      = st.sidebar.number_input("CC (cm3/cm3)",     value=0.396, step=0.001, format="%.3f")
PMP_vol     = st.sidebar.number_input("PMP (cm3/cm3)",    value=0.272, step=0.001, format="%.3f")
Prof        = st.sidebar.number_input("Profundidad (mm)", value=1000,  step=50)
frac_nap    = st.sidebar.slider("Fraccion NAP",      0.1, 1.0, 0.5,  0.05)
frac_consig = st.sidebar.slider("Fraccion consigna", 0.1, 1.0, 0.25, 0.05)

CC       = CC_vol  * Prof
PMP      = PMP_vol * Prof
IHD      = CC - PMP
NAP      = frac_nap * IHD
CONSIGNA = frac_consig * NAP

st.sidebar.markdown("---")
st.sidebar.write("CC =",       round(CC,1),       "mm")
st.sidebar.write("PMP =",      round(PMP,1),      "mm")
st.sidebar.write("IHD =",      round(IHD,1),      "mm")
st.sidebar.write("NAP =",      round(NAP,1),      "mm")
st.sidebar.write("Consigna =", round(CONSIGNA,1), "mm")

st.header("1. Carga de datos")
CSV_URL = "https://raw.githubusercontent.com/mamutla3-1982/BALANCE-HIDRICO/main/Cordoba.csv"
df = pd.read_csv(CSV_URL, sep=';', decimal='.', na_values=['n/d', '', ' '])
df.columns = df.columns.str.strip()
df['FECHA'] = pd.to_datetime(df['FECHA'], format='%d/%m/%y', errors='coerce')
df = df.dropna(subset=['FECHA']).sort_values('FECHA').reset_index(drop=True)
df = df.rename(columns={'Co06Precip': 'P', 'Co06ETo': 'ETo'})
df['P']    = pd.to_numeric(df['P'],   errors='coerce').fillna(0)
df['ETo']  = pd.to_numeric(df['ETo'], errors='coerce').fillna(0)
df['Anio'] = df['FECHA'].dt.year
df['DOY']  = df['FECHA'].dt.dayofyear
anos = sorted(df['Anio'].unique())
st.success("Datos cargados: " + str(len(df)) + " registros | " + str(anos[0]) + " - " + str(anos[-1]))

KC_PUNTOS = [(1,0.65),(60,0.65),(90,0.70),(120,0.75),(180,0.75),(240,0.70),(300,0.65),(365,0.65)]
dias_kc   = np.array([p[0] for p in KC_PUNTOS])
vals_kc   = np.array([p[1] for p in KC_PUNTOS])
KC_DIARIO = np.interp(np.arange(1, 366), dias_kc, vals_kc)
df['Kc']  = df['DOY'].apply(lambda d: KC_DIARIO[min(d, 365) - 1])
df['ETc'] = df['ETo'] * df['Kc']

st.markdown("---")
st.header("2. Figura 1 - Coeficiente Kc Naranjos")
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=list(range(1, 366)), y=list(KC_DIARIO),
    mode='lines', line=dict(color='#2ecc71', width=3)))
fig1.update_layout(title='Figura 1. Kc - Naranjos', xaxis_title='Dia del ano',
    yaxis_title='Kc', yaxis=dict(range=[0, 1]), height=380, template='plotly_white')
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")
st.header("3. Figura 2 - Necesidades netas de riego por ano")

resultados = {}
for ano in anos:
    datos = df[df['Anio'] == ano].copy().reset_index(drop=True)
    if len(datos) < 300:
        continue
    AC = 0.0
    NR_anual = 0.0
    ac_serie = []
    riego_dias = []
    for idx, row in datos.iterrows():
        AC += row['ETc'] - row['P']
        if AC < 0:
            AC = 0.0
        if AC >= CONSIGNA:
            NR_anual += AC
            riego_dias.append((idx, AC))
            AC = 0.0
        ac_serie.append(AC)
    resultados[ano] = {'NR': NR_anual, 'n_riegos': len(riego_dias),
                       'ac_serie': ac_serie, 'riego_dias': riego_dias, 'datos': datos}

anos_val = sorted(resultados.keys())
NR_vals  = np.array([resultados[a]['NR'] for a in anos_val])
NR_ord   = np.sort(NR_vals)[::-1]
n_total  = len(NR_vals)
prob_exc = np.arange(1, n_total + 1) / (n_total + 1) * 100
NR_50    = float(np.interp(50, prob_exc, NR_ord))
difs     = {a: abs(resultados[a]['NR'] - NR_50) for a in anos_val}
ano_med  = min(difs, key=difs.get)

colores = ['#e74c3c' if a == ano_med else '#3498db' for a in anos_val]
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=list(anos_val), y=list(NR_vals), marker_color=colores))
fig2.add_hline(y=NR_50, line_dash='dash', line_color='orange',
               annotation_text='P50=' + str(round(NR_50)) + ' mm')
fig2.update_layout(title='Figura 2. Necesidades netas de riego por ano',
    xaxis_title='Ano', yaxis_title='NR (mm)', height=400, template='plotly_white')
st.plotly_chart(fig2, use_container_width=True)

tabla_nr = pd.DataFrame({
    'Ano': anos_val,
    'NR (mm)': [round(resultados[a]['NR'], 1) for a in anos_val],
    'N riegos': [resultados[a]['n_riegos'] for a in anos_val],
    'Ano medio': ['SI' if a == ano_med else '' for a in anos_val]
})
with st.expander("Ver tabla NR por ano"):
    st.dataframe(tabla_nr, use_container_width=True)

st.markdown("---")
st.header("4. Figura 3 - Probabilidad de excedencia")
fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=list(NR_ord), y=list(prob_exc), mode='lines+markers',
    line=dict(color='#9b59b6', width=2.5),
    marker=dict(size=8, color='white', line=dict(color='#9b59b6', width=2))))
fig3.add_hline(y=50,    line_dash='dash', line_color='red', opacity=0.6)
fig3.add_vline(x=NR_50, line_dash='dash', line_color='red', opacity=0.6)
fig3.add_trace(go.Scatter(x=[NR_50], y=[50], mode='markers',
    marker=dict(size=14, color='red'), name='P50=' + str(round(NR_50)) + ' mm'))
fig3.update_layout(title='Figura 3. Probabilidad de excedencia',
    xaxis_title='Necesidades netas (mm)', yaxis_title='Probabilidad (%)',
    yaxis=dict(range=[0, 105]), height=400, template='plotly_white')
st.plotly_chart(fig3, use_container_width=True)

tabla_exc = pd.DataFrame({
    'Ano': anos_val,
    'NR (mm)': [round(v, 1) for v in NR_vals],
    'NR ordenada': [round(v, 1) for v in NR_ord],
    'N orden': list(range(1, n_total + 1)),
    'Prob exc (%)': [round(p, 1) for p in prob_exc]
})
with st.expander("Ver tabla probabilidades"):
    st.dataframe(tabla_exc, use_container_width=True)

st.markdown("---")
st.header("5. Ano medio: " + str(ano_med))
c1, c2, c3 = st.columns(3)
c1.metric("Ano medio", ano_med)
c2.metric("NR", str(round(resultados[ano_med]['NR'], 1)) + " mm")
c3.metric("N riegos", resultados[ano_med]['n_riegos'])

res_med  = resultados[ano_med]
ac_serie = res_med['ac_serie']
dias_p   = list(range(1, len(ac_serie) + 1))
datos_m  = res_med['datos']

fig4 = go.Figure()
fig4.add_trace(go.Scatter(x=dias_p, y=ac_serie, mode='lines',
    line=dict(color='#2c3e50', width=1.5), name='AC'))
fig4.add_hline(y=CONSIGNA, line_dash='dash', line_color='red',
               annotation_text='Consigna=' + str(round(CONSIGNA, 1)) + ' mm')
for (di, lam) in res_med['riego_dias']:
    fig4.add_vline(x=di + 1, line_color='#3498db', opacity=0.3, line_width=1)
fig4.update_layout(title='Figura 4. Agua consumida - Ano ' + str(ano_med),
    xaxis_title='Dia del ano', yaxis_title='Lamina agotada (mm)',
    height=400, template='plotly_white')
st.plotly_chart(fig4, use_container_width=True)

agua_disp = [IHD - ac for ac in ac_serie]
lam_disp  = [PMP + ad for ad in agua_disp]

fig5 = go.Figure()
fig5.add_trace(go.Scatter(
    x=dias_p + dias_p[::-1],
    y=lam_disp + [PMP] * len(dias_p),
    fill='toself', fillcolor='rgba(52,152,219,0.2)',
    line=dict(color='rgba(0,0,0,0)'), showlegend=False))
fig5.add_trace(go.Scatter(x=dias_p, y=lam_disp, mode='lines',
    line=dict(color='#3498db', width=2), name='Lamina disponible'))
fig5.add_hline(y=CC,  line_color='blue', line_width=2,
               annotation_text='CC=' + str(round(CC)) + ' mm')
fig5.add_hline(y=PMP + (IHD - CONSIGNA), line_dash='dash', line_color='red', line_width=2,
               annotation_text='Consigna=' + str(round(CONSIGNA, 1)) + ' mm')
fig5.add_hline(y=PMP, line_dash='dot', line_color='brown', line_width=1.5,
               annotation_text='PMP=' + str(round(PMP)) + ' mm')
fig5.update_layout(title='Figura 5. Lamina disponible - Ano ' + str(ano_med),
    xaxis_title='Dia del ano', yaxis_title='Lamina (mm)',
    yaxis=dict(range=[PMP * 0.9, CC * 1.05]),
    height=400, template='plotly_white')
st.plotly_chart(fig5, use_container_width=True)

filas = []
for i, (di, lam) in enumerate(res_med['riego_dias'], 1):
    if di < len(datos_m):
        fecha = datos_m.loc[di, 'FECHA'].strftime('%d/%m/%Y')
        doy   = int(datos_m.loc[di, 'DOY'])
    else:
        fecha = '---'
        doy   = di
    filas.append({'N': i, 'Fecha': fecha, 'Dia': doy, 'Lamina (mm)': round(lam, 1)})

st.markdown("**Tabla de riegos - Ano " + str(ano_med) + "**")
st.dataframe(pd.DataFrame(filas), use_container_width=True)

st.markdown("---")
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    tabla_nr.to_excel(writer,  sheet_name='NR anual',        index=False)
    tabla_exc.to_excel(writer, sheet_name='Prob excedencia',  index=False)
    pd.DataFrame(filas).to_excel(writer, sheet_name='Riegos ano medio', index=False)
buf.seek(0)
st.download_button("Descargar resultados en Excel", data=buf,
    file_name="balance_riego.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
