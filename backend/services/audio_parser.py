import os
import asyncio
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

class AudioStreamParser:
    def __init__(self, client_ws):
        self.client_ws = client_ws    # FastAPI websocket to user browser
        API_KEY = os.getenv("DEEPGRAM_API_KEY")
        self.deepgram = DeepgramClient(API_KEY)
        self.dg_connection = self.deepgram.listen.websocket.v("1")

    async def start_listening(self):
        def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            # We will stream this directly back to the FastAPI websocket for the user to see!
            asyncio.create_task(self.client_ws.send_json({"type": "transcript", "text": sentence}))
            
        def on_metadata(self, metadata, **kwargs):
            pass

        def on_error(self, error, **kwargs):
            pass

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
        self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        
        options = LiveOptions(
            model="nova-2-conversationalai",
            language="en",
            smart_format=True,
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            filler_words=True
        )

        if not self.dg_connection.start(options):
            print("Failed to connect to Deepgram")
            return False
            
        return True

    def process_audio_chunk(self, chunk: bytes):
        if self.dg_connection:
            self.dg_connection.send(chunk)
            
    def close(self):
        if self.dg_connection:
            self.dg_connection.finish()
