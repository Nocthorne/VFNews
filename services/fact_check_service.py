import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# URL da API do Google Fact Check
URL_GOOGLE = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

def mapear_veredito(texto_rating):
    """Traduz o que o Google responde para o nosso padrão."""
    if not texto_rating:
        return "Indeterminado"
    
    t = str(texto_rating).lower()
    
    falsos = ["false", "falso", "fake", "mostly false", "mentira", "misleading", "enganoso"]
    verdadeiros = ["true", "verdadeiro", "correto", "mostly true", "verdade"]
    parciais = ["partially true", "mixed", "inconclusive", "parcialmente verdadeiro", "misto"]
    
    if any(x in t for x in falsos):
        return "Falso"
    if any(x in t for x in verdadeiros):
        return "Verdadeiro"
    if any(x in t for x in parciais):
        return "Indeterminado"
    
    return "Indeterminado"

def consultar_fact_check_google(texto):
    """Consulta a API do Google para ver se a notícia já foi checada."""
    chave = os.getenv("GOOGLE_API_KEY", "").strip()

    if not chave or chave == "sua_chave_aqui":
        logger.warning("[AVISO] GOOGLE_API_KEY não configurada.")
        return {"encontrado": False, "resultados": []}

    try:
        params = {
            "key": chave,
            "query": texto,
            "languageCode": "pt",
            "pageSize": 3
        }
        
        logger.info("[INFO] Consultando Google Fact Check API...")
        res = requests.get(URL_GOOGLE, params=params, timeout=8)
        
        if res.status_code != 200:
            logger.warning(f"[AVISO] Google API retornou status {res.status_code}")
            return {"encontrado": False, "resultados": []}
        
        dados = res.json()

        claims = dados.get("claims", [])
        if not claims:
            logger.info("[INFO] Nenhuma checagem encontrada no Google Fact Check.")
            return {"encontrado": False, "resultados": []}

        formatados = []
        for c in claims:
            review = c.get("claimReview", [{}])[0]
            rating = review.get("textualRating", "Sem nota")
            formatados.append({
                "claim": c.get("text", ""),
                "publisher": review.get("publisher", {}).get("name", "Desconhecido"),
                "textualRating": rating,
                "url": review.get("url", ""),
                "veredito": mapear_veredito(rating)
            })
        
        logger.info(f"[INFO] Google Fact Check encontrou {len(formatados)} resultado(s).")
        return {"encontrado": True, "resultados": formatados}

    except requests.exceptions.Timeout:
        logger.error("[ERRO] Timeout ao consultar Google Fact Check API.")
        return {"encontrado": False, "resultados": [], "erro": "Timeout na API"}
    except Exception as e:
        logger.error(f"[ERRO] Erro ao consultar Google Fact Check API: {e}")
        return {"encontrado": False, "resultados": [], "erro": str(e)}
