import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, ScalarFormatter

# Configuração da Página
st.set_page_config(page_title="Coordenograma de Proteção Pro", layout="wide")

def calcular_tempo_ei(I_falta, I_ajuste, DT):
    M = I_falta / I_ajuste
    if M <= 1.05: return 1000
    return DT * (80.0 / (M**2 - 1))

# --- INTERFACE LATERAL (INPUTS) ---
st.sidebar.header("📋 Parâmetros do Sistema")
demanda_kw = st.sidebar.number_input("Demanda em KW", value=100.0, step=10.0)
icc_total = st.sidebar.number_input("Corrente de Curto-Circuito (Icc) [A]", value=1000.0, step=100.0)

st.sidebar.header("🔌 Transformadores")
kva_input = st.sidebar.text_input("Potências Nominais (KVA)", "112.5")
z_input = st.sidebar.text_input("Impedâncias (Z%)", "4.0")

st.sidebar.header("⏱️ Ajustes do Relé")
dt_fase = st.sidebar.number_input("Dial de tempo (DT) da Fase", value=0.1, min_value=0.01, step=0.01)
t_temp_neutro = st.sidebar.number_input("Tempo Temporizada Neutro (s)", value=0.5, min_value=0.1, step=0.1)

# --- PROCESSAMENTO ---
try:
    kva_list = [float(x.strip()) for x in kva_input.split(',') if x.strip()]
    z_list = [float(x.strip()) for x in z_input.split(',') if x.strip()]
    num_trafos = len(kva_list)

    # Cálculos de Corrente
    in_fase = demanda_kw / (1.732 * 13.8 * 0.92)
    ip_fase = 1.05 * in_fase

    in_trafo_individual = [(kva * 1000) / (1.732 * 13800) for kva in kva_list]
    im_trafo_calculated = [8 * in_t for in_t in in_trafo_individual]
    
    ansi_f_i_list = []
    ansi_f_t_list = []
    for z, in_t in zip(z_list, in_trafo_individual):
        t_ansi = 2.0 if z <= 4 else (3.0 if z <= 5 else (4.0 if z <= 6 else 5.0))
        ansi_f_i_list.append((100 / z) * in_t)
        ansi_f_t_list.append(t_ansi)

    # CÁLCULO DA MAGNETIZAÇÃO TOTAL (CRÍTICO)
    max_im = max(im_trafo_calculated)
    idx_max = im_trafo_calculated.index(max_im)
    im_total_edificacao = max_im + (sum(in_trafo_individual) - in_trafo_individual[idx_max])

    i_inst_fase = 1.01 * im_total_edificacao
    i_inst_neutro = 0.33 * i_inst_fase
    ip_neutro = 0.33 * ip_fase

    # --- GRÁFICO ---
    st.title("📊 Coordenograma de Proteção 13.8kV")
    fig, ax = plt.subplots(figsize=(12, 8))
    plt.subplots_adjust(right=0.7)

    # 1. LINHAS DE REFERÊNCIA (ZORDER BAIXO PARA FICAR ATRÁS)
    ax.axvline(in_fase, color='red', ls='--', lw=1.5, alpha=0.8, zorder=1, label=f'In Total ({in_fase:.1f}A)')
    ax.axvline(im_total_edificacao, color='orange', ls=':', lw=2, zorder=1, label=f'Im Total ({im_total_edificacao:.1f}A)')
    ax.axvline(icc_total, color='black', lw=2, zorder=1, label=f'Icc ({icc_total}A)')

    # 2. CURVAS DE PROTEÇÃO
    c_fase = np.logspace(np.log10(ip_fase * 1.001), np.log10(i_inst_fase), 500)
    t_fase = [calcular_tempo_ei(i, ip_fase, dt_fase) for i in c_fase]
    ax.loglog(list(c_fase) + [i_inst_fase, 10000], list(t_fase) + [0.01, 0.01], color='blue', lw=3, zorder=3, label='Fase (51/50)')
    
    ax.loglog([10000, i_inst_neutro, i_inst_neutro, ip_neutro, ip_neutro], [0.01, 0.01, t_temp_neutro, t_temp_neutro, 300], color='green', lw=3, zorder=3, label='Neutro (50N/51N)')

    # 3. PONTOS DOS TRAFOS
    colors = ['darkred', 'darkorange', 'purple', 'magenta', 'brown']
    for i in range(num_trafos):
        c = colors[i % len(colors)]
        ax.plot(im_trafo_calculated[i], 0.1, 'o', color=c, zorder=4, label=f'Inrush T{i+1}')
        ax.plot(ansi_f_i_list[i], ansi_f_t_list[i], 'x', color=c, mew=2, zorder=5, label=f'ANSI F T{i+1}')

    # Ajustes de Eixo
    ax.set_ylim(0.01, 300)
    # Define o limite X começando um pouco antes da corrente nominal
    limite_x_min = max(1, in_fase * 0.5)
    ax.set_xlim(limite_x_min, 10000)
    
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.2f}" if x < 1 else f"{int(x)}"))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.get_xaxis().set_scientific(False)
    plt.grid(True, which="both", ls="-", alpha=0.2)
    
    # Memorial
    memorial = (
        "RESUMO DOS CALCULOS\n"
        f"In Sistema: {in_fase:.2f} A\n"
        f"Ip (Partida): {ip_fase:.2f} A\n"
        f"Inrush Edif.: {im_total_edificacao:.2f} A\n"
        f"Icc (Curto): {icc_total} A\n"
        f"{'-'*25}\n"
        f"AJUSTES RELÉ:\n"
        f"51F: {ip_fase:.1f}A | DT {dt_fase}\n"
        f"50F: {i_inst_fase:.1f}A\n"
        f"51N: {ip_neutro:.1f}A | {t_temp_neutro}s\n"
        f"50N: {i_inst_neutro:.1f}A"
    )
    plt.text(1.05, 0.5, memorial, transform=ax.transAxes, fontsize=10, verticalalignment='center', bbox=dict(facecolor='white', alpha=0.9))

    ax.legend(title="Legenda", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    st.pyplot(fig)

except Exception as e:
    st.info("Aguardando entrada de dados válidos na barra lateral...")
