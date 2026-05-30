import json
import requests
import os
import pytz
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session, request

weather_bp = Blueprint('weather', __name__, template_folder='templates')


def get_local_time(tz_name):
    try:
        tz = pytz.timezone(tz_name)
        return datetime.now(tz).strftime('%H:%M:%S')
    except:
        return "Н/Д"


def get_weather_data_api(city_data):
    api_key = os.getenv("API_KEY")
    url = os.getenv("BASE_URL")
    params = {'key': api_key, 'q': f"{city_data['lat']},{city_data['lon']}", 'lang': 'ru'}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        if 'current' not in data or 'condition' not in data['current']:
            print(f"Неожиданный ответ API: {data}")
            return None
        return data
    except Exception as e:
        print(f"Ошибка запроса к API: {e}")
        return None


def get_clothing_recommendation(temp, wind_kph, humidity=None, condition_text="",
                                 feelslike_c=None, chance_of_rain=0, uv=0):
    cond = condition_text.lower()

    # Используем ощущаемую температуру если есть
    effective_temp = feelslike_c if feelslike_c is not None else temp

    if effective_temp < -20:
        base = "Арктический мороз! Термобельё, пуховик, зимние сапоги, балаклава и варежки."
    elif effective_temp < -10:
        base = "Сильный мороз. Тёплый пуховик, шапка, шарф и утеплённые сапоги."
    elif effective_temp < -5:
        base = "Хороший мороз. Зимняя куртка, шапка, шарф и тёплые перчатки."
    elif effective_temp < 0:
        base = "Лёгкий мороз. Зимняя куртка, шапка и перчатки не помешают."
    elif effective_temp < 5:
        base = "Холодно. Тёплая куртка и шапка."
    elif effective_temp < 10:
        base = "Прохладно. Плотная куртка или пальто."
    elif effective_temp < 15:
        base = "Свежо. Лёгкая куртка, джинсы или плотные брюки."
    elif effective_temp < 20:
        base = "Умеренно тепло. Рубашка или свитер, лёгкие брюки."
    elif effective_temp < 25:
        base = "Тепло. Футболка и лёгкие брюки или джинсы."
    elif effective_temp < 30:
        base = "Жарко. Футболка, шорты или лёгкое платье."
    else:
        base = "Очень жарко! Максимально лёгкая одежда и головной убор."

    extras = []

    # Ветер
    if wind_kph > 40:
        extras.append("очень сильный ветер — штормовка обязательна")
    elif wind_kph > 20:
        extras.append("ветрено — накинь ветровку")

    # Осадки
    if chance_of_rain >= 70:
        extras.append(f"дождь почти неизбежен ({chance_of_rain}%) — зонт обязателен")
    elif chance_of_rain >= 40:
        extras.append(f"возможен дождь ({chance_of_rain}%) — зонт не помешает")
    elif any(w in cond for w in ("дождь", "rain", "морось", "drizzle", "ливень", "shower")):
        extras.append("идёт дождь — зонт или дождевик")

    if any(w in cond for w in ("снег", "snow", "метель", "blizzard")):
        extras.append("снегопад — водонепроницаемая обувь")

    # УФ-индекс
    if uv >= 8:
        extras.append(f"УФ-индекс очень высокий ({uv:.0f}) — солнцезащитный крем обязателен")
    elif uv >= 5:
        extras.append(f"УФ-индекс повышенный ({uv:.0f}) — не забудь крем от солнца")

    # Влажность
    if humidity is not None and humidity > 80 and temp > 20:
        extras.append("высокая влажность — дышащие ткани в приоритете")

    if extras:
        return base + " " + "; ".join(e.capitalize() for e in extras) + "."
    return base


# Инициализация словарей городов
CITIES = {}
CITIES_LOWER = {}

try:
    with open('cities.json', 'r', encoding='utf-8') as f:
        CITIES = json.load(f)
        for display_name, data in CITIES.items():
            CITIES_LOWER[display_name.lower()] = {
                "data": data,
                "display_name": display_name
            }
except Exception as e:
    print(f"Ошибка чтения файла городов: {e}")


@weather_bp.route('/')
def index():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    return render_template('weather_index.html', cities=CITIES, bg_video="weather_main.mp4")


@weather_bp.route('/<city>')
def weather(city):
    if 'user_role' not in session:
        return redirect(url_for('login'))

    search_key = city.strip().lower()
    city_match = CITIES_LOWER.get(search_key)

    if not city_match:
        return redirect(url_for('weather.index'))

    city_data = city_match["data"]
    formatted_city = city_match["display_name"]

    weather_data = get_weather_data_api(city_data)
    if not weather_data:
        return render_template('city_weather.html', error="Ошибка API данных погоды", bg_video="default.mp4",
                               city=formatted_city)

    curr = weather_data['current']
    cond = curr['condition']['text'].lower()

    if "дождь" in cond or "rain" in cond or "морось" in cond:
        bg_video = "rain.mp4"
    elif "снег" in cond or "snow" in cond or "метель" in cond:
        bg_video = "snow.mp4"
    elif "ясно" in cond or "sunny" in cond or "clear" in cond:
        bg_video = "clear.mp4"
    else:
        bg_video = "clouds.mp4"

    return render_template('city_weather.html',
                           city=formatted_city,
                           temp=round(curr['temp_c']),
                           weather=curr['condition']['text'],
                           icon_url=f"https:{curr['condition']['icon']}",
                           local_time=get_local_time(city_data['tz']),
                           wind_speed=curr['wind_kph'],
                           humidity=curr['humidity'],
                           recommendation=get_clothing_recommendation(
                               curr['temp_c'],
                               curr['wind_kph'],
                               humidity=curr['humidity'],
                               condition_text=curr['condition']['text'],
                               feelslike_c=curr.get('feelslike_c'),
                               chance_of_rain=curr.get('chance_of_rain', 0),
                               uv=curr.get('uv', 0)
                           ),
                           bg_video=bg_video)