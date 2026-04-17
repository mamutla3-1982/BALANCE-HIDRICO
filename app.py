# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

CSV_PATH = "/Users/luisalbertoalvarezalvarado/BALANCE_HIDRICO/Cordoba.csv"

# PARAMETROS DEL SUELO (arcilloso, profundidad 1 m)
CC_vol  = 0.396
PMP_vol = 0.272
Prof    = 1000

CC       = CC_vol  * Prof
PMP      = PMP_vol * Prof
IHD      = CC - PMP
NAP      = 0.5 * IHD
CONSIGNA = 0.25 * NAP

# COEFICIENTES Kc NARANJOS (citricos)
KC_PUNTOS = [
    (1,   0.65), (60,  0.65), (90,  0.70),
    (120, 0.75), (180, 0.75), (240, 0.70),
    (300, 0.65), (365, 0.65)
]
dias_kc   = np.array([p[0] for p in KC_PUNTOS])
vals_kc   = np.array([p[1] for p in KC_PUNTOS])
KC_DIARIO = np.interp(np.arange(1, 366), dias_kc, vals_kc)

# CARGA Y LIMPIEZA DE DATOS
df = pd.read_csv(CSV_PATH, sep=';', decimal='.', na_values=['n/d', '', ' '])
df.columns = df.columns.str.strip()
df['FECHA'] = pd.to_datetime(df['FECHA'], format='%d/%m/%y', errors='coerce')
df = df.dropna(subset=['FECHA'])
df = df.sort_values('FECHA').reset_index(drop=True)
df = df.rename(columns={'Co06Precip': 'P', 'Co06ETo': 'ETo'})
df['P']   = pd.to_numeric(df['P'],   errors='coerce').fillna(0)
df['ETo'] = pd.to_numeric(df['ETo'], errors='coerce').fillna(0)
df['Anio'] = df['FECHA'].dt.year
df['DOY']  = df['FECHA'].dt.dayofyear
df['Kc']   = df['DOY'].apply(lambda d: KC_DIARIO[min(d, 365) - 1])
df['ETc']  = df['ETo'] * df['Kc']
anos = sorted(df['Anio'].unique())

# BALANCE HIDRICO ANUAL - NECESIDADES NETAS DE RIEGO
resultados = {}

for ano in anos:
    datos = df[df['Anio'] == ano].copy().reset_index(drop=True)
    if len(datos) < 300:
        continue
    AC       = 0.0
    NR_anual = 0.0
    ac_serie   = []
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
    resultados[ano] = {
        'NR':         NR_anual,
        'n_riegos':   len(riego_dias),
        'ac_serie':   ac_serie,
        'riego_dias': riego_dias,
        'datos':      datos
    }

# PROBABILIDADES DE EXCEDENCIA
anos_val = sorted(resultados.keys())
NR_vals  = np.array([resultados[a]['NR'] for a in anos_val])
n_total  = len(NR_vals)
NR_ord   = np.sort(NR_vals)[::-1]
prob_exc = np.arange(1, n_total + 1) / (n_total + 1) * 100
NR_50    = np.interp(50, prob_exc, NR_ord)

# ANO MEDIO
difs    = {a: abs(resultados[a]['NR'] - NR_50) for a in anos_val}
ano_med = min(difs, key=difs.get)
res_med = resultados[ano_med]
ac_serie = res_med['ac_serie']
dias_p   = np.arange(1, len(ac_serie) + 1)

# FIGURA 1 - Coeficiente de cultivo Kc de los naranjos
plt.style.use('seaborn-v0_8-whitegrid')

fig1, ax1 = plt.subplots(figsize=(12, 5))
ax1.plot(range(1, 366), KC_DIARIO, color='#2ecc71', linewidth=2.5)
ax1.set_title('Figura 1. Coeficiente de cultivo Kc - Naranjos (Citricos)',
              fontsize=13, fontweight='bold')
ax1.set_xlabel('Dia del ano')
ax1.set_ylabel('Kc')
ax1.set_xlim(0, 365)
ax1.set_ylim(0, 1.0)
plt.tight_layout()
plt.savefig('figura1_kc.png', dpi=150, bbox_inches='tight')
plt.show()

# FIGURA 2 - Necesidades netas de riego por ano
fig2, ax2 = plt.subplots(figsize=(12, 5))
colores = ['#e74c3c' if a == ano_med else '#3498db' for a in anos_val]
ax2.bar(anos_val, NR_vals, color=colores, edgecolor='white', linewidth=0.5)
ax2.axhline(NR_50, color='orange', linestyle='--', linewidth=2)
ax2.set_title('Figura 2. Necesidades netas de riego por ano',
              fontsize=13, fontweight='bold')
