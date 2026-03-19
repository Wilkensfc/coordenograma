import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, ScalarFormatter, LogLocator

# Configuração da Página
st.set_page_config(page_title="Coordenograma de Proteção Pro", layout="wide")

def calcular_tempo_ei(I_falta, I_ajuste, DT):
    M = I_falta / I_ajuste
    if M <= 1.05: return 1000.0
    return float(DT * (80.0 / (M**2 - 1)))

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

    # Cálculos Elétricos
    in_fase = demanda_kw / (1.732 * 13.8 * 0.92)
    ip_fase = 1.05 * in_fase
    in_trafos = [(kva * 1000) / (1.732 * 13800) for kva in kva_list]
    im_trafos = [8 * in_t for in_t in in_trafos]
    
    # Magnetização Total
    idx_max = np.argmax(im_trafos)
    im_total_edificacao = im_trafos[idx_max] + (sum(in_trafos) - in_trafos[idx_max])

    i_inst_fase = 1.01 * im_total_edificacao
    ip_neutro = 0.33 * ip_fase
    i_inst_neutro = 0.33 * i_inst_fase

    # --- GRÁFICO ---
    st.title("📊 Coordenograma de Proteção 13.8kV")
    fig, ax = plt.subplots(figsize=(12, 8))
    # Ajuste da margem direita para acomodar legenda e memorial
    plt.subplots_adjust(right=0.75)

    # 1. LINHAS VERTICAIS
    ax.axvline(in_fase, color='red', linestyle='--', lw=1.5, label=f'In Sistema ({in_fase:.1f}A)', zorder=1)
    ax.axvline(im_total_edificacao, color='orange', linestyle=':', lw=2, label=f'Im Total ({im_total_edificacao:.1f}A)', zorder=1)
    ax.axvline(icc_total, color='black', lw=2, label=f'Icc ({icc_total}A)', zorder=1)

    # 2. CURVAS
    c_fase = np.logspace(np.log10(ip_fase * 1.001), np.log10(i_inst_fase), 400)
    t_fase = [calcular_tempo_ei(i, ip_fase, dt_fase) for i in c_fase]
    ax.loglog(list(c_fase) + [i_inst_fase, 10000], list(t_fase) + [0.01, 0.01], color='blue', lw=3, label='Fase (51/50)', zorder=3)
    
    ax.loglog([10000, i_inst_neutro, i_inst_neutro, ip_neutro, ip_neutro], [0.01, 0.01, t_temp_neutro, t_temp_neutro, 300], color='green', lw=3, label='Neutro (50N/51N)', zorder=3)

    # 3. PONTOS TRAFOS
    colors = ['darkred', 'darkorange', 'purple', 'magenta', 'brown', 'teal', 'olive']
    for i in range(num_trafos):
        c = colors[i % len(colors)]
        ax.plot(im_trafos[i], 0.1, 'o', color=c, label=f'Inrush T{i+1}', zorder=4)
        ansi_i = (100 / z_list[i]) * in_trafos[i]
        t_ansi = 2.0 if z_list[i] <= 4 else 3.0
        ax.plot(ansi_i, t_ansi, 'x', mew=2, color=c, label=f'ANSI T{i+1}', zorder=5)

    # CONFIGURAÇÃO DO EIXO X (1 a 10.000)
    ax.set_xlim(1, 10000)
    ax.set_ylim(0.01, 300)
    
    ax.xaxis.set_major_locator(LogLocator(base=10.0, numticks=10))
    x_fmt = ScalarFormatter()
    x_fmt.set_scientific(False)
    ax.xaxis.set_major_formatter(x_fmt)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.2f}" if x < 1 else f"{int(x)}"))
    
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.xlabel("Corrente (A)")
    plt.ylabel("Tempo (s)")
    
    # --- MEMORIAL DE CÁLCULO (POSIÇÃO CORRIGIDA) ---
    trafos_txt = "".join([f"T{i+1}: {kva_list[i]}kVA | Z:{z_list[i]}%\n" for i in range(num_trafos)])
    memorial = (
        "RESUMO DOS CÁLCULOS\n"
        f"{'-'*25}\n"
        f"In Sistema: {in_fase:.2f} A\n"
        f"Ip (Partida): {ip_fase:.2f} A\n"
        f"Inrush Edif.: {im_total_edificacao:.2f} A\n"
        f"Icc (Curto): {icc_total} A\n"
        f"{'-'*25}\n"
        f"TRAFOS:\n{trafos_txt}"
        f"{'-'*25}\n"
        f"AJUSTES RELÉ:\n"
        f"51F: {ip_fase:.1f}A | DT {dt_fase}\n"
        f"50F: {i_inst_fase:.1f}A\n"
        f"51N: {ip_neutro:.1f}A | {t_temp_neutro}s\n"
        f"50N: {i_inst_neutro:.1f}A"
    )
    
    # O valor 0.15 no segundo parâmetro "desce" a tabela para longe da legenda
    plt.text(1.05, 0.15, memorial, transform=ax.transAxes, fontsize=9, 
             verticalalignment='bottom', bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray'))

    # Legenda com fonte menor para evitar sobreposição
    ax.legend(title="Legenda", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='x-small')
    
    st.pyplot(fig)
    import io

# Criar um buffer na memória para salvar a imagem
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')

# Botão de download da imagem
st.download_button(
    label="🖼️ Baixar Gráfico (PNG)",
    data=buf.getvalue(),
    file_name="coordenograma_protecao.png",
    mime="image/png"
)

# ... (após o comando st.pyplot(fig))
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Preparar download da imagem
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
        st.download_button(
            label="🖼️ Baixar Gráfico (PNG)",
            data=buf.getvalue(),
            file_name="coordenograma.png",
            mime="image/png"
        )

    with col2:
        # Botão do Memorial que já tínhamos
        st.download_button(
            label="📥 Baixar Memorial (TXT)",
            data=memorial,
            file_name="memorial.txt"
        )
    st.download_button("📥 Baixar Memorial", memorial, file_name="memorial.txt")

except Exception as e:
    st.info("Aguardando preenchimento dos dados...")
