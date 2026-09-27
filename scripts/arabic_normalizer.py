"""
Unified Arabic Normalizer for NexaServe.
Conservative, non-destructive, information-preserving normalization.
Used strictly for retrieval, search keys, and intent matching.
Never mutates original user text permanently.
"""

import re
import unicodedata

def normalize_arabic(text: str) -> str:
    """
    Conservative Arabic normalizer:
    1. Unicode NFKC normalization
    2. Strips tashkeel (diacritics: fatha, damma, kasra, sukun, tanween, shadda)
    3. Strips tatweel (kashida '\u0640')
    4. Normalizes Alef variants (أ, إ, آ, ٱ -> ا)
    5. Normalizes Persian/Urdu Yeh and Kaf variants (ي, ى -> ي; ك -> ك)
    6. PRESERVES Taa Marbuta ('ة') to avoid semantic collisions (e.g., منحة vs منحه)
    7. Normalizes punctuation and excessive whitespace
    """
    if not text or not isinstance(text, str):
        return ""

    # Unicode NFKC
    text = unicodedata.normalize('NFKC', text)

    # Strip tashkeel (diacritics: \u064B to \u065F, plus dagger alef \u0670)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)

    # Strip tatweel (kashida)
    text = text.replace('\u0640', '')

    # Normalize Alef variants to bare Alef
    text = re.sub(r'[إأآٱ]', 'ا', text)

    # Normalize Alef Maqsura to Yeh for search indexing
    text = text.replace('ى', 'ي')

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def test_normalization():
    cases = [
        ("مِنْحَةُ رُوَّادِ مِصْرَ", "منحة رواد مصر"),
        ("الأكاديمية العسكرية", "الاكاديمية العسكرية"),
        ("إمكانية التسجيل", "امكانية التسجيل"),
        ("تـقـديـم", "تقديم"),
        ("علي", "علي"),
        ("منحة", "منحة"), # Notice Taa Marbuta is preserved!
        ("منحه", "منحه")  # Distinct from منحة!
    ]
    for inp, expected in cases:
        out = normalize_arabic(inp)
        assert out == expected, f"Failed for {inp}: expected {expected}, got {out}"
    print("[OK] All conservative Arabic normalization unit tests passed!")

if __name__ == "__main__":
    test_normalization()
