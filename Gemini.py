import google.generativeai as gi
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

CONFIG={
        "system_instruction": "you are Doctor Who's robot dog K9.",
        "generation_config": {"response_modalities": ["TEXT"]}}




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
            if time.time()-self.lastResp > 20:
               print("Timeout closing connection")
               break
            await self.session.send({"data": chunk, "mime_type": "audio/pcm"})

    async def receive_resp(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        self.lastResp=time.time()
        while True:
            try:
               async for response in self.session.receive():
                   server_content = response.server_content
                   if server_content is not None:
                       self.lastResp=time.time()
                       model_turn = server_content.model_turn
                       if model_turn is not None:
                           parts = model_turn.parts
   
                           for part in parts:
                               if part.text is not None:
                                   print(part.text, end="")
   
                       server_content.model_turn = None
                       turn_complete = server_content.turn_complete
                       if turn_complete:
                           # If you interrupt the model, it sends a turn_complete.
                           # For interruptions to work, we need to stop playback.
                           # So empty out the audio queue because it may have loaded
                           # much more audio than has played yet.
                           print("Turn complete")
            except Exception as e: 
                print(e)
   

    async def run(self):
        async with (
            client.aio.live.connect(model=MODEL, config=CONFIG) as session,
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
  
