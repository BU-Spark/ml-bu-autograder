"""
This file was created with AI help:
https://chatgpt.com/share/6800049c-3ae8-800f-82fd-5a9aae0d2771

ONLY FOR TESTING NOT CURRENTLY USED.
"""

import json

import requests
import time
import logging

from pydantic import BaseModel, Field
from typing import List, Optional


class Word(BaseModel):
    word: str
    offset: str
    duration: str
    offsetInTicks: float
    durationInTicks: float
    offsetMilliseconds: int
    durationMilliseconds: int
    confidence: float


class NBest(BaseModel):
    confidence: float
    lexical: str
    itn: str
    maskedITN: str
    display: str
    words: Optional[List[Word]] = None


class RecognizedPhrase(BaseModel):
    recognitionStatus: str
    channel: int
    offset: str
    duration: str
    offsetInTicks: float
    durationInTicks: float
    offsetMilliseconds: int
    durationMilliseconds: int
    speaker: Optional[int] = Field(default=None)
    nBest: List[NBest]


class CombinedRecognizedPhrase(BaseModel):
    channel: int
    lexical: str
    itn: str
    maskedITN: str
    display: str


class TranscriptionResult(BaseModel):
    source: str
    timestamp: str
    durationInTicks: int
    durationMilliseconds: int
    duration: str
    combinedRecognizedPhrases: List[CombinedRecognizedPhrase]
    recognizedPhrases: List[RecognizedPhrase]


class AzureSpeechClient:
    def __init__(self, endpoint: str, subscription_key: str, region: str):
        self.subscription_key = subscription_key
        self.base_url = f"https://autograde-openai-connection.cognitiveservices.azure.com/speechtotext/v3.2"
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json"
        }

    # === Batch Mode ===
    def create_batch_transcription(self, name, description, locale, sas_uri, diarization=False, min_speakers=1,
                                   max_speakers=5):
        # TODO: https://github.com/Azure-Samples/cognitive-services-speech-sdk/issues/1109
        body = {
            "displayName": name,
            "description": description,
            "locale": locale,
            "contentUrls": [sas_uri],
            "properties": {
                "wordLevelTimestampsEnabled": True,
                "punctuationMode": "DictatedAndAutomatic",
                "profanityFilterMode": "Masked"
            }
        }

        if diarization:
            body["properties"]["diarizationEnabled"] = True
            body["properties"]["diarization"] = {
                "speakers": {
                    "minCount": min_speakers,
                    "maxCount": max_speakers
                }
            }

        response = requests.post(f"{self.base_url}/transcriptions", headers=self.headers, json=body)
        if not response.ok:
            print("Request failed:")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
        response.raise_for_status()
        return response.headers["Location"]

    def wait_for_completion(self, transcription_url: str, poll_interval=5):
        while True:
            response = requests.get(transcription_url, headers=self.headers)
            response.raise_for_status()
            status = response.json()["status"]
            logging.info(f"Transcription status: {status}")
            if status in ("Succeeded", "Failed"):
                return response.json()
            time.sleep(poll_interval)

    def get_transcription_results(self, transcription_url: str):
        transcription_id = transcription_url.split("/")[-1]
        files_url = f"{self.base_url}/transcriptions/{transcription_id}/files"
        response = requests.get(files_url, headers=self.headers)
        response.raise_for_status()

        results = []
        for file in response.json()["values"]:
            if file["kind"] == "Transcription":
                result_data = requests.get(file["links"]["contentUrl"])
                result_data.raise_for_status()
                result = TranscriptionResult.model_validate(result_data.json())
                results.append(result)
        return results

    def delete_transcription(self, transcription_url: str):
        response = requests.delete(transcription_url, headers=self.headers)
        if response.status_code == 204:
            logging.info("Transcription deleted successfully.")
        else:
            logging.warning(f"Failed to delete transcription: {response.status_code}")
        return response.status_code == 204

    def list_transcriptions(self, status_filter: str = None):
        params = {}
        if status_filter:
            params["filter"] = f"status eq '{status_filter}'"
        url = f"{self.base_url}/transcriptions"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()["values"]

    def transcribe_file_direct(self, file_path: str, locale="en-US"):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'rb') as audio_file:
            files = {
                "audio": (os.path.basename(file_path), audio_file, "audio/wav"),
                "definition": (None, json.dumps({
                    "displayName": "DirectUploadTranscription",
                    "description": "Transcription from uploaded file",
                    "locale": locale,
                    "properties": {
                        "wordLevelTimestampsEnabled": True,
                        "punctuationMode": "DictatedAndAutomatic"
                    }
                }), "application/json")
            }

            endpoint = f"{self.base_url}/transcriptions:transcribe"
            response = requests.post(endpoint, headers={"Ocp-Apim-Subscription-Key": self.subscription_key},
                                     files=files)
            response.raise_for_status()
            return response.json()

from pydub import AudioSegment
import os

def convert_to_mono(input_path: str, output_path: str, sample_rate: int = 16000):
    """
    Converts a stereo or multi-channel WAV audio file to mono and resamples to 16kHz.

    Args:
        input_path (str): Path to the input .wav or other audio file.
        output_path (str): Path where the mono .wav will be saved.
        sample_rate (int): Desired output sample rate (default 16000).
    """
    # Load the file
    audio = AudioSegment.from_file(input_path)

    # Convert to mono
    audio = audio.set_channels(1)

    # Resample
    audio = audio.set_frame_rate(sample_rate)

    # Export as PCM signed 16-bit little-endian WAV
    audio.export(output_path, format="wav", codec="pcm_s16le")

    print(f"Converted '{input_path}' → '{output_path}' [Mono, {sample_rate}Hz]")


if __name__ == '__main__':
    # Replace these placeholders with valid values for your Azure Speech API
    endpoint = ""
    subscription_key = ""
    region = ""

    client = AzureSpeechClient(endpoint, subscription_key, region)

    # Example transcription job parameters
    transcription_name = "Test Transcription"
    transcription_description = "Testing the Azure Speech API"
    transcription_locale = "en-US"

    r = client.get_transcription_results("https://autograde-openai-connection.cognitiveservices.azure.com/speechtotext/v3.2/transcriptions/551f5ad4-cfb1-4f76-b8e3-c7c5f081bc9a")
    print(r)

    try:
        # Create a transcription
        transcription_url = client.create_batch_transcription(
            name=transcription_name,
            description=transcription_description,
            locale=transcription_locale,
            sas_uri="https://nc.aseef.dev/s/8jET7qmsyZ88XT3/download/AA.mp3"
        )
        print(f"Transcription created at: {transcription_url}")

        # Wait for transcription to complete
        transcription_result = client.wait_for_completion(transcription_url)
        print("Transcription completed.")
        print(transcription_result)

        # Fetch transcription results
        results = client.get_transcription_results(transcription_url)
        print("Transcription results:")
        for result in results:
            print(result)

        # List transcriptions
        transcriptions = client.list_transcriptions()
        print("List of transcriptions with status 'Succeeded':")
        for transcription in transcriptions:
            print(transcription)

        # Delete transcription
        #if client.delete_transcription(transcription_url):
        #    print("Transcription deleted successfully.")
        #else:
        #    print("Failed to delete transcription.")

    except Exception as e:
        print(f"Error: {e}")

