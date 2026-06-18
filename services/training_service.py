import os
import re
import logging
import joblib
import pandas as pd
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)

class TrainingService:
    def __init__(self, db=None):
        self.db = db
        self.arquivo_dados = os.path.join(os.path.dirname(__file__), "..", "dataset_consolidado.csv")
        self.arquivo_modelo = os.path.join(os.path.dirname(__file__), "..", "model.pkl")
        self.arquivo_vetorizador = os.path.join(os.path.dirname(__file__), "..", "vectorizer.pkl")
        self.tamanho_minimo_dataset = 20
        self.test_size = 0.2
        self.random_state = 42
    
    def limpar_texto(self, texto):
        """Limpa o texto para treinamento."""
        if not isinstance(texto, str):
            return ""
        
        texto = texto.lower()
        texto = re.sub(r'[^a-záéíóúâêîôûãõàèìòùç\s]', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto
    
    def validar_dataset(self, df):
        """Valida o dataset antes do treinamento."""
        logger.info("[INFO] Validando dataset...")
        
        # Verificar se está vazio
        if df.empty:
            logger.error("[ERRO] Dataset vazio.")
            return False
        
        # Verificar tamanho mínimo
        if len(df) < self.tamanho_minimo_dataset:
            logger.error(f"[ERRO] Dataset muito pequeno ({len(df)} registros). Mínimo: {self.tamanho_minimo_dataset}")
            return False
        
        # Verificar número de classes
        classes = df['label'].unique()
        if len(classes) < 2:
            logger.error(f"[ERRO] Dataset contém apenas uma classe: {classes}")
            return False
        
        # Verificar balanceamento
        contagem = df['label'].value_counts()
        logger.info(f"[INFO] Distribuição de classes: {contagem.to_dict()}")
        
        # Verificar duplicatas
        duplicatas = df.duplicated(subset=['texto']).sum()
        if duplicatas > 0:
            logger.warning(f"[AVISO] {duplicatas} duplicatas encontradas no dataset.")
            df = df.drop_duplicates(subset=['texto'])
        
        logger.info(f"[INFO] Dataset validado com sucesso. Total de registros: {len(df)}")
        return True, df
    
    def treinar_modelo(self):
        """Executa a rotina de treinamento do modelo com a base de dados consolidada."""
        logger.info("[INFO] Iniciando treinamento do modelo...")
        
        # Verificar se arquivo de dados existe
        if not os.path.exists(self.arquivo_dados):
            logger.error(f"[ERRO] Arquivo de dados não encontrado: {self.arquivo_dados}")
            return False
        
        try:
            # Carregar dados
            df = pd.read_csv(self.arquivo_dados)
            logger.info(f"[INFO] Dataset carregado com {len(df)} registros.")
            
            # Validar dataset
            validacao = self.validar_dataset(df)
            if not validacao or not validacao[0]:
                logger.error("[ERRO] Base de dados inválida. Operação cancelada.")
                return False
            
            df = validacao[1]
            
            # Limpar textos
            logger.info("[INFO] Limpando textos...")
            df["texto_limpo"] = df["texto"].apply(self.limpar_texto)
            
            # Remover textos vazios
            df = df[df["texto_limpo"].str.len() > 0]
            
            if len(df) < self.tamanho_minimo_dataset:
                logger.error("[ERRO] Dataset insuficiente após limpeza.")
                return False
            
            # Preparar dados
            X = df["texto_limpo"]
            y = df["label"]
            
            logger.info(f"[INFO] Dividindo dataset: 80% treino, 20% teste")
            X_treino, X_teste, y_treino, y_teste = train_test_split(
                X, y, test_size=self.test_size, random_state=self.random_state, stratify=y
            )
            
            # Vetorização TF-IDF
            logger.info("[INFO] Aplicando TF-IDF...")
            vetorizador = TfidfVectorizer(max_features=1000, min_df=2, max_df=0.8)
            X_treino_vet = vetorizador.fit_transform(X_treino)
            X_teste_vet = vetorizador.transform(X_teste)
            
            logger.info(f"[INFO] Processamento TF-IDF concluído.")
            
            # Treinar modelo de regressão
            logger.info("[INFO] Treinando classificador de Regressão Logística...")
            modelo = LogisticRegression(max_iter=1000, random_state=self.random_state)
            modelo.fit(X_treino_vet, y_treino)
            
            # Validar resultados
            y_pred = modelo.predict(X_teste_vet)
            
            # Calcular métricas
            accuracy = accuracy_score(y_teste, y_pred)
            precision = precision_score(y_teste, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_teste, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_teste, y_pred, average='weighted', zero_division=0)
            
            logger.info(f"[INFO] Métricas de desempenho:")
            logger.info(f"[INFO] Precisão: {accuracy:.4f} ({accuracy*100:.2f}%)")
            logger.info(f"[INFO] Estabilidade: {f1:.4f}")
            
            # Salvar componentes
            logger.info("[INFO] Salvando componentes do sistema...")
            joblib.dump(modelo, self.arquivo_modelo)
            joblib.dump(vetorizador, self.arquivo_vetorizador)
            logger.info(f"[INFO] Componentes salvos com sucesso.")
            
            # Registrar atualização no banco de dados
            if self.db and self.db.is_connected():
                query = """
                INSERT INTO retreinamentos (data_inicio, data_fim, accuracy, precision, recall, f1_score, tamanho_dataset, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """
                self.db.execute_update(query, (
                    datetime.now(),
                    datetime.now(),
                    float(accuracy),
                    float(precision),
                    float(recall),
                    float(f1),
                    len(df),
                    "sucesso"
                ))
                logger.info("[INFO] Atualização registrada no banco de dados.")
            
            logger.info("[INFO] Processamento concluído com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"[ERRO] Erro durante o treinamento: {e}")
            
            # Registrar falha no banco de dados
            if self.db and self.db.is_connected():
                query = """
                INSERT INTO retreinamentos (data_inicio, data_fim, status)
                VALUES (%s, %s, %s);
                """
                self.db.execute_update(query, (datetime.now(), datetime.now(), "erro"))
            
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    service = TrainingService()
    service.treinar_modelo()
