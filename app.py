from flask import Flask, request
from groq import Groq
import requests
import os
import tempfile
from dotenv import load_dotenv
from pydub import AudioSegment

# =========================
# CARREGA .ENV
# =========================

load_dotenv()

app = Flask(__name__)

# =========================
# GROQ
# =========================

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# =========================
# Z-API
# =========================

INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
TOKEN = os.getenv("ZAPI_TOKEN")
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

# =========================
# MEMÓRIA DAS CONVERSAS
# =========================

memoria_conversas = {}

# =========================
# BAIXAR ÁUDIO
# =========================

def baixar_audio(url_audio):

    headers = {
        "Client-Token": CLIENT_TOKEN
    }

    resposta = requests.get(
        url_audio,
        headers=headers
    )

    temp_ogg = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".ogg"
    )

    temp_ogg.write(resposta.content)
    temp_ogg.close()

    return temp_ogg.name

# =========================
# CONVERTER OGG -> WAV
# =========================

def converter_para_wav(caminho_ogg):

    audio = AudioSegment.from_ogg(caminho_ogg)

    caminho_wav = caminho_ogg.replace(".ogg", ".wav")

    audio.export(
        caminho_wav,
        format="wav"
    )

    return caminho_wav

# =========================
# TRANSCRIÇÃO WHISPER
# =========================

def transcrever_audio(caminho_wav):

    with open(caminho_wav, "rb") as file:

        transcription = client.audio.transcriptions.create(
            file=file,
            model="whisper-large-v3"
        )

    return transcription.text

# =========================
# ENVIAR WHATSAPP
# =========================

def enviar_mensagem(telefone, mensagem):

    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text"

    headers = {
        "Client-Token": CLIENT_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "phone": telefone,
        "message": mensagem
    }

    print("\n====================")
    print("ENVIANDO WHATSAPP")
    print(payload)
    print("====================\n")

    resposta = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print("\n====================")
    print("RESPOSTA Z-API")
    print("STATUS:", resposta.status_code)
    print("TEXTO:", resposta.text)
    print("====================\n")

# =========================
# WEBHOOK
# =========================

@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.json

    print("\n====================")
    print("MENSAGEM RECEBIDA")
    print(data)
    print("====================\n")

    try:

        # =========================
        # IGNORA MENSAGENS DO BOT
        # =========================

        if data.get("fromMe"):
            return "ok", 200

        telefone = data["phone"]

        mensagem_usuario = ""

        # =========================
        # TEXTO
        # =========================

        if "text" in data:

            mensagem = data["text"]["message"]

            if mensagem.lower().startswith("!english"):

                mensagem_usuario = mensagem[8:].strip()

            else:
                return "ok", 200

        # =========================
        # ÁUDIO
        # =========================

        elif "audio" in data:

            print("\nÁUDIO RECEBIDO\n")

            url_audio = data["audio"]["audioUrl"]

            caminho_ogg = baixar_audio(url_audio)

            caminho_wav = converter_para_wav(caminho_ogg)

            texto_audio = transcrever_audio(caminho_wav)

            mensagem_usuario = texto_audio

            print("\n====================")
            print("TRANSCRIÇÃO")
            print(texto_audio)
            print("====================\n")

        else:
            return "ok", 200

        # =========================
        # IGNORA MENSAGEM VAZIA
        # =========================

        if not mensagem_usuario:
            return "ok", 200

        print("\nMensagem usuário:")
        print(mensagem_usuario)

        # =========================
        # CRIA MEMÓRIA
        # =========================

        if telefone not in memoria_conversas:

            memoria_conversas[telefone] = [
                {
                    "role": "system",
                    "content": """
                    You are an English tutor on WhatsApp.

                    Rules:
                    - Correct grammar naturally
                    - Be friendly and casual
                    - Keep responses short
                    - Always continue the conversation
                    - Sound like a real person
                    - Encourage the student
                    - Remember previous messages

                    If the sentence is wrong:
                    1. Show the correct version
                    2. Explain briefly
                    3. Continue the conversation naturally
                    """
                }
            ]

        # =========================
        # SALVA MENSAGEM USUÁRIO
        # =========================

        memoria_conversas[telefone].append({
            "role": "user",
            "content": mensagem_usuario
        })

        print("\n====================")
        print("MEMÓRIA")
        print(memoria_conversas[telefone])
        print("====================\n")

        # =========================
        # IA
        # =========================

        resposta_ia = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=memoria_conversas[telefone]
        )

        resposta = resposta_ia.choices[0].message.content

        print("\n====================")
        print("RESPOSTA IA")
        print(resposta)
        print("====================\n")

        # =========================
        # SALVA RESPOSTA
        # =========================

        memoria_conversas[telefone].append({
            "role": "assistant",
            "content": resposta
        })

        # =========================
        # ENVIA WHATSAPP
        # =========================

        enviar_mensagem(
            telefone,
            resposta
        )

        return "ok", 200

    except Exception as e:

        print("\n====================")
        print("ERRO")
        print(e)
        print("====================\n")

        return "erro", 500

# =========================
# START
# =========================

if __name__ == "__main__":
    app.run(port=5000)