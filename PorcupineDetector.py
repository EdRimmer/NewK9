import pvporcupine
from pvrecorder import PvRecorder
import os

class PorcupineDetector:

   library_path=None
   model_path=None
   access_key=str("Xci5M5dwg2zXFkLFSADvYL6fGe4te1Pa7H7CybgwBBMK18PpZvjgCw=="),
   keyword_paths=["./hey-canine_en_raspberry-pi_v3_0_0.ppn"]
   sensitivities=[0.5]
   porcupine=None
   recorder=None
   keywords=None

   def __init__(self):
   
       try:
         self.porcupine = pvporcupine.create(
           access_key="Xci5M5dwg2zXFkLFSADvYL6fGe4te1Pa7H7CybgwBBMK18PpZvjgCw==", 
           keyword_paths=self.keyword_paths,
           sensitivities=self.sensitivities,
           library_path=self.library_path,
           model_path=self.model_path)
       except pvporcupine.PorcupineInvalidArgumentError as e:
                      print("One or more arguments provided to Porcupine is invalid: ", args)
                      print(e)
                      raise e
       except pvporcupine.PorcupineActivationError as e:
                      print("AccessKey activation error")
                      raise e
       except pvporcupine.PorcupineActivationLimitError as e:
                      print("AccessKey '%s' has reached it's temporary device limit" % args.access_key)
                      raise e
       except pvporcupine.PorcupineActivationRefusedError as e:
                      print("AccessKey '%s' refused" % args.access_key)
                      raise e
       except pvporcupine.PorcupineActivationThrottledError as e:
                      print("AccessKey '%s' has been throttled" % args.access_key)
                      raise e
       except pvporcupine.PorcupineError as e:
                      print("Failed to initialize Porcupine")
                      raise e
   
       self.keywords = list()
       for x in self.keyword_paths:
           keyword_phrase_part = os.path.basename(x).replace('.ppn', '').split('_')
   
           if len(keyword_phrase_part) > 6:
                 self.keywords.append(' '.join(keyword_phrase_part[0:-6]))
           else:
                 self.keywords.append(keyword_phrase_part[0])
   
           print('Porcupine version: %s' % self.porcupine.version)
   
           self.recorder = PvRecorder(
               frame_length=self.porcupine.frame_length,
               device_index=-1)
           self.recorder.start()
   
   def waitForKeyword(self):
      found=False;
      while not found:
   
         try:
             pcm = self.recorder.read()
             result = self.porcupine.process(pcm)
             if result >= 0:
                 print('[%s] Detected %s' % (str(datetime.now()), self.keywords[result]))
                 # Report detection
                 matching_indexes=1
                 found=True
         except Exception:
                _LOGGER.exception("Read exception")