ax2.set_xlabel('Ano')
ax2.set_ylabel('NR (mm)')
ax2.legend(handles=[
    mpatches.Patch(color='#3498db', label='NR anual'),
    mpatches.Patch(color='#e74c3c', label='Ano medio (' + str(ano_med) + ')'),
    mpatches.Patch(color='orange',  label='NR media P50 = ' + str(round(NR_50)) + ' mm')
], fontsize=10)
plt.tight_layout()
plt.savefig('figura2_NR_anual.png', dpi=150, bbox_inches='tight')
plt.show()

# FIGURA 3 - Probabilidad de excedencia de las necesidades netas
fig3, ax3 = plt.subplots(figsize=(12, 5))
ax3.plot(NR_ord, prob_exc, 'o-', color='#9b59b6', linewidth=2.5,
         markersize=7, markerfacecolor='white', markeredgewidth=2)
ax3.axhline(50,    color='red', linestyle='--', linewidth=1.5, alpha=0.7)
ax3.axvline(NR_50, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
ax3.scatter([NR_50], [50], color='red', s=120, zorder=5,
            label='P50 = ' + str(round(NR_50)) + ' mm')
ax3.set_title('Figura 3. Probabilidad de excedencia de las necesidades netas',
              fontsize=13, fontweight='bold')
ax3.set_xlabel('Necesidades netas (mm)')
ax3.set_ylabel('Probabilidad de excedencia (%)')
ax3.set_xlim(min(NR_ord) * 0.95, max(NR_ord) * 1.05)
ax3.set_ylim(0, 105)
ax3.legend(fontsize=11)
plt.tight_layout()
plt.savefig('figura3_prob_excedencia.png', dpi=150, bbox_inches='tight')
plt.show()

# FIGURA 4 - Evolucion anual del agua consumida (ano medio)
fig4, ax4 = plt.subplots(figsize=(12, 5))
ax4.plot(dias_p, ac_serie, color='#2c3e50', linewidth=1.5)
ax4.axhline(CONSIGNA, color='red', linestyle='--', linewidth=1.5)
for (di, lam) in res_med['riego_dias']:
    ax4.axvline(di + 1, color='#3498db', linewidth=0.8, alpha=0.6)
ax4.set_title('Figura 4. Evolucion anual del agua consumida - Ano ' + str(ano_med),
              fontsize=13, fontweight='bold')
ax4.set_xlabel('Dia del ano')
ax4.set_ylabel('Lamina agotada (mm)')
ax4.set_xlim(0, len(ac_serie))
ax4.legend(handles=[
    mpatches.Patch(color='#2c3e50', label='Agua consumida (AC)'),
    mpatches.Patch(color='red',     label='Consigna = ' + str(round(CONSIGNA, 1)) + ' mm'),
    mpatches.Patch(color='#3498db', alpha=0.6, label='Riego aplicado')
], fontsize=10)
plt.tight_layout()
plt.savefig('figura4_agua_consumida.png', dpi=150, bbox_inches='tight')
plt.show()

# FIGURA 5 - Lamina disponible en el suelo (ano medio)
agua_disp = np.array([IHD - ac for ac in ac_serie])

fig5, ax5 = plt.subplots(figsize=(12, 5))
ax5.fill_between(dias_p, PMP, PMP + agua_disp, alpha=0.3, color='#3498db')
ax5.plot(dias_p, PMP + agua_disp, color='#3498db', linewidth=1.5, label='Lamina disponible')
ax5.axhline(CC,  color='blue',  linestyle='-',  linewidth=2,
            label='CC = ' + str(round(CC)) + ' mm')
ax5.axhline(PMP + (IHD - CONSIGNA), color='red', linestyle='--', linewidth=2,
            label='Consigna = ' + str(round(CONSIGNA, 1)) + ' mm')
ax5.axhline(PMP, color='brown', linestyle=':', linewidth=1.5,
            label='PMP = ' + str(round(PMP)) + ' mm')
ax5.set_title('Figura 5. Lamina disponible en el suelo - Ano ' + str(ano_med),
              fontsize=13, fontweight='bold')
ax5.set_xlabel('Dia del ano')
ax5.set_ylabel('Lamina (mm)')
ax5.set_xlim(0, len(ac_serie))
ax5.set_ylim(PMP * 0.9, CC * 1.05)
ax5.legend(fontsize=10)
plt.tight_layout()
plt.savefig('figura5_lamina_disponible.png', dpi=150, bbox_inches='tight')
plt.show()

# RESUMEN EN CONSOLA
print("NR media P50 =", round(NR_50, 1), "mm")
print("Ano medio =", ano_med)
print("NR ano medio =", round(resultados[ano_med]['NR'], 1), "mm")
print("Numero de riegos =", resultados[ano_med]['n_riegos'])
