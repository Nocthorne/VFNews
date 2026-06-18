import os
import re
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from factcheckexplorer.factcheckexplorer import FactCheckLib

load_dotenv()

class ColetorDados:
    def __init__(self):
        self.arquivo_csv = "dataset_consolidado.csv"
        self.dados = []
        self.news_key = os.getenv("NEWS_API_KEY")
        # Palavras-chave para buscar notícias e checagens de fatos
        self.termos = [
            "eleição", "urna eletrônica", "fraude eleitoral", "voto impresso", 
            "lula", "bolsonaro", "partido político", "fake news", "desinformação",
            "pib brasil", "inflação ipca", "taxa selic", "banco central",
            "reforma tributária", "arcabouço fiscal", "dólar hoje",
            "stf", "congresso nacional", "senado federal", "câmara dos deputados",
            "ministério da fazenda", "petrobras", "bndes", "agronegócio"
        ]

    def limpar_texto(self, texto):
        if not isinstance(texto, str): return ""
        texto = texto.lower()
        texto = re.sub(r'\s+', ' ', texto).strip()
        # Remove alguns caracteres especiais e pontuação
        texto = re.sub(r'[.,;!?"\'-]', '', texto)
        return texto

    def pegar_label(self, rating):
        # Converte o rating da API para verdadeiro ou falso
        r = rating.lower()
        falsos = ['false', 'falso', 'fake', 'mostly false', 'mentira', 'misleading', 'enganoso']
        verdadeiros = ['true', 'verdadeiro', 'correto', 'mostly true', 'verdade']
        
        if any(x in r for x in falsos): return "falso"
        if any(x in r for x in verdadeiros): return "verdadeiro"
        return None

    def coletar_news_api(self):
        print("Buscando notícias reais na NewsAPI...")
        if not self.news_key or self.news_key == "sua_chave_aqui":
            print("Aviso: NEWS_API_KEY não configurada.")
            return

        for termo in self.termos:
            url = f"https://newsapi.org/v2/everything?q={termo}&language=pt&apiKey={self.news_key}"
            try:
                res = requests.get(url, timeout=10)
                artigos = res.json().get("articles", [])
                for art in artigos:
                    texto = art.get("title", "")
                    if texto and "[Removed]" not in texto:
                        self.dados.append({
                            "texto": self.limpar_texto(texto),
                            "label": "verdadeiro",
                            "fonte": art.get("source", {}).get("name", "NewsAPI"),
                            "data_coleta": datetime.now().strftime("%Y-%m-%d")
                        })
            except:
                print(f"Erro ao buscar termo '{termo}' na NewsAPI")

    def coletar_fact_check(self):
        print("Buscando checagens de fatos no FactCheckExplorer...")
        for termo in self.termos:
            try:
                # Usa a biblioteca para pegar dados do Google Fact Check Explorer
                lib = FactCheckLib(query=termo, language=None, num_results=100)
                raw = lib.fetch_data()
                if raw:
                    infos = lib.extract_info(raw)
                    for item in infos:
                        claim = item.get("claimReviewed")
                        rating = item.get("textualRating")
                        label = self.pegar_label(rating)
                        
                        if claim and label:
                            self.dados.append({
                                "texto": self.limpar_texto(claim),
                                "label": label,
                                "fonte": item.get("publisher", "FactCheckExplorer"),
                                "data_coleta": datetime.now().strftime("%Y-%m-%d")
                            })
            except:
                print(f"Erro no FactCheckExplorer para o termo '{termo}'")

    def salvar_tudo(self):
        # Inicialização com dados de referência caso as APIs não retornem resultados
        if len(self.dados) < 5:
            print("Carregando dados de referência...")
            referencias = [
                # Verdadeiros (Política e Economia Brasil)
                {"texto": "Lula sanciona lei que recria o programa Minha Casa Minha Vida", "label": "verdadeiro", "fonte": "G1"},
                {"texto": "Copom mantém taxa Selic em 10,50% ao ano na última reunião", "label": "verdadeiro", "fonte": "Valor Econômico"},
                {"texto": "Câmara aprova texto-base da reforma tributária em dois turnos", "label": "verdadeiro", "fonte": "Folha de S.Paulo"},
                {"texto": "PIB do Brasil cresce 2,9% em 2023 impulsionado pelo agronegócio", "label": "verdadeiro", "fonte": "IBGE"},
                {"texto": "STF decide que guardas municipais integram sistema de segurança pública", "label": "verdadeiro", "fonte": "UOL"},
                {"texto": "Petrobras anuncia redução no preço da gasolina para distribuidoras", "label": "verdadeiro", "fonte": "CNN Brasil"},
                {"texto": "Congresso Nacional promulga emenda que amplia verba para saúde", "label": "verdadeiro", "fonte": "Agência Senado"},
                {"texto": "Dólar encerra o dia em queda frente ao real após dados da inflação", "label": "verdadeiro", "fonte": "Estadão"},
                {"texto": "Bolsa Família atende mais de 21 milhões de famílias em todo o país", "label": "verdadeiro", "fonte": "Portal Gov.br"},
                {"texto": "TSE afirma que urnas eletrônicas passaram por teste público de segurança", "label": "verdadeiro", "fonte": "Justiça Eleitoral"},
                
                # Falsos (Desinformação Política e Econômica Brasil)
                {"texto": "Governo vai confiscar a poupança para pagar dívida pública", "label": "falso", "fonte": "Boatos.org"},
                {"texto": "STF ordena prisão imediata de todos os críticos do governo", "label": "falso", "fonte": "Lupa"},
                {"texto": "Vídeo mostra fraude nas urnas durante apuração em tempo real", "label": "falso", "fonte": "Aos Fatos"},
                {"texto": "Nova lei permite que o governo tome casas com mais de dois quartos", "label": "falso", "fonte": "Fato ou Fake"},
                {"texto": "Brasil vai adotar moeda única com país vizinho para acabar com o Real", "label": "falso", "fonte": "E-farsas"},
                {"texto": "Projeto de lei quer proibir o consumo de carne bovina no país", "label": "falso", "fonte": "Boatos.org"},
                {"texto": "Documento prova que eleições foram manipuladas por satélites estrangeiros", "label": "falso", "fonte": "Lupa"},
                {"texto": "Banco Central vai cobrar taxa de 10% sobre cada transação via PIX", "label": "falso", "fonte": "Fato ou Fake"},
                {"texto": "Ministro da Fazenda anuncia fim do FGTS para todos os trabalhadores", "label": "falso", "fonte": "Aos Fatos"},
                {"texto": "Fotos mostram tanques de guerra cercando o Congresso Nacional hoje", "label": "falso", "fonte": "Boatos.org"}
            ]
            for ref in referencias:
                self.dados.append({
                    "texto": self.limpar_texto(ref["texto"]),
                    "label": ref["label"],
                    "fonte": ref["fonte"],
                    "data_coleta": datetime.now().strftime("%Y-%m-%d")
                })

        df = pd.DataFrame(self.dados)
        df = df.drop_duplicates(subset=["texto"])
        df.to_csv(self.arquivo_csv, index=False, encoding="utf-8")
        print(f"Dataset salvo com {len(df)} registros.")

    def iniciar(self):
        self.coletar_news_api()
        self.coletar_fact_check()
        self.salvar_tudo()

if __name__ == "__main__":
    c = ColetorDados()
    c.iniciar()
