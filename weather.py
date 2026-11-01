import requests
import streamlit as st

@st.cache_data(ttl=600)
def get_darica_weather():
    """Darıca/Kocaeli için canlı hava durumu verisi çeker."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 40.7621,
        "longitude": 29.3843,
        "current_weather": "true",
        "timezone": "Europe/Istanbul"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json().get("current_weather", {})
            temp = data.get("temperature")
            wind = data.get("windspeed")
            code = data.get("weathercode")

            # WMO Hava Durumu Kodları Eşleştirmesi
            weather_map = {
                0: ("Açık", "☀️"),
                1: ("Çoğunlukla Açık", "🌤️"),
                2: ("Parçalı Bulutlu", "⛅"),
                3: ("Bulutlu", "☁️"),
                45: ("Sisli", "🌫️"),
                51: ("Çiseleyen Yağmur", "🌦️"),
                61: ("Hafif Yağmurlu", "🌧️"),
                63: ("Yağmurlu", "🌧️"),
                71: ("Kar Yağışlı", "🌨️"),
                80: ("Sağanak Yağmur", "🌧️"),
                95: ("Gök Gürültülü Fırtına", "⛈️")
            }
            desc, icon = weather_map.get(code, ("Güzel", "🌡️"))
            return {"temp": temp, "wind": wind, "desc": desc, "icon": icon}
    except Exception:
        return None
    return None