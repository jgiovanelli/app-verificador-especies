import streamlit as st
import pandas as pd
import os
import requests
import time
import csv
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="Verificador de Espécies | Seleção Natural", 
    page_icon="🔍",
    layout="centered"
)

estilo_customizado = """
<style>
    /* Estilo dos botões */
    .stButton>button { 
        background-color: #1a73e8; color: white !important; border-radius: 4px; 
        border: none; padding: 8px 16px; font-weight: 500; transition: all 0.2s ease;
    }
    .stButton>button:hover { 
        background-color: #1557b0; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15); 
    }
    
    /* Estilo para o rodapé fixo */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f8f9fa; color: #5f6368;
        text-align: center; padding: 10px; font-size: 12px; border-top: 1px solid #e0e0e0;
        z-index: 100; display: flex; align-items: center; justify-content: center;
    }
    .main-content { margin-bottom: 70px; }
</style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # ==============================================================================
    # 2. BARRA LATERAL E MEMÓRIA
    # ==============================================================================
    with st.sidebar:
        # --- NOVIDADE: Adicionando o Logotipo Bold no topo ---
        try:
            # st.image lê o arquivo que você já subiu na mesma pasta do script
            st.image("SN - Logotipo Bold-03.png", use_container_width=True)
        except Exception as e:
            # Caso a imagem não seja encontrada, mostra o texto normal como backup
            st.markdown("### Seleção Natural")
        
        # O resto do conteúdo da sidebar continua igual
        st.markdown("### Sobre o Desenvolvedor")
        st.info("Este aplicativo foi desenvolvido pela **Seleção Natural**, abrindo espaço para biodiversidade.")
        st.markdown("[Acesse nosso site oficial](https://www.selecaonatural.net/)")
        st.write("---")
        st.caption("Versão 1.0 | © 2026 Seleção Natural")

    # Memórias do aplicativo
    if 'tabela_dados' not in st.session_state:
        st.session_state['tabela_dados'] = None
    if 'email_cadastrado_download' not in st.session_state:
        st.session_state['email_cadastrado_download'] = False

    # ==============================================================================
    # 3. CORPO DO APLICATIVO
    # ==============================================================================
    st.title("Verificador de Espécies - Fauna e Flora")
    st.markdown("Verificação do Grau de Ameaça de Extinção (MMA) com resolução taxonômica (GBIF).")

    aba1, aba2 = st.tabs(["📋 Copiar e Colar", "📁 Upload de Planilha"])

    with aba1:
        texto_nomes = st.text_area("Cole os nomes científicos aqui (um por linha):", height=150)
        if st.button("Carregar Nomes"):
            if texto_nomes.strip():
                lista_nomes = [nome.strip() for nome in texto_nomes.split('\n') if nome.strip()]
                st.session_state['tabela_dados'] = pd.DataFrame({"Espécie": lista_nomes})
                st.session_state['email_cadastrado_download'] = False # Reseta o download ao carregar nova lista
            else:
                st.warning("Cole algum nome antes de carregar.")

    with aba2:
        arquivo_upload = st.file_uploader("Ou faça upload do CSV", type=["csv"])
        if arquivo_upload is not None:
            st.session_state['tabela_dados'] = pd.read_csv(arquivo_upload)
            st.session_state['email_cadastrado_download'] = False

    if st.session_state['tabela_dados'] is not None:
        st.write("---")
        st.write("### Lista para Verificação:")
        
        df = st.session_state['tabela_dados'].copy()
        nome_coluna_especie = df.columns[0]
        st.dataframe(df, use_container_width=True)
        
        # LÓGICA DE CONSULTA
        if st.button("Consultar Status e Sinônimos"):
            caminho_fauna = "fauna-ameacada-2021.csv"
            caminho_flora = "flora-ameacada-2021.csv"
            
            if not os.path.exists(caminho_fauna) or not os.path.exists(caminho_flora):
                st.error(f"Certifique-se de que os arquivos '{caminho_fauna}' e '{caminho_flora}' estão na mesma pasta do aplicativo.")
            else:
                # 1. Carregar Fauna
                try:
                    df_fauna = pd.read_csv(caminho_fauna, sep=';', encoding='utf-8')
                except UnicodeDecodeError:
                    df_fauna = pd.read_csv(caminho_fauna, sep=';', encoding='latin1')
                
                # 2. Carregar Flora
                try:
                    df_flora = pd.read_csv(caminho_flora, sep=';', encoding='utf-8')
                except UnicodeDecodeError:
                    df_flora = pd.read_csv(caminho_flora, sep=';', encoding='latin1')
                
                # 3. Criar dicionários e juntá-los
                df_fauna['Espécie ou Subespécie'] = df_fauna['Espécie ou Subespécie'].astype(str).str.strip()
                dict_fauna = dict(zip(df_fauna['Espécie ou Subespécie'].str.lower(), df_fauna['Sugestão de Categoria 2021']))

                # Tratamento da Flora: Separa as palavras pelo espaço e pega apenas as duas primeiras (Gênero e Espécie), ignorando o autor
                df_flora['Espécie Limpa'] = df_flora['Espécie (FB 2020)'].astype(str).str.strip().apply(lambda x: ' '.join(x.split()[:2]))
                dict_flora = dict(zip(df_flora['Espécie Limpa'].str.lower(), df_flora['Sugestão de Categoria 2021']))
                
                # Dicionário unificado (Fauna + Flora)
                mma_dict = {**dict_fauna, **dict_flora}
                
                status_final = []
                notas_taxon = []
                texto_progresso = st.empty()
                barra_progresso = st.progress(0)
                total_especies = len(df)
                
                for i, nome_original in enumerate(df[nome_coluna_especie]):
                    nome_limpo = str(nome_original).strip()
                    nome_lower = nome_limpo.lower()
                    texto_progresso.text(f"Analisando: {nome_limpo}...")
                    
                    if nome_lower in mma_dict:
                        status_final.append(mma_dict[nome_lower])
                        notas_taxon.append("Correspondência exata")
                    else:
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

        # DASHBOARD E ÁREA DE DOWNLOAD COM CAPTURA DE LEADS
        if "Status MMA (Portaria 148)" in df.columns:
            st.write("---")
            st.write("### 📊 Resumo da Análise")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.write("**Contagem de Status:**")
                contagem = df["Status MMA (Portaria 148)"].value_counts()
                st.dataframe(contagem)
            with col2:
                st.write("**Gráfico de Ameaças:**")
                st.bar_chart(contagem)
            
            st.write("### 📥 Exportar Resultados")
            
            # Se o usuário ainda não colocou o e-mail, mostra o formulário
            if not st.session_state['email_cadastrado_download']:
                st.info("💡 **Para baixar a tabela completa (CSV), cadastre-se abaixo:**")
                with st.form("form_captura_leads"):
                    nome_lead = st.text_input("Seu Nome")
                    email_lead = st.text_input("Seu E-mail Profissional")
                    
                    # --- NOVIDADE: Adequação LGPD ---
                    # --- NOVIDADE: Adequação LGPD ---
                    st.markdown("""
                        <small style='color: #5f6368;'>
                        Ao informar seus dados, você concorda em receber comunicações da Seleção Natural. 
                        Seus dados estão seguros e você pode solicitar o descadastramento a qualquer momento 
                        enviando um e-mail para <b>contato@selecaonatural.net</b>.
                        </small>
                    """, unsafe_allow_html=True)
                    
                    aceite_lgpd = st.checkbox("Li e concordo com a Política de Privacidade.")
                    # --------------------------------
                    # --------------------------------
                    
                    btn_liberar = st.form_submit_button("Liberar Download da Tabela")
                    
                    if btn_liberar:
                        if not nome_lead or not email_lead:
                            st.error("⚠️ Preencha nome e e-mail para liberar o download.")
                        elif not aceite_lgpd:
                            st.error("⚠️ Você precisa concordar com a Política de Privacidade para continuar.")
                        else:
                            # Salva o contato em um arquivo CSV na sua pasta
                            arquivo_leads = "leads_capturados.csv"
                            cabecalho = not os.path.exists(arquivo_leads)
                            
                            with open(arquivo_leads, 'a', newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                if cabecalho:
                                    # Adicionei uma coluna para registrar que a pessoa deu o aceite (importante para auditoria)
                                    writer.writerow(['Data', 'Nome', 'Email', 'Origem', 'Aceite_LGPD'])
                                writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nome_lead, email_lead, 'Download Tabela', 'Sim'])
                            
                            st.session_state['email_cadastrado_download'] = True
                            st.success("Acesso liberado! Recarregando a página...")
                            time.sleep(1)
                            st.rerun()
            
            # Se o usuário JÁ colocou o e-mail, mostra o botão real de download
            else:
                st.success("✅ Acesso liberado! Clique no botão abaixo para salvar seu arquivo.")
                # Usando utf-8-sig para garantir que o Excel abra os acentos perfeitamente!
                csv_export = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="⬇️ Baixar Tabela Final (CSV)",
                    data=csv_export,
                    file_name="analise_especies_mma.csv",
                    mime="text/csv",
                )

    st.markdown('</div>', unsafe_allow_html=True)

with st.sidebar:
    st.write("---")
    senha_admin = st.text_input("Acesso Admin", type="password")
    if senha_admin == "suasenha123": # Escolha uma senha
        if os.path.exists("leads_capturados.csv"):
            with open("leads_capturados.csv", "rb") as f:
                st.download_button("📥 Baixar Lista de Leads", f, "leads_extraidos.csv", "text/csv")
        else:
            st.warning("Nenhum lead capturado ainda.")

# ==============================================================================
# 4. RODAPÉ HTML
# ==============================================================================
st.markdown(
    """
    <div class="footer">
        Desenvolvido por <a href="https://www.selecaonatural.net/" target="_blank" style="color: #1a73e8; font-weight: bold; text-decoration: none;">Seleção Natural</a>
    </div>
    """, 
    unsafe_allow_html=True
)
        
          
      
