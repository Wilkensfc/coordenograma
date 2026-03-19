import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, ScalarFormatter

# Configuração da página Web
st.set_page_config(page_title="Coordenograma Pro", layout="wide")

def calcular_tempo_ei(I_falta, I_ajuste, DT):
    M = I_falta / I_ajuste
    if M <= 1.05: return 1000
    return DT * (80.0 / (M**2 - 1))

# --- INTERFACE NA BARRA LATERAL ---
st.sidebar.header("⚡ Parâmetros do Sistema")
demanda_kw = st.sidebar.number_input("Demanda (kW)", value=100.0)
in_fase = demanda_kw / (1.732 * 13.8 * 0.92)
ip_fase = 1.05 * in_fase
icc_total = st.sidebar.number_input("Icc Total (A)", value=1000.0)

st.sidebar.header("🔌 Transformadores")
kva_input = st.sidebar.text_input("KVA dos Trafos (ex: 112.5, 300)", "112.5")
z_input = st.sidebar.text_input("Z% dos Trafos (ex: 4, 5)", "4")

st.sidebar.header("⏱️ Ajustes do Relé")
dt_fase = st.sidebar.number_input("Dial de Tempo (DT) Fase", value=0.10, step=0.01)
t_temp_neutro = st.sidebar.number_input("Tempo Temporizada Neutro (s)", value=0.50, step=0.1)

# --- LÓGICA DE CÁLCULO ---
try:
    kva_list = [float(x) for x in kva_input.split(',')]
    z_list = [float(x) for x in z_input.split(',')]
    
    in_trafo_list = [(kva * 1000) / (1.732 * 13800) for kva in kva_list]
    im_trafo_list = [8 * in_t for in_t in in_trafo_list]
    
    # Cálculo Im Total
    max_im = max(im_trafo_list)
    im_total_edificacao = max_im + (sum(in_trafo_list) - in_trafo_list[im_trafo_list.index(max_im)])
    
    i_inst_fase = 1.01 * im_total_edificacao
    i_inst_neutro = 0.33 * i_inst_fase
    ip_neutro = 0.33 * ip_fase

    # --- PLOTAGEM ---
    st.title("📊 Coordenograma de Proteção 13.8kV")
    fig, ax = plt.subplots(figsize=(11, 7))

    # Curvas (Mesma lógica anterior)
    correntes_fase = np.logspace(np.log10(ip_fase * 1.01), np.log10(i_inst_fase), 500)
    tempos_fase = [calcular_tempo_ei(i, ip_fase, dt_fase) for i in correntes_fase]
    ax.loglog(list(correntes_fase) + [i_inst_fase, 10000], tempos_fase + [0.01, 0.01], color='blue', label='Fase (51/50)')
    
    ax.loglog([10000, i_inst_neutro, i_inst_neutro, ip_neutro, ip_neutro], 
              [0.01, 0.01, t_temp_neutro, t_temp_neutro, 300], color='green', label='Neutro (50N/51N)')

    # ANSI e Icc
    ax.axvline(icc_total, color='black', ls='-', label=f'Icc ({icc_total}A)')
    
    # Formatação de Eixo (0.01, 0.10...)
    ax.set_ylim(0.01, 300)
    ax.set_xlim(1, 10000)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.2f}" if x < 1 else f"{int(x)}"))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()

    # Exibe o Gráfico
    st.pyplot(fig)

    # Exibe Memorial abaixo
    st.subheader("📝 Memorial de Cálculo")
    st.code(f"In Total: {in_fase:.2f}A | Ip Fase: {ip_fase:.2f}A\nIm Total Edificacao: {im_total_edificacao:.2f}A\n50F (Inst): {i_inst_fase:.2f}A")

except Exception as e:
    st.error(f"Erro nos dados: Verifique se as listas de KVA e Z% batem.")
