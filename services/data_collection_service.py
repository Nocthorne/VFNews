import os
import re
import logging
import pandas as pd
import requests
import random
import time
from datetime import datetime
from dotenv import load_dotenv
from factcheckexplorer.factcheckexplorer import FactCheckLib
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory

# Garantir consistência na detecção de idioma
DetectorFactory.seed = 42

# Constantes para as URLs das APIs/sites
URL_GNEWS = "https://gnews.io/api/v4/search"

load_dotenv()

logger = logging.getLogger(__name__)

class DataCollectionService:
    def __init__(self, db=None):
        self.db = db
        self.arquivo_csv = os.path.join(os.path.dirname(__file__), "..", "dataset_consolidado.csv")
        self.dados = []
        self.news_key = os.getenv("NEWS_API_KEY", "").strip()
        self.gnews_key = os.getenv("GNEWS_API_KEY", "").strip()
        self.google_fact_check_key = os.getenv("GOOGLE_API_KEY", "").strip()

        # LISTA COMPLETA DE TERMOS
        self.termos_completos = [
            "eleição", "urna eletrônica", "fraude", "voto", "campanha", 
            "lula", "bolsonaro", "pt", "fake news", "política", "desinformação",
            "pib brasil", "taxa selic", "inflação ipca", "banco central",
            "reforma tributária", "arcabouço fiscal", "ministério da fazenda",
            "stf", "supremo tribunal federal", "congresso nacional", "senado",
            "câmara dos deputados", "governo federal", "petrobras",
            "agronegócio", "mercado financeiro", "bolsa de valores", "b3",
            "auxílio brasil", "bolsa família", "fgts", "juros",
            "notícia política", "economia brasileira", "urgente brasil"
        ]
        
        # Termos reduzidos APENAS para a NewsAPI
        self.termos_newsapi = ["notícia", "brasil", "política", "economia", "mundo"]
    
    def limpar_texto(self, texto):
        if not isinstance(texto, str): return ""
        texto = texto.lower()
        texto = re.sub(r'[\U0001F300-\U0001F9FF]', '', texto)
        texto = re.sub(r'http\S+|www\S+', '', texto)
        texto = re.sub(r'[^a-záéíóúâêîôûãõàèìòùç\s]', '', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def is_portuguese(self, text):
        """Filtro rigoroso de idioma."""
        try:
            if not text or len(text.strip()) < 10: return False
            return detect(text) == 'pt'
        except:
            return False
    
    def pegar_label(self, rating):
        if not rating: return None
        r = str(rating).lower()
        falsos = ['false', 'falso', 'fake', 'mostly false', 'mentira', 'misleading', 'enganoso', 'improcedente', 'falsidade']
        verdadeiros = ['true', 'verdadeiro', 'correto', 'mostly true', 'verdade', 'procedente', 'real']
        if any(x in r for x in falsos): return "falso"
        if any(x in r for x in verdadeiros): return "verdadeiro"
        return None
    
    def coletar_news_api(self):
        logger.info("[INFO] === Coletando dados da NewsAPI ===")
        if not self.news_key or self.news_key == "sua_chave_aqui": return 0
        qtd = 0
        for i, termo in enumerate(self.termos_newsapi):
            try:
                print(f"[{i+1}/{len(self.termos_newsapi)}] NewsAPI: '{termo}'...", end='\r')
                url = f"https://newsapi.org/v2/everything?q={termo}&language=pt&sortBy=publishedAt&pageSize=50&apiKey={self.news_key}"
                res = requests.get(url, timeout=10)
                if res.status_code == 429: break
                
                artigos = res.json().get("articles", [])
                for art in artigos:
                    texto = art.get("title") or art.get("description")
                    if texto and "[Removed]" not in texto:
                        texto_limpo = self.limpar_texto(texto)
                        if self.is_portuguese(texto_limpo):
                            self.dados.append({
                                "texto": texto_limpo,
                                "label": "verdadeiro",
                                "fonte": art.get("source", {}).get("name", "NewsAPI"),
                                "data_coleta": datetime.now().strftime("%Y-%m-%d")
                            })
                            qtd += 1
                time.sleep(2)
            except: continue
        print(f"\n[INFO] NewsAPI: {qtd} notícias em PT.")
        return qtd

    def coletar_gnews(self):
        logger.info("[INFO] === Coletando da GNews ===")
        if not self.gnews_key or self.gnews_key == "sua_chave_aqui": return 0
        qtd = 0
        for i, termo in enumerate(self.termos_completos):
            try:
                print(f"[{i+1}/{len(self.termos_completos)}] GNews: '{termo}'...", end='\r')
                url = f"{URL_GNEWS}?q={termo}&lang=pt&country=br&max=20&token={self.gnews_key}"
                res = requests.get(url, timeout=10)
                if res.status_code == 429: break
                
                artigos = res.json().get("articles", [])
                for art in artigos:
                    texto = art.get("title") or art.get("description")
                    if texto:
                        texto_limpo = self.limpar_texto(texto)
                        if self.is_portuguese(texto_limpo):
                            self.dados.append({
                                "texto": texto_limpo,
                                "label": "verdadeiro",
                                "fonte": art.get("source", {}).get("name", "GNews"),
                                "data_coleta": datetime.now().strftime("%Y-%m-%d")
                            })
                            qtd += 1
                time.sleep(1.5)
            except: continue
        print(f"\n[INFO] GNews: {qtd} notícias em PT.")
        return qtd

    def coletar_fact_check(self):
        logger.info("[INFO] === Coletando dados do FactCheckExplorer ===")
        qtd = 0
        for i, termo in enumerate(self.termos_completos):
            try:
                print(f"[{i+1}/{len(self.termos_completos)}] FactCheck: '{termo}'...", end='\r')
                lib = FactCheckLib(query=termo, language='pt', num_results=50)
                raw = lib.fetch_data()
                if raw:
                    infos = lib.extract_info(raw)
                    for item in infos:
                        claim = item.get("claimReviewed")
                        rating = item.get("textualRating")
                        label = self.pegar_label(rating)
                        if claim and label:
                            texto_limpo = self.limpar_texto(claim)
                            if self.is_portuguese(texto_limpo):
                                self.dados.append({
                                    "texto": texto_limpo,
                                    "label": label,
                                    "fonte": item.get("publisher", "FactCheckExplorer"),
                                    "data_coleta": datetime.now().strftime("%Y-%m-%d")
                                })
                                qtd += 1
                time.sleep(0.5)
            except: continue
        print(f"\n[INFO] FactCheck: {qtd} checagens em PT.")
        return qtd

    def salvar_dataset(self):
        if not self.dados: return
        df_novos = pd.DataFrame(self.dados)
        
        if os.path.exists(self.arquivo_csv):
            df_antigo = pd.read_csv(self.arquivo_csv)
            df_final = pd.concat([df_antigo, df_novos]).drop_duplicates(subset=["texto"])
        else:
            df_final = df_novos.drop_duplicates(subset=["texto"])
            
        df_final.to_csv(self.arquivo_csv, index=False, encoding="utf-8")
        print(f"[SUCESSO] Dataset atualizado. Total: {len(df_final)} registros em Português.")

    def iniciar_coleta(self):
        print("=== INICIANDO ATUALIZAÇÃO DA BASE DE DADOS ===")
        self.coletar_news_api()
        self.coletar_gnews()
        self.coletar_fact_check()
        self.salvar_dataset()
        print("=== ATUALIZAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    service = DataCollectionService()
    service.iniciar_coleta()
