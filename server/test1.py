import pygame
import sys
import cv2
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import threading
import qrcode
import os
import json
from datetime import datetime

message = ""
ip_info = ""
event_message = ""

class VideoControlHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global message, event_message
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        parsed_data = urllib.parse.parse_qs(post_data)

        if 'action' in parsed_data:
            action = parsed_data['action'][0]

            if action == 'play':
                server_state.set_paused(False)
                event_message = f"Remote event received 'play' from {self.client_address[0]}"
                log_event(action, self.client_address[0])
            elif action == 'pause':
                server_state.set_paused(True)
                event_message = f"Remote event received 'pause' from {self.client_address[0]}"
                log_event(action, self.client_address[0])

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(bytes("Action received: " + action, "utf-8"))
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(bytes("Missing 'action' parameter", "utf-8"))

def log_event(action, ip):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        log_entry = f"{action},{ip},{timestamp}\n"
        with open('events.log', 'a') as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"Error logging event: {e}")

class VideoServerState:
    def __init__(self):
        self.paused = False

    def set_paused(self, paused):
        self.paused = paused

def start_http_server(config, server_class=HTTPServer, handler_class=VideoControlHandler):
    server_address = (config['server_address'], config['port'])
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on {config["server_address"]}:{config["port"]}...')
    global ip_info
    ip_info = f"{config['server_address']}:{config['port']}/"
    httpd.serve_forever()

def create_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    img = img.resize((100, 100))

    img.save(filename)

def play_video(video_path, qr_code_image, server_state):
    pygame.init()
    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    progress_bar_width = screen_width // 5  # Largura da barra de progresso (20% da largura da tela)
    progress_bar_height = 10  # Altura da barra de progresso
    progress_bar_x = 100  # Posição horizontal à esquerda (100 pixels de margem)
    progress_bar_y = screen_height - progress_bar_height - 100  # Posição vertical no rodapé da tela (100 pixels de margem)
    fill_color = (255, 255, 255)  # Cor do preenchimento da barra de progresso (branco)
    border_color = (255, 255, 255)  # Cor da borda da barra de progresso (branca)
    font_color = (255, 255, 255)  # Cor da fonte do contador de tempo (branca)
    event_color = (255, 255, 255)  # Cor da fonte para mensagens de eventos (branca)
    pygame.font.init()
    font = pygame.font.Font(None, 30)  # Define a fonte com tamanho 30 pixels
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption('Video Player')
    clock = pygame.time.Clock()

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration_sec = total_frames / fps
        start_time = pygame.time.get_ticks()
        server_state.set_paused(False)
        pause_start_time = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if not server_state.paused:
                elapsed_time = (pygame.time.get_ticks() - start_time) / 1000.0
                progress = elapsed_time / duration_sec
                progress = min(progress, 1.0)  # Limitar o progresso a 1.0 para evitar valores maiores que 1
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (screen_width, screen_height))
                frame = pygame.image.frombuffer(frame.tobytes(), (screen_width, screen_height), 'RGB')
                screen.blit(frame, (0, 0))
                progress_bar_width_actual = progress_bar_width * progress
                progress_bar_rect = pygame.Rect(progress_bar_x, progress_bar_y, progress_bar_width_actual, progress_bar_height)
                pygame.draw.rect(screen, border_color, progress_bar_rect, 3)
                pygame.draw.rect(screen, fill_color, progress_bar_rect)
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                time_str = f"{minutes:02}:{seconds:02}"
                time_surface = font.render(f"Time: {time_str}", True, font_color)
                time_rect = time_surface.get_rect()
                time_rect.topleft = (progress_bar_x, progress_bar_y - 40)  # Posição do tempo decorrido acima da barra de progresso
                screen.blit(time_surface, time_rect)
                ip_surface = font.render(f"Local IP: {ip_info}", True, font_color)
                ip_rect = ip_surface.get_rect()
                ip_rect.topleft = (progress_bar_x, progress_bar_y + progress_bar_height + 10)  # Posição das informações de IP/porta abaixo da barra de progresso
                screen.blit(ip_surface, ip_rect)
                event_surface = font.render(event_message, True, event_color)
                event_rect = event_surface.get_rect()
                event_rect.topleft = (progress_bar_x, ip_rect.bottom + 10)  # Posição da mensagem de evento abaixo das informações de IP/porta
                screen.blit(event_surface, event_rect)
                qr_resized = pygame.transform.scale(qr_code_image, (100, 100))
                qr_position = (screen_width - 110, screen_height - 110)
                screen.blit(qr_resized, qr_position)
                pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_q:
                        pygame.quit()
                        os._exit(0)  # Encerra o processo imediatamente
                    elif event.key == pygame.K_p:
                        server_state.set_paused(not server_state.paused)
                        if server_state.paused:
                            pause_start_time = pygame.time.get_ticks()  # Marcar o tempo de pausa
                        else:
                            start_time += (pygame.time.get_ticks() - pause_start_time)  # Retomar contagem do tempo

            clock.tick(30)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        pygame.quit()
        if 'cap' in locals():
            cap.release()

def read_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Arquivo config.json não encontrado.")
        return None
    except KeyError as e:
        print(f"Chave ausente no arquivo config.json: {e}")
        return None

def start_server_and_play():
    global server_state, qr_code_image

    config = read_config()
    if config is None:
        return

    server_state = VideoServerState()  # Inicializa o estado do servidor
    server_address = (config['server_address'], config['port'])
    qr_code_data = config.get('qr_code_data')
    video_path = config.get('video_path')

    if not qr_code_data or not video_path:
        print("Configurações inválidas no arquivo config.json.")
        return

    create_qr_code(qr_code_data, 'qrcode.png')
    qr_code_image = pygame.image.load('qrcode.png')
    http_thread = threading.Thread(target=start_http_server, args=(config,))
    http_thread.start()
    play_video(video_path, qr_code_image, server_state)

if __name__ == '__main__':
    start_server_and_play()
