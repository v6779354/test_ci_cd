import re
from datetime import time
from zoneinfo import ZoneInfo, available_timezones

# Русские названия городов и регионов -> часовой пояс IANA.
RU_NAMES = {
    "калининград": "Europe/Kaliningrad",
    "москва": "Europe/Moscow",
    "санкт-петербург": "Europe/Moscow",
    "петербург": "Europe/Moscow",
    "питер": "Europe/Moscow",
    "спб": "Europe/Moscow",
    "нижний новгород": "Europe/Moscow",
    "казань": "Europe/Moscow",
    "ростов-на-дону": "Europe/Moscow",
    "краснодар": "Europe/Moscow",
    "сочи": "Europe/Moscow",
    "воронеж": "Europe/Moscow",
    "волгоград": "Europe/Volgograd",
    "самара": "Europe/Samara",
    "ижевск": "Europe/Samara",
    "саратов": "Europe/Saratov",
    "ульяновск": "Europe/Ulyanovsk",
    "астрахань": "Europe/Astrakhan",
    "екатеринбург": "Asia/Yekaterinburg",
    "челябинск": "Asia/Yekaterinburg",
    "пермь": "Asia/Yekaterinburg",
    "уфа": "Asia/Yekaterinburg",
    "тюмень": "Asia/Yekaterinburg",
    "омск": "Asia/Omsk",
    "новосибирск": "Asia/Novosibirsk",
    "томск": "Asia/Tomsk",
    "барнаул": "Asia/Barnaul",
    "новокузнецк": "Asia/Novokuznetsk",
    "кемерово": "Asia/Novokuznetsk",
    "красноярск": "Asia/Krasnoyarsk",
    "иркутск": "Asia/Irkutsk",
    "чита": "Asia/Chita",
    "якутск": "Asia/Yakutsk",
    "владивосток": "Asia/Vladivostok",
    "хабаровск": "Asia/Vladivostok",
    "сахалин": "Asia/Sakhalin",
    "южно-сахалинск": "Asia/Sakhalin",
    "магадан": "Asia/Magadan",
    "камчатка": "Asia/Kamchatka",
    "петропавловск-камчатский": "Asia/Kamchatka",
    "анадырь": "Asia/Anadyr",
    "минск": "Europe/Minsk",
    "киев": "Europe/Kyiv",
    "кишинёв": "Europe/Chisinau",
    "рига": "Europe/Riga",
    "вильнюс": "Europe/Vilnius",
    "таллин": "Europe/Tallinn",
    "тбилиси": "Asia/Tbilisi",
    "ереван": "Asia/Yerevan",
    "баку": "Asia/Baku",
    "алматы": "Asia/Almaty",
    "астана": "Asia/Almaty",
    "ташкент": "Asia/Tashkent",
    "бишкек": "Asia/Bishkek",
    "душанбе": "Asia/Dushanbe",
    "лондон": "Europe/London",
    "париж": "Europe/Paris",
    "берлин": "Europe/Berlin",
    "рим": "Europe/Rome",
    "мадрид": "Europe/Madrid",
    "стамбул": "Europe/Istanbul",
    "дубай": "Asia/Dubai",
    "дели": "Asia/Kolkata",
    "пекин": "Asia/Shanghai",
    "шанхай": "Asia/Shanghai",
    "токио": "Asia/Tokyo",
    "сеул": "Asia/Seoul",
    "бангкок": "Asia/Bangkok",
    "сидней": "Australia/Sydney",
    "нью-йорк": "America/New_York",
    "вашингтон": "America/New_York",
    "чикаго": "America/Chicago",
    "денвер": "America/Denver",
    "лос-анджелес": "America/Los_Angeles",
    "сан-франциско": "America/Los_Angeles",
    "торонто": "America/Toronto",
    "мехико": "America/Mexico_City",
    "сан-паулу": "America/Sao_Paulo",
    "гринвич": "Etc/GMT",
}

# Буквенные аббревиатуры поясов -> часовой пояс IANA.
ABBREVIATIONS = {
    "utc": "UTC",
    "gmt": "Etc/GMT",
    "kalt": "Europe/Kaliningrad",
    "msk": "Europe/Moscow",
    "samt": "Europe/Samara",
    "yekt": "Asia/Yekaterinburg",
    "omst": "Asia/Omsk",
    "novt": "Asia/Novosibirsk",
    "krat": "Asia/Krasnoyarsk",
    "irkt": "Asia/Irkutsk",
    "yakt": "Asia/Yakutsk",
    "vlat": "Asia/Vladivostok",
    "magt": "Asia/Magadan",
    "pett": "Asia/Kamchatka",
    "cet": "Europe/Paris",
    "eet": "Europe/Kyiv",
    "est": "America/New_York",
    "cst": "America/Chicago",
    "mst": "America/Denver",
    "pst": "America/Los_Angeles",
    "jst": "Asia/Tokyo",
}

TIME_RE = re.compile(r"^\s*(\d{1,2})([.:])(\d{2})(?:\2(\d{2}))?\s*$")


def _normalize(name: str) -> str:
    return " ".join(name.strip().lower().replace("ё", "е").replace("_", " ").split())


def _build_index() -> dict[str, str]:
    index = {}
    for zone in available_timezones():
        # "Asia/Yekaterinburg" ищется и целиком, и по последней части — "yekaterinburg".
        index.setdefault(_normalize(zone), zone)
        index.setdefault(_normalize(zone.rsplit("/", 1)[-1]), zone)
    index.update({_normalize(k): v for k, v in ABBREVIATIONS.items()})
    index.update({_normalize(k): v for k, v in RU_NAMES.items()})
    return index


ZONE_INDEX = _build_index()


def find_zone(name: str) -> ZoneInfo | None:
    zone = ZONE_INDEX.get(_normalize(name))
    return ZoneInfo(zone) if zone else None


def parse_time(value: str) -> tuple[time, str] | None:
    """Разбирает "15.00", "15:00" или "15:00:30"; возвращает время и разделитель."""
    match = TIME_RE.match(value)
    if not match:
        return None
    hours, sep, minutes, seconds = match.groups()
    try:
        return time(int(hours), int(minutes), int(seconds or 0)), sep
    except ValueError:
        return None
