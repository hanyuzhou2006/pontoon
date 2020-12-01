import json
import logging
import requests

from collections import defaultdict

from django.conf import settings
from six.moves.urllib.parse import quote

import pontoon.base as base

log = logging.getLogger(__name__)
MAX_RESULTS = 5


def get_google_translate_data(text, locale_code):
    api_key = settings.GOOGLE_TRANSLATE_API_KEY

    if not api_key:
        log.error("GOOGLE_TRANSLATE_API_KEY not set")
        return {
            "status": False,
            "message": "Bad Request: Missing api key.",
        }

    url = "https://translation.googleapis.com/language/translate/v2"

    payload = {
        "q": text,
        "source": "zh-CN",
        "target": locale_code,
        "format": "text",
        "key": api_key,
    }

    try:
        r = requests.post(url, params=payload)
        root = json.loads(r.content)

        if "data" not in root:
            log.error("Google Translate error: {error}".format(error=root))
            return {
                "status": False,
                "message": "Bad Request: {error}".format(error=root),
            }

        return {
            "status": True,
            "translation": root["data"]["translations"][0]["translatedText"],
        }

    except requests.exceptions.RequestException as e:
        log.error("Google Translate error: {error}".format(error=e))
        return {
            "status": False,
            "message": "Bad Request: {error}".format(error=e),
        }


def get_translation_memory_data(text, locale, pk=None):
    entries = (
        base.models.TranslationMemoryEntry.objects.filter(locale=locale)
        .minimum_levenshtein_ratio(text)
        .exclude(translation__approved=False, translation__fuzzy=False)
    )

    # Exclude existing entity
    if pk:
        entries = entries.exclude(entity__pk=pk)

    entries = entries.values("source", "target", "quality")
    entries_merged = defaultdict(lambda: {"count": 0, "quality": 0})

    # Group entries with the same target and count them
    for entry in entries:
        if (
            entry["target"] not in entries_merged
            or entry["quality"] > entries_merged[entry["target"]]["quality"]
        ):
            entries_merged[entry["target"]].update(entry)
        entries_merged[entry["target"]]["count"] += 1

    return sorted(
        entries_merged.values(), key=lambda e: (e["quality"], e["count"]), reverse=True,
    )[:MAX_RESULTS]

def get_google_cn_translate_data(text, locale_code):

    source = 'zh-CN'
    url = "https://translate.google.cn/translate_a/single?client=gtx&sl={source}&tl={to}&hl=zh-CN&dt=t&dt=bd&ie=UTF-8&oe=UTF-8&dj=1&source=icon&q={text}"\
    .format_map({"source": source, "to": locale_code, "text": quote(text.encode("utf-8"))})

    try:
        r = requests.get(url)
        root = json.loads(r.content)

        if "sentences" not in root:
            log.error("Google Translate error: {error}".format(error=root))
            return {
                "status": False,
                "message": "Bad Request: {error}".format(error=root),
            }

        return {
            "status": True,
            "translations": root["sentences"],
        }

    except requests.exceptions.RequestException as e:
        log.error("Google Translate error: {error}".format(error=e))
        return {
            "status": False,
            "message": "Bad Request: {error}".format(error=e),
        }
