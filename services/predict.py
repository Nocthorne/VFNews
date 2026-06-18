import re
import os
import logging
import joblib

logger = logging.getLogger(__name__)

# Caminhos dos arquivos gerados no treino
MODELO_PATH = os.path.join(os.path.dirname(__file__), "..", "model.pkl")
VETORIZADOR_PATH = os.path.join(os.path.dirname(__file__), "..", "vectorizer.pkl")

# Threshold para salvar automaticamente no dataset
AUTO_SAVE_THRESHOLD = 92

def limpar_texto(texto):
    """Limpa o texto para predição."""
    if not isinstance(texto, str):
        return ""
    
    texto = texto.lower()
    texto = re.sub(r"[^a-záéíóúâêîôûãõàèìòùç\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    
    return texto

def realizar_predicao_ml(texto_noticia, db=None):
    """Realiza análise de veracidade usando o modelo de Machine Learning local."""
    
    # Verificar se o modelo foi treinado
    if not os.path.exists(MODELO_PATH) or not os.path.exists(VETORIZADOR_PATH):
        logger.error("[ERRO] Modelo de ML não foi treinado ainda.")
        return {"erro": "O modelo de ML não foi treinado ainda."}

    try:
        # Carregamento dos componentes do modelo
        logger.info("[INFO] Carregando componentes do modelo...")
        modelo = joblib.load(MODELO_PATH)
        vetorizador = joblib.load(VETORIZADOR_PATH)

        texto_limpo = limpar_texto(texto_noticia)
        if not texto_limpo:
            logger.warning("[AVISO] Texto inválido para predição.")
            return {"erro": "Texto inválido."}

        # Transformar o texto e fazer a predição
        vetor = vetorizador.transform([texto_limpo])
        label = modelo.predict(vetor)[0]
        probs = modelo.predict_proba(vetor)[0]
        
        # Calcular o nível de confiança da análise
        classes = list(modelo.classes_)
        idx = classes.index(label)
        confianca = float(probs[idx] * 100)

        logger.info(f"[INFO] Análise realizada: {label} com {confianca:.2f}% de confiança.")
        
        # Salvar no dataset se confiança for alta
        if confianca >= AUTO_SAVE_THRESHOLD and db and db.is_connected():
            try:
                from services.dataset_service import salvar_no_dataset
                salvar_no_dataset(texto_noticia, label, "Modelo Local", confianca, db)
            except Exception as e:
                logger.warning(f"[AVISO] Não foi possível salvar predição no dataset: {e}")

        return {
            "label": label,
            "confianca": round(confianca, 2)
        }
    except Exception as e:
        logger.error(f"[ERRO] Erro na análise: {e}")
        return {"erro": f"Erro na análise: {e}"}
