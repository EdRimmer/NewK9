from PorcupineDetector import PorcupineDetector
from Gemini import Gemini
import asyncio
import pyaudio

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
CHUNK_SIZE = 512

class Main:

    def __init__(self):
       self.porcupine = None
       self.audioInQueue1 = None 
       self.gemini= None
       self.pya = pyaudio.PyAudio()
       self.wakeWordDetected=False

    async def listenAudio(self):
        mic_info = self.pya.get_default_input_device_info()
        stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        while True:
            data = await asyncio.to_thread(stream.read, CHUNK_SIZE)
            self.audioInQueue1.put_nowait(data)    
            if not self.wakeWordDetected:
               while self.audioInQueue1.qsize() > (SEND_SAMPLE_RATE/CHUNK_SIZE)*0.3: # retain 0.3s of data
                  await self.audioInQueue1.get()    


    async def mainLoop(self):
       self.porcupine = PorcupineDetector()
       self.gemini = Gemini(self.audioInQueue1)

       while True:
           print("into main loop")
           self.wakeWordDetected=False
           #await self.porcupine.waitForKeyword()
           self.wakeWordDetected=True

           print("Keyword detected")
           await self.gemini.run()
           print("out of main loop")
    
    async def run(self):
        async with asyncio.TaskGroup() as tg:
            self.audioInQueue1 = asyncio.Queue()
            tg.create_task(self.mainLoop())
            tg.create_task(self.listenAudio())

if __name__ == "__main__":
    main = Main()
    asyncio.run(main.run())
