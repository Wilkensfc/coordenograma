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
demanda_kw = st.sidebar.number_input("Demanda em KW", value=100.0)
icc_total = st.sidebar.number_input("Corrente de Curto-Circuito (Icc) [A]", value=1000.0)

st.sidebar.header("🔌 Transformadores (Separados por vírgula)")
kva_input = st.sidebar.text_input("Potências Nominais (KVA)", "112.5")
z_input = st.sidebar.text_input("Impedâncias (Z%)", "4.0")

st.sidebar.header("⏱️ Ajustes do Relé")
dt_fase = st.sidebar.number_input("Dial de tempo (DT) da Fase", value=0.1, step=0.01)
t_temp_neutro = st.sidebar.number_input("Tempo Temporizada Neutro (s)", value=0.5, step=0.1)

# --- PROCESSAMENTO DOS DADOS ---
try:
    # Converter strings de input para listas
    kva_list = [float(x.strip()) for x in kva_input.split(',')]
    z_list = [float(x.strip()) for x in z_input.split(',')]
    num_trafos = len(kva_list)

    if len(z_list) != num_trafos:
        st.error("Erro: A quantidade de KVA e Z% deve ser a mesma.")
        st.stop()

    # Cálculos de Base
    in_fase = demanda_kw / (1.732 * 13.8 * 0.92)
    ip_fase = 1.05 * in_fase

    # Cálculos Individuais por Trafo
    in_trafo_individual = [(kva * 1000) / (1.732 * 13800) for kva in kva_list]
    im_trafo_calculated = [8 * in_t for in_t in in_trafo_individual]
    
    ansi_f_i_list = []
    ansi_f_t_list = []
    
    for i, (z, in_t) in enumerate(zip(z_list, in_trafo_individual)):
        if z <= 4: t_ansi = 2.0
        elif z <= 5: t_ansi = 3.0
        elif z <= 6: t_ansi = 4.0
        else: t_ansi = 5.0
        
        ansi_f_i_list.append((100 / z) * in_t)
        ansi_f_t_list.append(t_ansi)

    # Im Total Edificação
    max_im = max(im_trafo_calculated)
    idx_max = im_trafo_calculated.index(max_im)
    im_total_edificacao = max_im + (sum(in_trafo_individual) - in_trafo_individual[idx_max])

    # Ajustes Finais
    i_inst_fase = 1.01 * im_total_edificacao
    i_inst_neutro = 0.33 * i_inst_fase
    ip_neutro = 0.33 * ip_fase

    # --- PLOTAGEM ---
    st.title("📊 Coordenograma de Proteção 13.8kV")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    plt.subplots_adjust(right=0.7)

    # Curvas de Proteção
    correntes_fase = np.logspace(np.log10(ip_fase * 1.01), np.log10(i_inst_fase), 500)
    tempos_fase = [calcular_tempo_ei(i, ip_fase, dt_fase) for i in correntes_fase]
    ax.loglog(list(correntes_fase) + [i_inst_fase, 10000], tempos_fase + [0.01, 0.01], color='blue', lw=2.5, label='Fase (51-EI/50)')
    
    ax.loglog([10000, i_inst_neutro, i_inst_neutro, ip_neutro, ip_neutro], 
              [0.01, 0.01, t_temp_neutro, t_temp_neutro, 300], color='green', lw=2.5, label='Neutro (50N/51N)')

    # Pontos de Inrush e ANSI
    colors = ['red', 'orange', 'purple', 'brown', 'cyan', 'magenta']
    for i in range(num_trafos):
        col = colors[i % len(colors)]
        ax.plot(im_trafo_calculated[i], 0.1, 'o', color=col, label=f'Inrush T{i+1} ({kva_list[i]}kVA)')
        ax.plot(ansi_f_i_list[i], ansi_f_t_list[i], 'x', color=col, markersize=8, mew=2, label=f'ANSI F T{i+1}')
        ax.plot(0.58 * ansi_f_i_list[i], ansi_f_t_list[i], '^', color=col, label=f'ANSI N T{i+1}')

    # Linhas de Referência
    ax.axvline(icc_total, color='black', label=f'Icc ({icc_total}A)')
    ax.axvline(in_fase, color='purple', ls='--', alpha=0.5, label=f'In Total ({in_fase:.1f}A)')

    # Formatação Técnica
    ax.set_ylim(0.01, 300)
    ax.set_xlim(1, 10000)
    
    def format_func(x, pos):
        return f"{x:.2f}" if x < 1 else f"{int(x)}"
    
    ax.yaxis.set_major_formatter(FuncFormatter(format_func))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.get_xaxis().set_scientific(False)
    plt.grid(True, which="both", ls="-", alpha=0.2)
    
    # Memorial de Cálculo
    trafos_txt = "".join([f"T{i+1}: {kva_list[i]}kVA - Z{z_list[i]}% - In:{in_trafo_individual[i]:.1f}A\n" for i in range(num_trafos)])
    memorial = (
        f"MEMORIAL DE CÁLCULO\n{'-'*25}\n"
        f"In Sistema: {in_fase:.2f} A\n"
        f"Ip Partida: {ip_fase:.2f} A\n"
        f"Im Edificação: {im_total_edificacao:.2f} A\n"
        f"Icc Max: {icc_total} A\n"
        f"{'-'*25}\n"
        f"DETALHE TRAFOS:\n{trafos_txt}"
        f"{'-'*25}\n"
        f"AJUSTES RELÉ:\n"
        f"51F: {ip_fase:.1f}A | DT: {dt_fase}\n"
        f"50F: {i_inst_fase:.1f}A | 0.01s\n"
        f"51N: {ip_neutro:.1f}A | {t_temp_neutro}s\n"
        f"50N: {i_inst_neutro:.1f}A | 0.01s"
    )
    plt.text(1.05, 0.5, memorial, transform=ax.transAxes, fontsize=9, verticalalignment='center', bbox=dict(facecolor='white', alpha=0.8))

    ax.legend(title="Legenda", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='x-small')
    st.pyplot(fig)

except Exception as e:
    st.warning("Aguardando preenchimento correto dos dados na barra lateral.")
