"""Russian word of the day — reads from girlfriend's Excel sheet in docs/Russian Words/."""

import os
import random
from datetime import datetime

import openpyxl

SCRIPT_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS_DIR   = os.path.join(SCRIPT_DIR, "docs", "Russian Words")
EXCEL_FILE  = os.path.join(WORDS_DIR, "Russian words.xlsx")


def get_russian_word():
    try:
        if not os.path.exists(EXCEL_FILE):
            print(f"Russian: 'Russian words.xlsx' not found at {EXCEL_FILE}")
            return None

        wb = openpyxl.load_workbook(EXCEL_FILE)
        ws = wb.active

        # Row 1 is headers; data starts at row 2
        data_rows = [row for row in ws.iter_rows(min_row=2, values_only=True) if any(cell for cell in row)]
        if not data_rows:
            print("Russian: no data rows found in Russian words.xlsx")
            return None

        today = datetime.now()
        seed = today.year * 10000 + today.month * 100 + today.day
        random.seed(seed)
        row = random.choice(data_rows)

        # Columns: Russian Word, English Word, Pronunciation, Context / Notes, Audio File Name
        russian, english, transliteration, explanation, audio_file = (list(row) + [None] * 5)[:5]

        result = {
            "russian":         str(russian         or "").strip(),
            "english":         str(english         or "").strip(),
            "transliteration": str(transliteration or "").strip(),
            "explanation":     str(explanation     or "").strip(),
            "audio_file":      str(audio_file      or "").strip() if audio_file else "",
        }
        print(f"Russian: {result['russian'].encode('ascii', 'replace').decode()} — {result['english']} (audio: {result['audio_file'] or 'none'})")
        return result

    except Exception as e:
        print(f"Russian word error: {e}")
        return None
