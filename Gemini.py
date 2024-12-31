import aiohttp
from IntentManager import IntentManager
import requests
import time
import asyncio
import base64
import io
import os
import sys
import traceback
from google import genai


if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000


MODEL = "models/gemini-2.0-flash-exp"



client = genai.Client(
    http_options={'api_version': 'v1alpha'}, api_key="AIzaSyAN3w3ylhcmw50uX8T6RPb7QZntgNZZi24")


system_instructions="""
         You are Doctor Who's robot dog K9. Respond fairly briefly. 
         If you require real time information to answer or if I am commanding you to do something then before  answering send me a request in one the following REQUEST formats and wait for the response before answering: 
         1) REQUEST (requestWeatherInformation # weatherRequestGeographicLocation) where weatherRequestGeographicLocation is the location that the forcast is for, 
         2) REQUEST (shutdown) where 'shutdown' or 'shutdown system' are examples that should invoke this REQUEST
         3) REQUEST (requestTime), 
         4) REQUEST (requestDate),
         5) REQUEST (endOfConversation) where 'Goodbye' or 'Thank you' or 'that will be all' are examples that should invoke this REQUEST,
      """

CONFIG={
        "system_instruction": system_instructions,
        "generation_config": {"response_modalities": ["TEXT"]},
        "tools": []  }



class Gemini:
    def __init__(self, queue, manager):
        #self.audio_out_queue = asyncio.Queue()
        self.audio_out_queue = queue
        self.cancelled = False
        self.session = None

        self.send_text_task = None
        self.lastResp = None
        self.pya = None #pyaudio.PyAudio()
        self.intentManager=IntentManager(self)
        self.manager=manager

    async def shutdown(self):
        print("Gemini received shutdown system")
        await self.manager.shutdown();


    async def send_text(self):
        while True:
            await asyncio.sleep(10)
            #text = await asyncio.to_thread(input, "message > ")
            #if text.lower() == "q":
            #   break
            #await self.session.send(text or ".", end_of_turn=True)



    async def send_audio(self):
        self.lastResp=time.time()
        while True:
            chunk = await self.audio_out_queue.get()
            if time.time()-self.lastResp > 40 or self.cancelled==True:
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

                                      if self.intentManager.isIntent(subs[0]):
                                          resp=await self.intentManager.handleIntent(subs[0])
                                          print("Intent manager returned:"+resp)
                                          await self.session.send(resp, end_of_turn=True)
                                      else:
                                          print("sending "+subs[0])
                                          await self.speak(subs[0]+".")

                       if server_content.turn_complete is not None:
                             if server_content.turn_complete:
                                if self.intentManager.isIntent(text):
                                  resp=await self.intentManager.handleIntent(text)
                                  print("Intent manager returned:"+resp)
                                  await self.session.send(resp, end_of_turn=True)
                                else:
                                  await self.speak(text)
                                  print("sending final:"+text)
                                  text=""


   
                       server_content.model_turn = None

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

        async with (
            client.aio.live.connect(model=MODEL, config=CONFIG) as session,
            asyncio.TaskGroup() as tg,
        ):

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
  
