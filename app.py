import streamlit as st
import pandas as pd
import os
import requests
import time

# 1. CONFIGURAÇÃO DA PÁGINA (Clean / Estilo Google)
st.set_page_config(
    page_title="Verificador de Espécies | Seleção Natural", 
    page_icon="🔍",
    layout="centered"
)

# 2. IDENTIDADE VISUAL E ESTILIZAÇÃO
# (Adicionada a estilização para o rodapé e sidebar com logo)
estilo_customizado = """
<style>
    /* Azul clássico do Google para os botões */
    .stButton>button { 
        background-color: #1a73e8; 
        color: white !important; 
        border-radius: 4px; 
        border: none; 
        padding: 8px 16px; 
        font-weight: 500; 
        transition: all 0.2s ease;
    }
    .stButton>button:hover { 
        background-color: #1557b0; 
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15); 
    }
    
    /* Centralizar o logo na sidebar */
    [data-testid="stSidebar"] div.stImage {
        display: flex;
        justify-content: center;
        padding-top: 20px;
    }
    
    /* Estilo para o rodapé */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        color: #5f6368;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #e0e0e0;
        z-index: 100;
    }
</style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)

# Link para o arquivo de logo (usando a imagem fornecida)
url_logo = "image_0.png" # Caminho local para a imagem fornecida. Certifique-se de que a imagem esteja na mesma pasta do script.

# 3. BARRA LATERAL - IDENTIDADE DA EMPRESA E LOGO
with st.sidebar:
    # Exibir o Logo da Seleção Natural
    if os.path.exists(url_logo):
        st.image(url_logo, width=180) # Ajuste a largura conforme necessário
    else:
        # Fallback caso a imagem não seja encontrada
        st.error(f"Logo 'image_0.png' não encontrado na pasta.")
        st.markdown("### Seleção Natural")

    st.markdown("### Sobre o Desenvolvedor")
    st.info("Este aplicativo foi desenvolvido pela **Seleção Natural**, abrindo espaço para biodiversidade.")
    
    st.markdown("[Acesse nosso site](https://www.selecaonatural.net/)") # Link para a empresa
    st.write("---")
    st.caption("Versão 1.0.0 | © 2026 Seleção Natural")

# Título principal
st.title("🔍 Verificador de Espécies")
st.markdown("Verificação do Grau de Ameaça de Extinção (MMA) com resolução taxonômica (GBIF).")

# Memória do app
if 'tabela_dados' not in st.session_state:
    st.session_state['tabela_dados'] = None

aba1, aba2 = st.tabs(["📋 Copiar e Colar", "📁 Upload de Planilha"])

with aba1:
    texto_nomes = st.text_area("Cole os nomes científicos aqui (um por linha):", height=150)
    if st.button("Carregar Nomes"):
        if texto_nomes.strip():
            lista_nomes = [nome.strip() for nome in texto_nomes.split('\n') if nome.strip()]
            st.session_state['tabela_dados'] = pd.DataFrame({"Espécie": lista_nomes})
        else:
            st.warning("Cole algum nome antes de carregar.")

with aba2:
    arquivo_upload = st.file_uploader("Ou faça upload do CSV", type=["csv"])
    if arquivo_upload is not None:
        st.session_state['tabela_dados'] = pd.read_csv(arquivo_upload)

# Se temos dados, mostra a tabela e a análise
if st.session_state['tabela_dados'] is not None:
    st.write("---")
    st.write("### Lista para Verificação:")
    
    df = st.session_state['tabela_dados'].copy()
    nome_coluna_especie = df.columns[0]
    
    st.dataframe(df, use_container_width=True)
    
    if st.button("Consultar Status e Sinônimos"):
        caminho_mma = "fauna-ameacada-2021.csv"
        
        if not os.path.exists(caminho_mma):
            st.error(f"Arquivo '{caminho_mma}' não encontrado na pasta.")
        else:
            try:
                df_mma = pd.read_csv(caminho_mma, sep=';', encoding='utf-8')
            except UnicodeDecodeError:
                df_mma = pd.read_csv(caminho_mma, sep=';', encoding='latin1')
            
            df_mma['Espécie ou Subespécie'] = df_mma['Espécie ou Subespécie'].astype(str).str.strip()
            mma_dict = dict(zip(df_mma['Espécie ou Subespécie'].str.lower(), df_mma['Sugestão de Categoria 2021']))
            
            status_final = []
            notas_taxon = []
            
            texto_progresso = st.empty()
            barra_progresso = st.progress(0)
            total_especies = len(df)
            
            for i, nome_original in enumerate(df[nome_coluna_especie]):
                nome_limpo = str(nome_original).strip()
                nome_lower = nome_limpo.lower()
                
                texto_progresso.text(f"Analisando: {nome_limpo}...")
                
                # 1. Tenta direto na lista do MMA
                if nome_lower in mma_dict:
                    status_final.append(mma_dict[nome_lower])
                    notas_taxon.append("Correspondência exata")
                else:
                    # 2. Busca sinônimos no GBIF
                    url_gbif = "https://api.gbif.org/v1/species/match"
                    encontrou_sinonimo = False
                    
                    try:
                        resp = requests.get(url_gbif, params={"name": nome_limpo, "strict": False}, timeout=5)
                        if resp.status_code == 200:
                            dados_gbif = resp.json()
                            if dados_gbif.get("matchType") != "NONE":
                                nome_aceite_gbif = dados_gbif.get("species", "")
                                if nome_aceite_gbif and nome_aceite_gbif.lower() != nome_lower:
                                    if nome_aceite_gbif.lower() in mma_dict:
                                        status_final.append(mma_dict[nome_aceite_gbif.lower()])
                                        notas_taxon.append(f"Sinônimo. Nome aceito (GBIF): {nome_aceite_gbif}")
                                        encontrou_sinonimo = True
                    except Exception:
                        pass 
                    
                    if not encontrou_sinonimo:
                        status_final.append("Não Ameaçada / Não Encontrada")
                        notas_taxon.append("-")
                        
                    time.sleep(0.1)
                
                barra_progresso.progress((i + 1) / total_especies)
            
            texto_progresso.empty()
            barra_progresso.empty()
            
            df["Status MMA (Portaria 148)"] = status_final
            df["Notas Taxonômicas (GBIF)"] = notas_taxon
            
            st.session_state['tabela_dados'] = df
            st.success("Análise finalizada!")
            st.rerun()

# Espaço extra para o rodapé
st.write(" " * 5)
st.write("---")

# Rodapé customizado com o logo e link
if os.path.exists(url_logo):
    st.markdown(
        f"""
        <div class="footer">
            <img src="{url_logo}" alt="Logo Seleção Natural" width="100" style="vertical-align: middle; margin-right: 10px;">
            Desenvolvido por <a href="https://www.selecaonatural.com.br/" target="_blank" style="color: #1a73e8; font-weight: bold;">Seleção Natural</a>
        </div>
        """, 
        unsafe_allow_html=True
    )
else:
     st.markdown(
        """
        <div class="footer">
            Desenvolvido por <a href="https://www.selecaonatural.com.br/" target="_blank" style="color: #1a73e8; font-weight: bold;">Seleção Natural</a>
        </div>
        """, 
        unsafe_allow_html=True
    )
