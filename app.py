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
st.sidebar.info("Separe por vírgula para múltiplos trafos")
kva_input = st.sidebar.text_input("Potências Nominais (KVA)", "112.5")
z_input = st.sidebar.text_input("Impedâncias (Z%)", "4.0")

st.sidebar.header("⏱️ Ajustes do Relé")
dt_fase = st.sidebar.number_input("Dial de tempo (DT) da Fase", value=0.1, min_value=0.01, max_value=2.0, step=0.01)
t_temp_neutro = st.sidebar.number_input("Tempo Temporizada Neutro (s)", value=0.5, min_value=0.1, max_value=10.0, step=0.1)

# --- PROCESSAMENTO DOS DADOS COM TRATAMENTO DE ERRO ---
try:
    # Limpeza e conversão dos inputs
    kva_list = [float(x.strip()) for x in kva_input.split(',') if x.strip()]
    z_list = [float(x.strip()) for x in z_input.split(',') if x.strip()]
    num_trafos = len(kva_list)

    if len(z_list) != num_trafos:
        st.warning("⚠️ A quantidade de valores em KVA e Z% deve ser a mesma para gerar o gráfico.")
        st.stop()

    # Cálculos de Base (13.8kV fixo conforme solicitado)
    in_fase = demanda_kw / (1.732 * 13.8 * 0.92)
    ip_fase = 1.05 * in_fase

    # Cálculos Individuais por Trafo
    in_trafo_individual = [(kva * 1000) / (1.732 * 13800) for kva in kva_list]
    im_trafo_calculated = [8 * in_t for in_t in in_trafo_individual]
    
    ansi_f_i_list = []
    ansi_f_t_list = []
    
    for z, in_t in zip(z_list, in_trafo_individual):
        if z <= 4: t_ansi = 2.0
        elif z <= 5: t_ansi = 3.0
        elif z <= 6: t_ansi = 4.0
        else: t_ansi = 5.0
        ansi_f_i_list.append((100 / z) * in_t)
        ansi_f_t_list.append(t_ansi)

    # Corrente de Magnetização (Inrush) Total da Edificação
    max_im = max(im_trafo_calculated)
    idx_max = im_trafo_calculated.index(max_im)
    im_total_edificacao = max_im + (sum(in_trafo_individual) - in_trafo_individual[idx_max])

    # Ajustes das Funções de Proteção
    i_inst_fase = 1.01 * im_total_edificacao
    i_inst_neutro = 0.33 * i_inst_fase
    ip_neutro = 0.33 * ip_fase

    # --- PLOTAGEM DO GRÁFICO ---
    st.title("📊 Coordenograma de Proteção 13.8kV")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    # Ajuste para o memorial não cortar
    plt.subplots_adjust(right=0.7)

    # 1. Curva de Fase (51-EI / 50)
    # Gerar pontos até a instantânea
    correntes_fase = np.logspace(np.log10(ip_fase * 1.001), np.log10(i_inst_fase), 500)
    tempos_fase = [calcular_tempo_ei(i, ip_fase, dt_fase) for i in correntes_fase]
    # Adicionar o degrau da instantânea (0.01s)
    x_fase = list(correntes_fase) + [i_inst_fase, 10000]
    y_fase = list(tempos_fase) + [0.01, 0.01]
    ax.loglog(x_fase, y_fase, color='blue', lw=3, label='Fase (51-EI / 50)')
    
    # 2. Curva de Neutro (51N / 50N - Degrau)
    # [Fim do gráfico, Inst_N, Inst_N, Ip_N, Ip_N] -> Coordenadas do degrau
    x_neutro = [10000, i_inst_neutro, i_inst_neutro, ip_neutro, ip_neutro]
    y_neutro = [0.01, 0.01, t_temp_neutro, t_temp_neutro, 300]
    ax.loglog(x_neutro, y_neutro, color='green', lw=3, label='Neutro (50N/51N)')

    # 3. Pontos de Transformadores (Inrush e ANSI)
    colors = ['red', 'darkorange', 'purple', 'magenta', 'brown']
    for i in range(num_trafos):
        c = colors[i % len(colors)]
        # Inrush (Ponto de magnetização) em 0.1s
        ax.plot(im_trafo_calculated[i], 0.1, 'o', color=c, markersize=8, label=f'Inrush T{i+1} ({kva_list[i]}kVA)')
        # ANSI Fase
        ax.plot(ansi_f_i_list[i], ansi_f_t_list[i], 'x', color=c, markersize=10, mew=2, label=f'ANSI Fase T{i+1}')
        # ANSI Neutro (0.58 x ANSI Fase)
        ax.plot(0.58 * ansi_f_i_list[i], ansi_f_t_list[i], '^', color=c, markersize=8, label=f'ANSI Neutro T{i+1}')

    # 4. Linhas de Curto-Circuito e Nominal
    ax.axvline(icc_total, color='black', lw=2, label=f'Icc Total ({icc_total}A)')
    ax.axvline(in_fase, color='gray', ls='--', alpha=0.6, label=f'In Sistema ({in_fase:.1f}A)')

    # --- CONFIGURAÇÃO TÉCNICA DO GRÁFICO ---
    ax.set_ylim(0.01, 300)
    ax.set_xlim(1, 10000)
    
    # Formatador para mostrar 0.01 e 0.10 corretamente
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.2f}" if x < 1 else f"{int(x)}"))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.get_xaxis().set_scientific(False)
    
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.xlabel("Corrente (A)", fontsize=12)
    plt.ylabel("Tempo (s)", fontsize=12)
    
    # Memorial de Cálculo Lateral
    trafos_txt = "".join([f"T{i+1}: {kva_list[i]}kVA | Z:{z_list[i]}% | In:{in_trafo_individual[i]:.1f}A\n" for i in range(num_trafos)])
    memorial = (
        f"RESUMO DOS CÁLCULOS\n{'-'*25}\n"
        f"Demanda: {demanda_kw} kW\n"
        f"In Sistema: {in_fase:.2f} A\n"
        f"Ip (Partida): {ip_fase:.2f} A\n"
        f"Im (Inrush Total): {im_total_edificacao:.2f} A\n"
        f"Icc (Curto): {icc_total} A\n"
        f"{'-'*25}\n"
        f"DADOS DOS TRAFOS:\n{trafos_txt}"
        f"{'-'*25}\n"
        f"AJ
