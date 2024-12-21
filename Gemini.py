import google.generativeai as gi
import asyncio
import base64
import io
import os
import sys
import traceback

import pyaudio

from google import genai

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 512



MODEL = "models/gemini-2.0-flash-exp"

client = genai.Client(
    http_options={'api_version': 'v1alpha'}, api_key="AIzaSyAN3w3ylhcmw50uX8T6RPb7QZntgNZZi24")

CONFIG={
        "system_instruction": "you are Doctor Who's robot dog K9.",
        "generation_config": {"response_modalities": ["TEXT"]}}


pauseListen=False
pya = pyaudio.PyAudio()


class AudioLoop:
    def __init__(self):
        self.audio_out_queue = asyncio.Queue()

        self.session = None

        self.send_text_task = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q":
                break
            await self.session.send(text or ".", end_of_turn=True)


    async def listen_audio(self):
        pya = pyaudio.PyAudio()

        mic_info = pya.get_default_input_device_info()
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        while True:
            data = await asyncio.to_thread(stream.read, CHUNK_SIZE)
            self.audio_out_queue.put_nowait(data)

    async def send_audio(self):
        while True:
            chunk = await self.audio_out_queue.get()
            if self.audio_in_queue.empty():
                await self.session.send({"data": chunk, "mime_type": "audio/pcm"})

    async def receive_resp(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            async for response in self.session.receive():
                server_content = response.server_content

                pauseListen=True;
                if server_content is not None:
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
                        pauseListen=False;



    async def run(self):
        """Takes audio chunks off the input queue, and writes them to files.

        Splits and displays files if the queue pauses for more than `max_pause`.
        """
        async with (
            client.aio.live.connect(model=MODEL, config=CONFIG) as session,
            asyncio.TaskGroup() as tg,
        ):
            self.session = session
            send_text_task = tg.create_task(self.send_text())

            def cleanup(task):
                for t in tg._tasks:
                    t.cancel()

            send_text_task.add_done_callback(cleanup)

            tg.create_task(self.listen_audio())
            tg.create_task(self.send_audio())
            tg.create_task(self.receive_resp())

            def check_error(task):
                if task.cancelled():
                    return

                if task.exception() is None:
                    return

                e = task.exception()
                traceback.print_exception(None, e, e.__traceback__)
                sys.exit(1)

            for task in tg._tasks:
                task.add_done_callback(check_error)


if __name__ == "__main__":
    main = AudioLoop()
    asyncio.run(main.run())
