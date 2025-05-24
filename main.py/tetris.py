import pygame
import random
import sqlite3
import datetime
import cv2
import numpy as np
import math
from collections import deque

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 600, 730
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris")

font = pygame.font.Font(None, 48)
COLS, ROWS = 10, 18
CELL_SIZE = 40

try:
    sound_move = pygame.mixer.Sound("sounds/move.wav")
    sound_rotate = pygame.mixer.Sound("sounds/rotate.wav")
    sound_place = pygame.mixer.Sound("sounds/place.wav")
    sound_line_clear = pygame.mixer.Sound("sounds/line_clear.wav")
    sound_tetris = pygame.mixer.Sound("sounds/tetris.wav")
    sound_game_over = pygame.mixer.Sound("sounds/game_over.wav")
    pygame.mixer.music.load("sounds/background_music.wav")
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)
except pygame.error as e:
    print(f"Eroare la încărcarea sunetelor sau muzicii: {e}")
    sound_move = sound_rotate = sound_place = sound_line_clear = sound_tetris = sound_game_over = None

def create_db():
    with sqlite3.connect("tetris.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scoruri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nume TEXT,
                scor INTEGER,
                dificultate TEXT,
                timp INTEGER,
                data TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistici (
                nume TEXT PRIMARY KEY,
                jocuri INTEGER,
                timp_total INTEGER
            )
        ''')
        conn.commit()

def save_player_name(name):
    with open("player_name.txt", "w") as file:
        file.write(name)

def load_player_name():
    try:
        with open("player_name.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return ""

def select_theme():
    global background_color, PIECE_COLORS, background
    selecting = True
    themes = [
        {"image": "bianca.jpg", "bg_color": (255, 105, 180),
         "colors": [(255, 20, 147), (255, 105, 180), (255, 182, 193), (128, 0, 128), (0, 0, 255), (255, 240, 245)]},
        {"image": "fundalucv3.jpg", "bg_color": (255, 182, 193),
         "colors": [(255, 182, 193), (255, 165, 0), (0, 0, 255), (255, 0, 0), (0, 255, 0)]},
        {"image": "space.jpg", "bg_color": (0, 0, 50),
         "colors": [(135, 206, 250), (65, 105, 225), (30, 144, 255), (72, 61, 139), (0, 191, 255)]},
        {"image": "jungle.jpg", "bg_color": (34, 139, 34),
         "colors": [(0, 100, 0), (34, 139, 34), (60, 179, 113), (46, 139, 87), (107, 142, 35)]}
    ]
    preview_image = None
    preview_index = None
    preview_size = (200, 300)
    menu_font = pygame.font.Font(None, 36)
    while selecting:
        screen.fill((0, 0, 0))
        title_text = font.render("Alege tema:", True, (255, 255, 255))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 100))
        for i, theme in enumerate(themes):
            text = menu_font.render(f"{i+1} - Tema {i+1}", True, theme["bg_color"] if i != preview_index else (255, 255, 0))
            screen.blit(text, (150, 200 + i * 60))
        if preview_image:
            preview_rect = pygame.Rect(350, 150, preview_size[0], preview_size[1])
            pygame.draw.rect(screen, (255, 255, 255), preview_rect, 3)
            screen.blit(preview_image, (350, 150))
        prompt_line1 = menu_font.render("1-4 pentru previzualizare;", True, (255, 255, 255))
        prompt_line2 = menu_font.render("Enter pentru selectare", True, (255, 255, 255))
        screen.blit(prompt_line1, (WIDTH // 2 - prompt_line1.get_width() // 2, HEIGHT - 80))
        screen.blit(prompt_line2, (WIDTH // 2 - prompt_line2.get_width() // 2, HEIGHT - 40))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                    index = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4].index(event.key)
                    try:
                        preview_image = pygame.image.load(themes[index]["image"])
                        preview_image = pygame.transform.scale(preview_image, preview_size)
                        preview_index = index
                    except pygame.error as e:
                        print(f"Eroare la încărcarea imaginii de previzualizare: {e}")
                        preview_image = None
                        preview_index = None
                if event.key == pygame.K_RETURN and preview_index is not None:
                    background_color = themes[preview_index]["bg_color"]
                    PIECE_COLORS = themes[preview_index]["colors"]
                    background = pygame.image.load(themes[preview_index]["image"])
                    background = pygame.transform.scale(background, (400, HEIGHT))
                    selecting = False

def show_scores_and_stats():
    screen.fill((0, 0, 0))
    small_font = pygame.font.Font(None, 24)
    title_text = small_font.render("Scoruri și Statistici", True, (255, 255, 255))
    screen.blit(title_text, (150, 50))
    with sqlite3.connect("tetris.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT jocuri, timp_total FROM statistici WHERE nume = ?", (player_name,))
        stats = cursor.fetchone()
        if stats:
            screen.blit(small_font.render(f"Jocuri jucate: {stats[0]}", True, (255, 255, 255)), (50, 150))
            screen.blit(small_font.render(f"Timp total jucat: {stats[1]} secunde", True, (255, 255, 255)), (50, 180))
        else:
            screen.blit(small_font.render("Nu există statistici încă.", True, (255, 0, 0)), (50, 150))
        cursor.execute("SELECT scor, dificultate, timp, data FROM scoruri WHERE nume = ? ORDER BY data DESC LIMIT 10",
                       (player_name,))
        rows = cursor.fetchall()
        y_position = 210
        for scor, dif, timp, data in rows:
            text = f"Scor: {scor} | Dificultate: {dif} | Timp: {timp}s | Data: {data}"
            screen.blit(small_font.render(text, True, (255, 255, 255)), (50, y_position))
            y_position += 30
    back_text = small_font.render("Apasă ESC pentru a reveni la joc", True, (255, 255, 255))
    screen.blit(back_text, (150, HEIGHT - 100))
    pygame.display.update()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    waiting = False
                    return

def show_game_stats():
    screen.fill((0, 0, 0))
    small_font = pygame.font.Font(None, 36)
    title_text = small_font.render("Statistici Jucător", True, (255, 255, 255))
    screen.blit(title_text, (150, 100))
    with sqlite3.connect("tetris.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT jocuri, timp_total FROM statistici WHERE nume = ?", (player_name,))
        stats = cursor.fetchone()
        if stats:
            screen.blit(small_font.render(f"Jocuri jucate: {stats[0]}", True, (255, 255, 255)), (150, 200))
            screen.blit(small_font.render(f"Timp total jucat: {stats[1]} secunde", True, (255, 255, 255)), (150, 250))
        else:
            screen.blit(small_font.render("Nu există statistici.", True, (255, 0, 0)), (150, 200))
    pygame.display.update()
    pygame.time.wait(3000)

def load_high_score():
    try:
        with open("highscore.txt", "r") as file:
            return int(file.read().strip())
    except:
        return 0

def save_high_score(score):
    with open("highscore.txt", "w") as file:
        file.write(str(score))

def show_game_over_menu():
    if sound_game_over:
        sound_game_over.play()
    pygame.mixer.music.stop()
    waiting = True
    while waiting:
        screen.fill((0, 0, 0))
        title_text = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(title_text, (WIDTH // 2 - 100, 200))
        menu_font = pygame.font.Font(None, 36)
        screen.blit(menu_font.render("1 - Continuă", True, (255, 255, 255)), (160, 300))
        screen.blit(menu_font.render("2 - Joc nou", True, (255, 255, 255)), (160, 350))
        screen.blit(menu_font.render("ESC - Ieșire", True, (255, 255, 255)), (160, 400))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return "continue"
                elif event.key == pygame.K_2:
                    return "new_game"
                elif event.key == pygame.K_ESCAPE:
                    return "exit"

def get_player_name():
    global player_name
    player_name = ""
    typing = True
    while typing:
        screen.fill((0, 0, 0))
        title = font.render("Introdu numele tău:", True, (255, 255, 255))
        name_surface = font.render(player_name, True, (0, 255, 0))
        screen.blit(title, (150, 200))
        screen.blit(name_surface, (150, 260))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if player_name.strip() != "":
                        save_player_name(player_name)
                        typing = False
                elif event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                else:
                    player_name += event.unicode

def select_difficulty():
    global fall_speed, difficulty
    selecting = True
    while selecting:
        screen.fill((0, 0, 0))
        title_text = font.render("Selectează dificultatea", True, (255, 255, 255))
        screen.blit(title_text, (150, 200))
        menu_font = pygame.font.Font(None, 36)
        screen.blit(menu_font.render("1 - Ușor", True, (0, 255, 0)), (230, 300))
        screen.blit(menu_font.render("2 - Mediu", True, (255, 255, 0)), (230, 350))
        screen.blit(menu_font.render("3 - Greu", True, (255, 0, 0)), (230, 400))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    fall_speed = 3
                    difficulty = "Ușor"
                    selecting = False
                if event.key == pygame.K_2:
                    fall_speed = 5
                    difficulty = "Mediu"
                    selecting = False
                if event.key == pygame.K_3:
                    fall_speed = 8
                    difficulty = "Greu"
                    selecting = False

def start_game():
    global player_name, difficulty, score, high_score, fall_speed
    global piece, color, next_piece, next_color, piece_x, piece_y
    global grid, start_time, running, use_camera, cap, bg_gray
    create_db()
    score = 0
    high_score = load_high_score()
    grid = [[(0, 0, 0) for _ in range(COLS)] for _ in range(ROWS)]
    select_difficulty()
    piece = random.choice(SHAPES)
    color = random.choice(PIECE_COLORS)
    next_piece = random.choice(SHAPES)
    next_color = random.choice(PIECE_COLORS)
    piece_x, piece_y = 3, 0
    start_time = pygame.time.get_ticks()
    if cap is None:
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Camera nu a putut fi deschisă!")
                use_camera = False
            else:
                ret, bg_frame = cap.read()
                if not ret:
                    print("Nu s-a putut citi frame-ul de referință!")
                    use_camera = False
                else:
                    bg_gray = cv2.cvtColor(bg_frame, cv2.COLOR_BGR2GRAY)
                    bg_gray = cv2.GaussianBlur(bg_gray, (21, 21), 0)
                    use_camera = True
        except Exception as e:
            print(f"Eroare la inițializarea camerei: {e}")
            use_camera = False
    running = True
    pygame.mixer.music.play(-1)
    game_loop()
    pygame.mixer.music.stop()
    show_game_stats()
    choice = show_game_over_menu()
    if choice == "continue":
        pygame.mixer.music.play(-1)
        start_game()
    elif choice == "new_game":
        pygame.mixer.music.play(-1)
        get_player_name()
        select_theme()
        start_game()
    elif choice == "exit":
        if cap is not None:
            cap.release()
            cv2.destroyAllWindows()
        pygame.quit()
        exit()

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(5, 15)
        self.velocity = [random.uniform(-5, 5), random.uniform(-8, -1)]
        self.gravity = 0.2
        self.life = random.randint(40, 80)
        self.alpha = 255
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-5, 5)

    def update(self):
        self.velocity[1] += self.gravity
        self.x += self.velocity[0]
        self.y += self.velocity[1]
        self.size *= 0.97
        self.life -= 1
        self.alpha = max(0, min(255, int(self.life * 3)))
        self.rotation += self.rotation_speed

    def draw(self, surface):
        if self.life <= 0:
            return
        try:
            s = pygame.Surface((int(self.size), int(self.size)), pygame.SRCALPHA)
            shape_type = int(self.size) % 3
            alpha = min(255, self.alpha)
            color = list(self.color[:3]) + [alpha] if len(self.color) >= 3 else (255, 255, 255, alpha)
            if shape_type == 0:
                pygame.draw.circle(s, color, (int(self.size // 2), int(self.size // 2)), int(self.size // 2))
            elif shape_type == 1:
                pygame.draw.rect(s, color, (0, 0, int(self.size), int(self.size)))
            else:
                points = []
                center = (int(self.size // 2), int(self.size // 2))
                for i in range(5):
                    angle_outer = math.radians(self.rotation + i * 72)
                    x_outer = center[0] + (self.size // 2) * math.cos(angle_outer)
                    y_outer = center[1] + (self.size // 2) * math.sin(angle_outer)
                    points.append((x_outer, y_outer))
                    angle_inner = math.radians(self.rotation + i * 72 + 36)
                    x_inner = center[0] + (self.size // 4) * math.cos(angle_inner)
                    y_inner = center[1] + (self.size // 4) * math.sin(angle_inner)
                    points.append((x_inner, y_inner))
                if len(points) >= 3:
                    pygame.draw.polygon(s, color, points)
            rotated = pygame.transform.rotate(s, self.rotation)
            rect = rotated.get_rect(center=(int(self.x + self.size // 2), int(self.y + self.size // 2)))
            surface.blit(rotated, rect.topleft)
        except Exception as e:
            print(f"Eroare la desenarea particulei: {e}")

class BonusEffect:
    def __init__(self, lines, score_value):
        self.lines = lines
        self.score_value = score_value
        self.start_time = pygame.time.get_ticks()
        self.duration = 3000
        self.particles = []
        self.y_positions = [y * CELL_SIZE for y in range(max(0, ROWS - lines), ROWS)]
        if self.lines > 0:
            for y in self.y_positions:
                for _ in range(80):
                    try:
                        self.particles.append(
                            Particle(
                                random.randint(0, COLS * CELL_SIZE),
                                y + random.randint(-5, 5),
                                random.choice(PIECE_COLORS)
                            )
                        )
                    except Exception as e:
                        print(f"Eroare la crearea particulei: {e}")
        self.flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.flash_alpha = 200
        self.flash_decay = 8
        if lines == 4:
            self.flash_color = (255, 50, 50)
        elif lines == 3:
            self.flash_color = (255, 165, 0)
        elif lines == 2:
            self.flash_color = (255, 215, 0)
        else:
            self.flash_color = (255, 255, 255)
        self.text_scale = 0.1
        self.text_scaling_speed = 0.15
        self.text_max_scale = 2.0
        self.text_direction = 1
        self.font = pygame.font.Font(None, 100)
        try:
            if lines >= 4 and sound_tetris:
                sound_tetris.play()
            elif lines >= 2 and sound_line_clear:
                sound_line_clear.play()
        except Exception as e:
            print(f"Eroare la redarea sunetului: {e}")
        self.wave_radius = 0
        self.wave_width = 10
        self.wave_color = (255, 255, 255, 100)
        self.wave_speed = 10
        self.max_wave_radius = WIDTH

    def update(self):
        current_time = pygame.time.get_ticks()
        time_elapsed = current_time - self.start_time
        for particle in self.particles[:]:
            try:
                particle.update()
                if particle.life <= 0:
                    self.particles.remove(particle)
            except Exception as e:
                print(f"Eroare la actualizarea particulei: {e}")
                self.particles.remove(particle)
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - self.flash_decay)
        if self.text_direction == 1:
            self.text_scale += self.text_scaling_speed
            if self.text_scale >= self.text_max_scale:
                self.text_direction = -1
        else:
            self.text_scale -= self.text_scaling_speed
            if self.text_scale <= 0.8:
                self.text_direction = 1
        if self.wave_radius < self.max_wave_radius:
            self.wave_radius += self.wave_speed
        return (time_elapsed < self.duration)

    def draw(self, surface):
        try:
            for particle in self.particles:
                particle.draw(surface)
            if self.wave_radius < self.max_wave_radius:
                pygame.draw.circle(surface, self.wave_color, (WIDTH // 2, HEIGHT // 2),
                                   int(self.wave_radius), self.wave_width)
            if self.flash_alpha > 0:
                self.flash_surface.fill((0, 0, 0, 0))
                flash_rect = pygame.Rect(0, 0, COLS * CELL_SIZE, HEIGHT)
                flash_color_with_alpha = (*self.flash_color, max(0, min(255, int(self.flash_alpha))))
                pygame.draw.rect(self.flash_surface, flash_color_with_alpha, flash_rect)
                surface.blit(self.flash_surface, (0, 0))
            if self.lines >= 4:
                msg = "TETRIS BONUS!"
                text_color = (255, 50, 50)
                glow_color = (255, 100, 100, 100)
            elif self.lines == 3:
                msg = "TRIPLU!"
                text_color = (255, 165, 0)
                glow_color = (255, 200, 100, 100)
            elif self.lines == 2:
                msg = "DUBLU!"
                text_color = (255, 215, 0)
                glow_color = (255, 230, 100, 100)
            else:
                return
            orig_text = self.font.render(msg, True, text_color)
            glow_size = int(orig_text.get_width() * (self.text_scale + 0.2))
            glow_height = int(orig_text.get_height() * (self.text_scale + 0.2))
            glow_surf = pygame.Surface((glow_size, glow_height), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, glow_color, (0, 0, glow_size, glow_height))
            glow_rect = glow_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
            surface.blit(glow_surf, glow_rect)
            scaled_width = int(orig_text.get_width() * (self.text_scale))
            scaled_height = int(orig_text.get_height() * (self.text_scale))
            scaled_text = pygame.transform.scale(orig_text, (scaled_width, scaled_height))
            text_rect = scaled_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
            surface.blit(scaled_text, text_rect)
            bonus_font = pygame.font.Font(None, 70)
            bonus_txt = f"+{self.score_value} PUNCTE!"
            bonus_text = bonus_font.render(bonus_txt, True, (50, 255, 50))
            time_val = pygame.time.get_ticks() % 1000 / 1000.0
            pulse = 0.5 + 0.5 * math.sin(time_val * 2 * math.pi)
            bonus_glow = pygame.Surface((bonus_text.get_width() + 20, bonus_text.get_height() + 20), pygame.SRCALPHA)
            glow_size = int(10 + 5 * pulse)
            pygame.draw.rect(bonus_glow, (100, 255, 100, 50 + int(50 * pulse)),
                             bonus_glow.get_rect(), border_radius=glow_size)
            bonus_glow_rect = bonus_glow.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
            bonus_rect = bonus_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
            surface.blit(bonus_glow, bonus_glow_rect)
            surface.blit(bonus_text, bonus_rect)
        except Exception as e:
            print(f"Eroare la desenarea efectului de bonus: {e}")

SHAPES = [
    [(0, 0), (1, 0), (2, 0), (2, 1)],
    [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2)],
    [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)],
    [(0, 0), (1, 0), (0, 1), (1, 1)],
    [(0, 0), (1, 0), (2, 0), (1, 1)],
    [(1, 0), (2, 0), (0, 1), (1, 1)],
    [(0, 0), (1, 0), (1, 1), (2, 1)],
    [(0, 0), (0, 1), (1, 1), (2, 1)],
    [(0, 0), (1, 0), (2, 0), (3, 0)]
]

grid = [[(0, 0, 0) for _ in range(COLS)] for _ in range(ROWS)]
active_effects = []

def draw_grid():
    for i in range(COLS + 1):
        pygame.draw.line(screen, (50, 50, 50), (i * CELL_SIZE, 0), (i * CELL_SIZE, HEIGHT))
    for j in range(ROWS + 1):
        pygame.draw.line(screen, (50, 50, 50), (0, j * CELL_SIZE), (400, j * CELL_SIZE))

def draw_piece(piece, color, offset):
    for coord in piece:
        x, y = coord
        rect = pygame.Rect((x + offset[0]) * CELL_SIZE, (y + offset[1]) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 3)

def valid_move(piece, offset):
    for coord in piece:
        x, y = coord
        new_x, new_y = x + offset[0], y + offset[1]
        if new_x < 0 or new_x >= COLS or new_y >= ROWS or (new_y >= 0 and grid[new_y][new_x] != (0, 0, 0)):
            return False
    return True

def remove_full_lines():
    global grid, score, active_effects
    full_lines = []
    for i, row in enumerate(grid):
        if all(cell != (0, 0, 0) for cell in row):
            full_lines.append(i)
    if full_lines:
        lines_cleared = len(full_lines)
        new_grid = []
        for i, row in enumerate(grid):
            if i not in full_lines:
                new_grid.append(row)
        for _ in range(lines_cleared):
            new_grid.insert(0, [(0, 0, 0) for _ in range(COLS)])
        grid = new_grid
        base_points = 100
        if lines_cleared == 1:
            points = base_points
        elif lines_cleared == 2:
            points = base_points * 3
        elif lines_cleared == 3:
            points = base_points * 7
        else:
            points = base_points * 15
        score += points
        try:
            active_effects.append(BonusEffect(lines_cleared, points))
        except Exception as e:
            print(f"Eroare la crearea efectului de bonus: {e}")
        return lines_cleared
    return 0

def draw_effects(surface):
    for effect in active_effects[:]:
        try:
            if not effect.update():
                active_effects.remove(effect)
            else:
                effect.draw(surface)
        except Exception as e:
            print(f"Eroare la procesarea efectului: {e}")
            active_effects.remove(effect)

def rotate_piece(piece, clockwise=True):
    if clockwise:
        return [(y, -x) for x, y in piece]
    else:
        return [(-y, x) for x, y in piece]

def draw_score():
    pygame.draw.rect(screen, (0, 0, 0), (450, 50, 140, 100))
    screen.blit(font.render(f"Scor: {score}", True, (255, 255, 255)), (430, 60))
    screen.blit(font.render(f"High: {high_score}", True, (255, 255, 0)), (430, 100))
    diff_font = pygame.font.Font(None, 30)
    screen.blit(diff_font.render(f"Dificultate: {difficulty}", True, (255, 255, 255)), (430, 600))

def draw_time():
    elapsed_time = (pygame.time.get_ticks() - start_time) // 1000
    screen.blit(font.render(f"Timp: {elapsed_time}s", True, (255, 255, 255)), (430, 410))

def draw_next_piece():
    pygame.draw.rect(screen, (0, 0, 0), (420, 160, 170, 160))
    pygame.draw.rect(screen, (255, 255, 255), (420, 160, 170, 160), 2)
    for coord in next_piece:
        x, y = coord
        rect = pygame.Rect(460 + x * 30, 200 + y * 30, 30, 30)
        pygame.draw.rect(screen, next_color, rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)

def draw_white_border():
    pygame.draw.rect(screen, (255, 255, 255), (0, 0, 400, HEIGHT), 10)

def game_loop():
    global running, piece_x, piece_y, piece, color, next_piece, next_color, grid, score, high_score, active_effects
    clock = pygame.time.Clock()
    move_cooldown = 0
    move_cooldown_duration = 600
    angle_history = deque(maxlen=3)
    min_aspect_ratio = 1.2
    last_rotation = None
    object_detected = False
    while running:
        move_left = move_right = rotate_cw = rotate_ccw = False
        if use_camera:
            try:
                ret_cam, frame_cam = cap.read()
                if not ret_cam:
                    print("Nu s-a putut citi cadrul de la cameră!")
                else:
                    frame_cam = cv2.flip(frame_cam, 1)
                    hsv = cv2.cvtColor(frame_cam, cv2.COLOR_BGR2HSV)
                    lower_pink = np.array([130, 30, 30])
                    upper_pink = np.array([180, 255, 255])
                    mask = cv2.inRange(hsv, lower_pink, upper_pink)
                    mask = cv2.erode(mask, None, iterations=2)
                    mask = cv2.dilate(mask, None, iterations=2)
                    mask = cv2.GaussianBlur(mask, (5, 5), 0)
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    h, w = frame_cam.shape[:2]
                    current_time = pygame.time.get_ticks()
                    object_detected = False
                    if current_time - move_cooldown > move_cooldown_duration:
                        for cnt in contours:
                            if cv2.contourArea(cnt) < 2000:
                                continue
                            object_detected = True
                            M = cv2.moments(cnt)
                            if M["m00"] != 0:
                                cx = int(M["m10"] / M["m00"])
                                cy = int(M["m01"] / M["m00"])
                                if cx < w // 3:
                                    move_left = True
                                    move_cooldown = current_time
                                    if sound_move:
                                        sound_move.play()
                                elif cx > 2 * w // 3:
                                    move_right = True
                                    move_cooldown = current_time
                                    if sound_move:
                                        sound_move.play()
                                if len(cnt) >= 5:
                                    ellipse = cv2.fitEllipse(cnt)
                                    (center, axes, angle) = ellipse
                                    major_axis, minor_axis = max(axes), min(axes)
                                    aspect_ratio = major_axis / minor_axis if minor_axis > 0 else float('inf')
                                    if aspect_ratio >= min_aspect_ratio:
                                        angle_history.append(angle)
                                        if len(angle_history) == angle_history.maxlen:
                                            smoothed_angle = sum(angle_history) / len(angle_history)
                                            is_horizontal = (70 <= smoothed_angle <= 110) or (250 <= smoothed_angle <= 290)
                                            if is_horizontal:
                                                if 70 <= smoothed_angle <= 110:
                                                    if last_rotation != "cw":
                                                        rotate_cw = True
                                                        last_rotation = "cw"
                                                        move_cooldown = current_time
                                                        if sound_rotate:
                                                            sound_rotate.play()
                                                elif 250 <= smoothed_angle <= 290:
                                                    if last_rotation != "ccw":
                                                        rotate_ccw = True
                                                        last_rotation = "ccw"
                                                        move_cooldown = current_time
                                                        if sound_rotate:
                                                            sound_rotate.play()
                                            else:
                                                last_rotation = None
                                break
            except Exception as e:
                print(f"Eroare la procesarea imaginii camerei: {e}")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and valid_move(piece, (piece_x - 1, piece_y)):
                    piece_x -= 1
                    if sound_move:
                        sound_move.play()
                if event.key == pygame.K_RIGHT and valid_move(piece, (piece_x + 1, piece_y)):
                    piece_x += 1
                    if sound_move:
                        sound_move.play()
                if event.key == pygame.K_DOWN and valid_move(piece, (piece_x, piece_y + 1)):
                    piece_y += 1
                    if sound_move:
                        sound_move.play()
                if event.key == pygame.K_UP:
                    rotated = rotate_piece(piece, clockwise=True)
                    if valid_move(rotated, (piece_x, piece_y)):
                        piece = rotated
                        if sound_rotate:
                            sound_rotate.play()
                if event.key == pygame.K_s:
                    show_scores_and_stats()
        if move_left and valid_move(piece, (piece_x - 1, piece_y)):
            piece_x -= 1
            if sound_move:
                sound_move.play()
        if move_right and valid_move(piece, (piece_x + 1, piece_y)):
            piece_x += 1
            if sound_move:
                sound_move.play()
        if rotate_cw:
            rotated = rotate_piece(piece, clockwise=True)
            if valid_move(rotated, (piece_x, piece_y)):
                piece = rotated
                if sound_rotate:
                    sound_rotate.play()
        if rotate_ccw:
            rotated = rotate_piece(piece, clockwise=False)
            if valid_move(rotated, (piece_x, piece_y)):
                piece = rotated
                if sound_rotate:
                    sound_rotate.play()
        if not valid_move(piece, (piece_x, piece_y + 1)):
            for coord in piece:
                x, y = coord
                if y + piece_y >= 0:
                    grid[y + piece_y][x + piece_x] = color
            if sound_place:
                sound_place.play()
            remove_full_lines()
            piece, color = next_piece, next_color
            next_piece = random.choice(SHAPES)
            next_color = random.choice(PIECE_COLORS)
            piece_x, piece_y = 3, 0
        else:
            piece_y += 1
        if not valid_move(piece, (piece_x, piece_y)):
            if score > high_score:
                high_score = score
                save_high_score(high_score)
            elapsed = (pygame.time.get_ticks() - start_time) // 1000
            with sqlite3.connect("tetris.db") as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scoruri (nume, scor, dificultate, timp, data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (player_name, score, difficulty, elapsed, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                cursor.execute("SELECT jocuri, timp_total FROM statistici WHERE nume = ?", (player_name,))
                result = cursor.fetchone()
                if result:
                    jocuri, timp_total = result
                    cursor.execute('''
                        UPDATE statistici
                        SET jocuri = ?, timp_total = ?
                        WHERE nume = ?
                    ''', (jocuri + 1, timp_total + elapsed, player_name))
                else:
                    cursor.execute('''
                        INSERT INTO statistici (nume, jocuri, timp_total)
                        VALUES (?, ?, ?)
                    ''', (player_name, 1, elapsed))
                conn.commit()
            print("GAME OVER")
            running = False
            return
        screen.fill((0, 0, 0))
        screen.blit(background, (0, 0))
        draw_grid()
        draw_white_border()
        draw_piece(piece, color, (piece_x, piece_y))
        draw_score()
        draw_time()
        draw_next_piece()
        for row in range(ROWS):
            for col in range(COLS):
                if grid[row][col] != (0, 0, 0):
                    rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, grid[row][col], rect)
                    pygame.draw.rect(screen, (255, 255, 255), rect, 2)
        draw_effects(screen)
        if use_camera:
            if object_detected:
                pygame.draw.circle(screen, (0, 255, 0), (50, 50), 20)
                detect_text = font.render("Obiect detectat!", True, (0, 255, 0))
                screen.blit(detect_text, (100, 40))
            else:
                pygame.draw.circle(screen, (255, 0, 0), (50, 50), 20)
        pygame.display.update()
        clock.tick(fall_speed)

player_name = ""
background_color = None
PIECE_COLORS = []
background = None
difficulty = ""
fall_speed = 0
score = 0
high_score = 0
start_time = 0
running = False
use_camera = False
cap = None
bg_gray = None

create_db()
get_player_name()
select_theme()
start_game()

if cap is not None:
    cap.release()
    cv2.destroyAllWindows()

pygame.quit()
