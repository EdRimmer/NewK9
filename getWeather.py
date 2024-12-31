import requests
import math
import openmeteo_requests
import json
import requests_cache
import pandas as pd
from retry_requests import retry

def getWeather(city):
   try:
      print("requesing lat long for "+city)
      result_city = requests.get(url='https://geocoding-api.open-meteo.com/v1/search?name=' + city.strip())
      location = result_city.json()

      longitude=str(location['results'][0]['longitude'])
      latitude=str(location['results'][0]['latitude'])
   except Exception as e:
      print (str(e))
      longitude="-2.0"
      latitude="53.0"

   print(latitude)
   print(longitude)
   print(city)

   # Setup the Open-Meteo API client with cache and retry on error
   cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
   retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
   openmeteo = openmeteo_requests.Client(session = retry_session)

   # Make sure all required weather variables are listed here
   # The order of variables in hourly or daily is important to assign them correctly below
   url = "https://api.open-meteo.com/v1/forecast"

   params = {
	"latitude": latitude,
	"longitude": longitude,
	"current": ["temperature_2m", "precipitation", "rain", "showers", "snowfall", "weather_code", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
	"daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset", "daylight_duration", "precipitation_sum", "rain_sum", "showers_sum", "snowfall_sum", "wind_speed_10m_max", "wind_gusts_10m_max"],
	"models": "ukmo_uk_deterministic_2km"
   }
   responses = openmeteo.weather_api(url, params=params)

   # Process first location. Add a for-loop for multiple locations or weather models
   response = responses[0]
   
   # Current values. The order of variables needs to be the same as requested.
   current = response.Current()
   current_temperature_2m = current.Variables(0).Value()
   current_precipitation = current.Variables(1).Value()
   current_rain = current.Variables(2).Value()
   current_showers = current.Variables(3).Value()
   current_snowfall = current.Variables(4).Value()
   current_weather_code = current.Variables(5).Value()
   current_cloud_cover = current.Variables(6).Value()
   current_wind_speed_10m = current.Variables(7).Value()
   current_wind_direction_10m = current.Variables(8).Value()
   current_wind_gusts_10m = current.Variables(9).Value()

   if math.isnan(current_temperature_2m):
       current_temperature_2m=0
   if math.isnan(current_precipitation):
       current_precipitation=0
   if math.isnan(current_rain):
       current_rain=0
   if math.isnan(current_showers):
       current_showers=0
   if math.isnan(current_snowfall):
       current_snowfall=0
   if math.isnan(current_cloud_cover):
       current_cloud_cover=0
   if math.isnan(current_wind_speed_10m):
       current_wind_speed_10m=0
   if math.isnan(current_wind_direction_10m):
       current_wind_direction_10m=0
   if math.isnan(current_wind_gusts_10m):
       current_wind_gusts_10m=0

   weather_forecast={}
   weather_forecast["current_temperature"]=int(current_temperature_2m)
   weather_forecast["current_precipitation"]=int(current_precipitation)
   weather_forecast["current_rain"]=int(current_rain)
   weather_forecast["current_forecast"]=getWCText(int(current_weather_code))
   weather_forecast["current_cloud_cover_percentage"]=int(current_cloud_cover)
   weather_forecast["current_wind_speed"]=int(current_wind_speed_10m)
   weather_forecast["current_wind_direction"]=int(current_wind_direction_10m)
   
   # Process daily data. The order of variables needs to be the same as requested.
   daily = response.Daily()
   daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()
   daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()
   
   if math.isnan(daily_temperature_2m_max[0]):
       daily_temperature_2m_max[0]=0
   if math.isnan(daily_temperature_2m_min[0]):
       daily_temperature_2m_min[0]=0



   weather_forecast["todays_temperature_maximum"] = int(daily_temperature_2m_max[0])
   weather_forecast["todays_temperature_minimum"] = int(daily_temperature_2m_min[0])
   
   print(weather_forecast)
   return(str(weather_forecast))

def getWCText(wc):
    text={}
    text[0]="Clear sky"
    text[1]="Mainly clear"
    text[2]="partly cloudy"
    text[3]="overcast"
    text[45]="Fog"
    text[48]="Fog"
    text[51]="Light Drizzle"
    text[53]="Moderate Drizzle"
    text[55]="Dense Drizzle"
    text[56]="Light Freezing Drizzle"
    text[57]="Dence Freezing Drizzle"
    text[61]="Slight Rain"
    text[63]="Moderate Rain"
    text[65]="Heavy Rain"
    text[66]="Light Freezing Rain"
    text[67]="Heavy Freezing Rain"
    text[71]="Slight Snow fall"
    text[73]="Moderate Snow fall"
    text[75]="Heavy Snow fall"
    text[77]="Snowy"
    text[80]="slight Rain showers"
    text[81]="Moderate Rain showers"
    text[82]="Heavy Rain showers"
    text[85]="Slight Snow showers"
    text[86]="Heavy Snow showers"
    text[95]="Thunderstorm"
    text[96]="Thunderstorm with hail"
    text[99]="Thunderstorm with  heavy hail"

    return text[wc]
