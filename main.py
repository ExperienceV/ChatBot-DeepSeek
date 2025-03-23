from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pathlib import Path
import markdown

# Configurar la API key y base_url de DeepSeek
client = OpenAI(api_key="sk-c6e55ff3e4ca4ac5a040ff4f34d4f459", base_url="https://api.deepseek.com")

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

@app.get('/', response_class=HTMLResponse)
async def chat_page():
    path = Path('static/index.html')
    return path.read_text(encoding='utf-8')

class ChatBot:
    def __init__(self, system_message="Eres un asistente útil."):
        self.historial = []
        if system_message:
            self.historial.append({"role": "system", "content": system_message})
    
    async def enviar_mensaje(self, mensaje_usuario, stream=True):
        self.historial.append({"role": "user", "content": mensaje_usuario})
        
        try:
            respuesta = client.chat.completions.create(
                model="deepseek-chat",
                messages=self.historial,
                stream=stream
            )
            
            if stream:
                respuesta_completa = ""
                for chunk in respuesta:
                    if chunk.choices[0].delta.content:
                        contenido = chunk.choices[0].delta.content
                        respuesta_completa += contenido
                        # Renderizar el contenido en Markdown y enviarlo al cliente
                        contenido_html = markdown.markdown(contenido)
                        yield contenido_html
                self.historial.append({"role": "assistant", "content": respuesta_completa})
            else:
                respuesta_asistente = respuesta.choices[0].message.content
                self.historial.append({"role": "assistant", "content": respuesta_asistente})
                yield markdown.markdown(respuesta_asistente)
        
        except Exception as e:
            yield markdown.markdown(f"Error: {str(e)}")

chatbot = ChatBot(system_message="Eres un asistente útil que habla español.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            mensaje_usuario = await websocket.receive_text()
            async for chunk in chatbot.enviar_mensaje(mensaje_usuario, stream=True):
                await websocket.send_text(chunk)
    except WebSocketDisconnect:
        print("Cliente desconectado")
    except Exception as e:
        print(f"Error en la conexión WebSocket: {str(e)}")
