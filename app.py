import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_sock import Sock
import json

app = Flask(__name__)
sock = Sock(app)

# Estrutura para armazenar as salas e os jogadores
salas = {}

@app.route('/')
def home():
    return "Servidor do Jogo de Senhas está rodando!"

@sock.route('/ws')
def websocket_conexao(ws):
    """ Gerencia a conexão WebSocket dos jogadores """
    print("✅ Cliente conectado ao WebSocket!")

    jogador = None
    sala = None

    while True:
        try:
            mensagem = ws.receive()
            print(f"📩 Mensagem recebida: {mensagem}")
            
            if not mensagem:
                break

            data = json.loads(mensagem)

            if data["tipo"] == "entrar_sala":
                sala = data["sala"]
                jogador = data["jogador"]
                senha = data["senha"]

                if sala not in salas:
                    salas[sala] = {"jogadores": {}, "senhas": {}, "tentativas": []}

                salas[sala]["jogadores"][jogador] = ws
                salas[sala]["senhas"][jogador] = senha  # Armazena a senha do jogador

                print(f"🎮 {jogador} entrou na sala {sala} com senha {senha}")

                # Informar os outros jogadores que um novo jogador entrou
                for nome, conn in salas[sala]["jogadores"].items():
                    if nome != jogador:
                        conn.send(json.dumps({"tipo": "info", "mensagem": f"{jogador} entrou na sala"}))

                ws.send(json.dumps({"tipo": "info", "mensagem": f"Você entrou na sala {sala}!"}))

            elif data["tipo"] == "tentativa":
                tentativa = data["tentativa"]
                if sala in salas:
                    senha_adversario = next((s for j, s in salas[sala]["senhas"].items() if j != jogador), None)
                    
                    if senha_adversario:
                        certos, posicoes = verificar_tentativa(tentativa, senha_adversario)
                        resultado = f"{certos} números certos, {posicoes} na posição correta."

                        # Enviar feedback para os jogadores
                        for nome, conn in salas[sala]["jogadores"].items():
                            conn.send(json.dumps({
                                "tipo": "resultado",
                                "jogador": jogador,
                                "tentativa": tentativa,
                                "resultado": resultado
                            }))

            else:
                ws.send(json.dumps({"tipo": "erro", "mensagem": "Comando inválido"}))

        except Exception as e:
            print(f"❌ Erro na conexão WebSocket: {e}")
            break

    # Remover jogador ao sair
    if sala and jogador:
        salas[sala]["jogadores"].pop(jogador, None)
        salas[sala]["senhas"].pop(jogador, None)
        print(f"🚪 {jogador} saiu da sala {sala}")

        # Avisar o outro jogador
        for nome, conn in salas[sala]["jogadores"].items():
            conn.send(json.dumps({"tipo": "info", "mensagem": f"{jogador} saiu da sala"}))

def verificar_tentativa(tentativa, senha):
    """ 
    Verifica quantos números estão corretos e quantos estão na posição correta.
    Agora corrigindo o bug de contagem duplicada dos números!
    """
    tentativa = list(tentativa)  # Converte para lista para facilitar manipulação
    senha = list(senha)

    certos = 0
    posicoes = 0

    # Criar um dicionário para contar quantas vezes cada número aparece na senha correta
    contagem_senha = {}
    for num in senha:
        contagem_senha[num] = contagem_senha.get(num, 0) + 1

    # Primeiro, contar os números na posição certa
    for i in range(len(senha)):
        if tentativa[i] == senha[i]:
            posicoes += 1
            contagem_senha[senha[i]] -= 1  # Reduz a contagem desse número na senha

    # Depois, contar os números certos, mas na posição errada
    for i in range(len(senha)):
        if tentativa[i] in contagem_senha and contagem_senha[tentativa[i]] > 0 and tentativa[i] != senha[i]:
            certos += 1
            contagem_senha[tentativa[i]] -= 1  # Reduz a contagem desse número para evitar contagem duplicada

    return certos, posicoes

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True) 
