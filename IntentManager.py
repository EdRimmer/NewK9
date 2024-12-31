import subprocess
import time
from getWeather import getWeather

class IntentManager:
   def __init__(self, manager):
       self.manager = manager

   def isIntent(self,text):
      print(text)
      return text.startswith("REQUEST")

   async def handleIntent(self,text):
      print("Intent manager received: ", text)
      try:
       
         if self.isIntent(text):
             params=text[text.find("(")+1:text.find(")")]
             print("Params="+params)
             parts=params.split("#")
             command=parts[0].strip()
             print("Command="+command)
   
             if command=="shutdown":
                  print("Intent manager handling shutdown")
                  await self.manager.shutdown();
                  return "OK"
             elif command=="requestTime":
                  return time.strftime('%l %M %p')
             elif command=="requestDate":
                  return time.strftime('%B %d')
             elif command=="requestWeatherInformation":
                  location="Poynton"
                  if len(parts)>1 and parts[1] is not None and len(parts[1])>2:
                     location=parts[1].strip()
                  data=getWeather(location)
                  print(data)
                  return data
             elif command=="requestTemperature":
                  location="Poynton"
                  if param is not None and len(param)>2:
                     location=param
                  data=getWeather(location)
                  print(data)
                  return data
             elif command=="endOfConversation":
                  print("Handling end of conversation")
                  self.manager.cancelled=True
                  return ""
             else:
                 return "No response"
      except Exception as e:
          print("exceptiom handling intent:"+str(e))
          return "No response"

