from flask import Flask, request
from openai import OpenAI
import requests
import os
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================
load_dotenv()

app = Flask(__name__)

# =========================
# GROQ CONFIG
# =========================
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# =========================
# Z-API CONFIG
# =========================
INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
TOKEN = os.getenv("ZAPI_TOKEN")
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

# =========================
# MEMÓRIA DAS CONVERSAS
# =========================
memoria_conversas = {}

# =========================
# WEBHOOK
# =========================
@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.json

    print("\n====================")
    print("MENSAGEM RECEBIDA:")
    print(data)
    print("====================\n")

    try:

        # IGNORA MENSAGENS DO PRÓPRIO BOT
        if data['fromMe']:
            return "ok", 200

        # IGNORA GRUPOS
        if data['isGroup']:
            return "ok", 200

        mensagem = data['text']['message']
        telefone = data['phone']

        # RESPONDE SOMENTE !english
        if not mensagem.lower().startswith("!english"):
            return "ok", 200

        # REMOVE COMANDO
        mensagem_usuario = (
            mensagem
            .replace("!english", "")
            .replace("!English", "")
            .strip()
        )

        print("Mensagem usuário:", mensagem_usuario)

        # =========================
        # CRIA MEMÓRIA DO USUÁRIO
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

        # SALVA MENSAGEM DO USUÁRIO
        memoria_conversas[telefone].append(
            {
                "role": "user",
                "content": mensagem_usuario
            }
        )

        # LIMITAR HISTÓRICO
        memoria_conversas[telefone] = memoria_conversas[telefone][-10:]

        # =========================
        # IA
        # =========================
        resposta_ia = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=memoria_conversas[telefone]
        )

        resposta = resposta_ia.choices[0].message.content

        print("\n====================")
        print("RESPOSTA IA:")
        print(resposta)
        print("====================\n")

        # SALVA RESPOSTA DA IA
        memoria_conversas[telefone].append(
            {
                "role": "assistant",
                "content": resposta
            }
        )

        # =========================
        # ENVIO WHATSAPP
        # =========================
        url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text"

        payload = {
            "phone": telefone,
            "message": resposta
        }

        headers = {
            "Client-Token": CLIENT_TOKEN,
            "Content-Type": "application/json"
        }

        resposta_zapi = requests.post(
            url,
            json=payload,
            headers=headers
        )

        print("\n====================")
        print("RESPOSTA Z-API:")
        print("Status:", resposta_zapi.status_code)
        print("Texto:", resposta_zapi.text)
        print("====================\n")

        return "ok", 200

    except Exception as e:

        print("\n====================")
        print("ERRO:")
        print(e)
        print("====================\n")

        return "erro", 500

# =========================
# START APP
# =========================
if __name__ == "__main__":
    app.run(port=5000)