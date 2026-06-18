import os
import re
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Arquivos que vamos usar e gerar
ARQUIVO_DADOS = "dataset_consolidado.csv"
ARQUIVO_MODELO = "model.pkl"
ARQUIVO_VETORIZADOR = "vectorizer.pkl"

def limpar_texto(texto):
    if not isinstance(texto, str): return ""
    texto = texto.lower()
    # Mantém apenas letras e espaços
    texto = re.sub(r"[^a-záéíóúâêîôûãõàèìòùç\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def treinar_modelo():
    print("--- Treinando Modelo de Machine Learning ---")

    if not os.path.exists(ARQUIVO_DADOS):
        print("Erro: O arquivo de dados não existe!")
        return

    try:
        # Carrega os dados coletados
        df = pd.read_csv(ARQUIVO_DADOS)
        print(f"Total de notícias: {len(df)}")

        if len(df) < 5:
            print("Base de dados insuficiente para inicialização.")
            return

        # Limpa os textos para o treino
        df["texto_limpo"] = df["texto"].apply(limpar_texto)
        
        X = df["texto_limpo"]
        y = df["label"]
        
        # Divide 80% para treino e 20% para teste
        X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=0.2, random_state=42)

        # Transforma texto em números (TF-IDF)
        vetorizador = TfidfVectorizer(max_features=1000)
        X_treino_vet = vetorizador.fit_transform(X_treino)
        X_teste_vet = vetorizador.transform(X_teste)

        # Usa Regressão Logística para classificar
        modelo = LogisticRegression()
        modelo.fit(X_treino_vet, y_treino)

        # Calcula a acurácia básica
        preds = modelo.predict(X_teste_vet)
        acc = accuracy_score(y_teste, preds)
        
        print(f"Processamento concluído! Precisão: {acc:.2%}")

        # Salva os componentes de análise para usar no app
        joblib.dump(modelo, ARQUIVO_MODELO)
        joblib.dump(vetorizador, ARQUIVO_VETORIZADOR)
        print("Componentes salvos com sucesso!")

    except Exception as e:
        print(f"Erro no treinamento: {e}")

if __name__ == "__main__":
    treinar_modelo()
