from PorcupineDetector import PorcupineDetector
import time
import paho.mqtt.client as mqtt #import the client1
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
       self.mqttClient = None
       self.audioInQueue1 = None 
       self.gemini= None
       self.pya = pyaudio.PyAudio()
       self.wakeWordDetected=False
       self.speaking=False

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
            if not self.speaking:
               self.audioInQueue1.put_nowait(data)    
               if not self.wakeWordDetected:
                  while self.audioInQueue1.qsize() > (SEND_SAMPLE_RATE/CHUNK_SIZE)*0.3: # retain 0.3s of data
                     await self.audioInQueue1.get()    


    async def mainLoop(self):
       self.porcupine = PorcupineDetector()
       self.gemini = Gemini(self.audioInQueue1)

       while True:
           print("into main loop")
           self.speaking=False
           self.wakeWordDetected=False
           await self.porcupine.waitForKeyword()
           self.wakeWordDetected=True
           self.mqttClient.publish("hermes/intent/StartEars","ON")

           print("Keyword detected")
           await self.gemini.run()
           print("out of main loop")
    
    async def run(self):
        async with asyncio.TaskGroup() as tg:
            self.audioInQueue1 = asyncio.Queue()
            tg.create_task(self.mainLoop())
            tg.create_task(self.listenAudio())


    def on_message(self, client, userdata, message):
        payload=str(message.topic).strip();
        payload=str(message.payload.decode("utf-8")).strip();
    
        if message.topic.strip()=="head/speaking":
            if payload=="OFF":
               print("Received stopped speaking")
               self.speaking=False
            else:
               print("Received start speaking")
               self.mqttClient.publish("hermes/intent/StopEars","ON")
               self.speaking=True


    def on_connect(self,client, userdata, flags, rc):
        print("Subscribing to topics")
        client.subscribe("head/speaking")
        client.subscribe("head/thinking")

    def connectToMqtt(self):
       broker_address="127.0.0.1"
       print("creating new instance")
       self.mqttClient = mqtt.Client("voiceDialog") #create new instance
       self.mqttClient.on_message=self.on_message #attach function to callback
       self.mqttClient.on_connect=self.on_connect #attach function to callback

       mqttConnected=False
       while not mqttConnected:
           try:
               print("connecting to broker")
               self.mqttClient.connect(broker_address,12183) #connect to broker
               mqttConnected=True
               print("Connected to MQQT broker")
           except:
               print("Did not connect to MQQT broker")
               time.sleep(1)

       self.mqttClient.loop_start() #start the loop

if __name__ == "__main__":
    main = Main()
    main.connectToMqtt()
    asyncio.run(main.run())

