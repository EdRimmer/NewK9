import aiohttp
import requests
import time
import asyncio
import base64
import io
import os
import sys
import traceback
from google import genai

#from google.genai.types import (
#    Tool,
#    FunctionDeclaration
#)

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000


MODEL = "models/gemini-2.0-flash-exp"


def search_the_internet_func(search_term):
    
    # get the API KEY here: https://developers.google.com/custom-search/v1/overview
    SEARCH_ENGINE_ID = "f666c6804cfdd4701"
    # get your Search Engine ID on your CSE control panel
    API_KEY = "AIzaSyA2cc0NiL4RLzYEOQWVX8TuU9cZ_ifbQ6s"
    
    
    # the search query you want
    query = "what time is it"
    # using the first page
    page = 1
    # constructing the URL
    # doc: https://developers.google.com/custom-search/v1/using_rest
    # calculating start, (page=2) => (start=11), (page=3) => (start=21)
    start = (page - 1) * 10 + 1
    url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start={start}"
    
    
    # make the API request
    data = requests.get(url).json()
    
    # get the result items
    search_items = data.get("items")
    # iterate over 10 results found
    for i, search_item in enumerate(search_items, start=1):
        try:
            long_description = search_item["pagemap"]["metatags"][0]["og:description"]
        except KeyError:
            long_description = "N/A"
        # get the page title
        title = search_item.get("title")
        # page snippet
        snippet = search_item.get("snippet")
        # alternatively, you can get the HTML snippet (bolded keywords)
        html_snippet = search_item.get("htmlSnippet")
        # extract the page url
        link = search_item.get("link")
        # print the results
        print("="*10, f"Result #{i+start-1}", "="*10)
        print("Title:", title)
        print("Description:", snippet)
        print("Long description:", long_description)
        print("URL:", link, "\n")

    return search_items

# Define the tool (function)
tool_search = {
    "function_declarations": [
        {
            "name": "search",
            "description": "allows a search term to be searched on the internet.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "search_term": {
                        "type": "STRING",
                        "description": "The search term"
                    },
                },
                "required": ["search_term"]
            }
        }
    ]
}


def set_light_values(brightness, color_temp):

    return {
        "brightness": brightness,
        "colorTemperature": color_temp,
    }

# Define the tool (function)
tool_set_light_values = {
    "function_declarations": [
        {
            "name": "set_light_values",
            "description": "Set the brightness and color temperature of a room light.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "brightness": {
                        "type": "NUMBER",
                        "description": "Light level from 0 to 100. Zero is off and 100 is full brightness"
                    },
                    "color_temp": {
                        "type": "STRING",
                        "description": "Color temperature of the light fixture, which can be `daylight`, `cool` or `warm`."
                    }
                },
                "required": ["brightness", "color_temp"]
            }
        }
    ]
}

client = genai.Client(
    http_options={'api_version': 'v1alpha'}, api_key="AIzaSyAN3w3ylhcmw50uX8T6RPb7QZntgNZZi24")

CONFIG={
        "system_instruction": "you are Doctor Who's robot dog K9. Never respond with  generated code but consider using function calls",
        "generation_config": {"response_modalities": ["TEXT"]},
        "tools": [tool_search]  }



class Gemini:
    def __init__(self, queue):
        #self.audio_out_queue = asyncio.Queue()
        self.audio_out_queue = queue

        self.session = None

        self.send_text_task = None
        self.lastResp = None
        self.pya = None #pyaudio.PyAudio()

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q":
                break
            await self.session.send(text or ".", end_of_turn=True)



    async def send_audio(self):
        self.lastResp=time.time()
        while True:
            chunk = await self.audio_out_queue.get()
            if time.time()-self.lastResp > 40:
               print("Timeout closing connection")
               break
            await self.session.send({"data": chunk, "mime_type": "audio/pcm"})

    async def receive_resp(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        self.lastResp=time.time()
        text=""
        while True:
            try:
               async for response in self.session.receive():
                   server_content = response.server_content
                   if server_content is not None:
                       print (server_content)
                       self.lastResp=time.time()
                       model_turn = server_content.model_turn
                       if model_turn is not None:
                           parts = model_turn.parts
   
                           for part in parts:
                               if part.function_call is not None:
                                  if part.function_call.function_name=="search_the_internet":
                                     result=search_the_internet(part.function_call.args)
 
                               if part.text is not None:
                                   partText=part.text.replace("?",".")
                                   partText=part.text.replace("irmative, Master","irmative")
                                   partText=partText.replace(",","");
                                   partText=partText.replace("Mark III","Mark 4");
                                   partText=partText.replace("Mark II","Mark 4");
                                   partText=partText.replace("Mark I","Mark 4");
                                   partText=partText.replace("Mark IV","Mark 4");
                                   text=text+partText
                                   print("***"+part.text)
                                   if "." in text:
                                      subs=text.split(".",1)
                                      text=subs[1] 
                                      print("sending "+subs[0])
                                      
                                      await self.speak(subs[0]+".")
                       if server_content.turn_complete is not None:
                             if server_content.turn_complete:
                                  await self.speak(text)
                                  print("sending final:"+text)
                                  text=""


   
                       server_content.model_turn = None
                       turn_complete = server_content.turn_complete
                       if turn_complete:
                           # If you interrupt the model, it sends a turn_complete.
                           # For interruptions to work, we need to stop playback.
                           # So empty out the audio queue because it may have loaded
                           # much more audio than has played yet.
                           print("Turn complete")
            except Exception as e: 
                print("Exception:" + str(e))
   
    async def speak (self, text):
        text=text.strip()
        url = "http://192.168.1.179:12102/api/tts"
        payload = {"voice": "nanotts:en-GB", "handleIntent":"yes", "play":"yes", "text":text}
        
        async with aiohttp.ClientSession() as session:
           async with session.get(url,params=payload) as response:
              data = await response.json(content_type='text/html')
              print(f"Completed task: {url}")
              return data

    async def run(self):
        #config_message = await client_websocket.recv()
        #config_data = json.loads(config_message)
        #config = config_data.get("setup", {})

        config={}

        config["system_instruction"]="you are Doctor Who's robot dog K9."
        config["generation_config"]={"response_modalities": ["TEXT"]}
        config["tools"] = [tool_set_light_values]

        async with (
            client.aio.live.connect(model=MODEL, config=config) as session,
            asyncio.TaskGroup() as tg,
        ):
            print("qq")

            send_text_task = tg.create_task(self.send_text())
            self.session=session

            def cleanup(task):
                for t in tg._tasks:
                    t.cancel()

            send_text_task.add_done_callback(cleanup)


            send_audio_task=tg.create_task(self.send_audio())
            receive_response_task=tg.create_task(self.receive_resp())

            send_audio_task.add_done_callback(cleanup)

            def check_error(task):
                if task.cancelled():
                    return

                if task.exception() is None:
                    return

                e = task.exception()
                traceback.print_exception(None, e, e.__traceback__)
                #sys.exit(1)

            for task in tg._tasks:
                task.add_done_callback(check_error)
  
