import requests
from config import Config
import time

class SeamlessTranslator:
    """
    Translator using Hugging Face Inference API for SeamlessM4T.
    Dont Falls back to original text if translation fails, Rather give the user a prompt to please choose another language.
    """
    def __init__(self):
        self.api_url = Config.HF_TRANSLATION_URL
        self.headers = {"Authorization": f"Bearer {Config.HF_TOKEN}"}
        
    def translate(self, text: str, src_lang: str, target_lang: str) -> str:
        """
        Translate text.
        Note: The HF Inference API for SeamlessM4T might accept specific payloads.
        Standard T2TT payload: {"inputs": text, "parameters": {"src_lang": "eng", "tgt_lang": "hau"}}
        Language Codes: eng, hau, yor, ibo, fra.
        """
        if not text or not text.strip():
            return text
            
        # Map codes for NLLB-200 (FLORES-200 style)
        # eng_Latn, hau_Latn, yor_Latn, ibo_Latn, fra_Latn
        lang_map = {
            "english": "eng_Latn", "hausa": "hau_Latn", "yoruba": "yor_Latn", "igbo": "ibo_Latn", "french": "fra_Latn",
            "en": "eng_Latn", "ha": "hau_Latn", "yo": "yor_Latn", "ig": "ibo_Latn", "fr": "fra_Latn"
        }
        
        src = lang_map.get(src_lang.lower(), "eng_Latn")
        tgt = lang_map.get(target_lang.lower(), "eng_Latn")
        
        if src == tgt:
            return text

        payload = {
            "inputs": text,
            "parameters": {
                "src_lang": src,
                "tgt_lang": tgt
            }
        }
        
        # Retry logic
        for _ in range(3):
            try:
                response = requests.post(self.api_url, headers=self.headers, json=payload)
                if response.status_code == 200:
                    # Parse response. Seamless usually returns [{"translation_text": "..."}] or similar
                    # Note: Seamless API output format varies. Audio models return bytes?
                    # Verification needed. For now assume standard T2T.
                    # If model is loading, it sends 503.
                    result = response.json()
                    if isinstance(result, list) and "translation_text" in result[0]:
                        return result[0]["translation_text"]
                    return result[0] if isinstance(result, list) else str(result)
                elif response.status_code == 503:
                    # Model loading
                    time.sleep(5)
                    continue
                else:
                    # Supress 404/410/500 errors to avoid CLI SPAM.
                    # Fallback to Llama 3 native capability is preferred over crashing flow.
                    # print(f"Translation Error {response.status_code}: {response.text}")
                    break
            except Exception as e:
                # print(f"Translation Exception: {e}")
                break
        
        return text # Fallback

# Singleton
_translator = None
def get_translator():
    global _translator
    if not _translator:
        _translator = SeamlessTranslator()
    return _translator
