import pygame
import sys
import random
import threading
import json
import os
import math

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
BLACK, WHITE = (5, 5, 15), (255, 255, 255)
NEON_GREEN, RED = (57, 255, 20), (255, 50, 50)
ORANGE, YELLOW, BLUE = (255, 165, 0), (255, 255, 0), (0, 191, 255)
SCORE_FILE = "high_scores_v5.json"

class GameState:
    def __init__(self, user_name):
        self.user_name = user_name
        self.score = 0
        self.level = 1
        self.data = self.load_data()

    def load_data(self):
        if os.path.exists(SCORE_FILE):
            try:
                with open(SCORE_FILE, 'r') as f: return json.load(f)
            except: return {}
        return {}

    def save_score_threaded(self):
        def _save():
            if self.user_name not in self.data: self.data[self.user_name] = []
            self.data[self.user_name].append(self.score)
            self.data[self.user_name] = self.data[self.user_name][-15:]
            with open(SCORE_FILE, 'w') as f: json.dump(self.data, f)
        threading.Thread(target=_save, daemon=True).start()


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, NEON_GREEN, [(25, 0), (50, 40), (0, 40)])
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-50))
        self.speed = 8

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0: self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < SCREEN_WIDTH: self.rect.x += self.speed
        if keys[pygame.K_UP] and self.rect.top > 0: self.rect.y -= self.speed
        if keys[pygame.K_DOWN] and self.rect.bottom < SCREEN_HEIGHT: self.rect.y += self.speed

class Alien(pygame.sprite.Sprite):
    def __init__(self, level, player, score):
        super().__init__()
        self.player = player
        self.score = score
        self.image = pygame.Surface((35, 30))
        
        if score >= 70:
            self.type = "FLANKER" 
            self.image.fill(BLUE)
        elif score >= 40:
            self.type = "KAMIKAZE" 
            self.image.fill(ORANGE)
        else:
            self.type = "NORMAL"
            self.image.fill(RED)

        self.rect = self.image.get_rect(x=random.randint(0, SCREEN_WIDTH-40), y=random.randint(-150, -50))
        self.speed_y = 2 + (level * 0.3)
        self.vx = random.choice([-3, 3])

    def update(self):
        if self.type == "FLANKER":
            target_x = self.player.rect.x + (self.vx * 10)
            if self.rect.x < target_x: self.rect.x += 4
            else: self.rect.x -= 4
            self.rect.y += self.speed_y + 1
        elif self.type == "KAMIKAZE":
            dx, dy = self.player.rect.x - self.rect.x, self.player.rect.y - self.rect.y
            dist = math.hypot(dx, dy)
            if dist != 0:
                self.rect.x += (dx / dist) * 4
                self.rect.y += (dy / dist) * 4
        else:
            self.rect.y += self.speed_y
            self.rect.x += self.vx
            if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH: self.vx *= -1
        
        if self.rect.top > SCREEN_HEIGHT: self.kill()

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx=0, dy=-12, color=YELLOW):
        super().__init__()
        self.image = pygame.Surface((6, 12))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.dx, self.dy = dx, dy

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        if not (0 <= self.rect.x <= SCREEN_WIDTH and 0 <= self.rect.y <= SCREEN_HEIGHT):
            self.kill()


class AlienInvasion:
    def __init__(self, name):
        pygame.init()
        pygame.mixer.init() 
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier", 20, bold=True)
        self.state = GameState(name)
        self.menu_active = True

        
        try:
            self.shoot_sound = pygame.mixer.Sound("fire.wav")
            self.destroy_sound = pygame.mixer.Sound("explode.wav")
        except FileNotFoundError:
            print("Sound files missing. Place 'fire.wav' and 'explode.wav' in the same folder.")
            self.shoot_sound = None
            self.destroy_sound = None

    def draw_text(self, text, y, color=WHITE):
        img = self.font.render(text, True, color)
        self.screen.blit(img, (SCREEN_WIDTH//2 - img.get_width()//2, y))

    def main_menu(self):
        while self.menu_active:
            self.screen.fill(BLACK)
            self.draw_text("=== ALIEN INVASION: ELITE ===", 100, NEON_GREEN)
            self.draw_text("[1] START GAME", 200)
            self.draw_text("[2] VIEW HIGH SCORES", 250)
            self.draw_text("[3] CONTROL MANUAL", 300)
            self.draw_text("[4] EXIT GAME", 350, RED)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.quit_game()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: self.menu_active = False; self.run_game()
                    if event.key == pygame.K_2: self.show_stats()
                    if event.key == pygame.K_3: self.show_manual()
                    if event.key == pygame.K_4: self.quit_game()

    def show_manual(self):
        waiting = True
        while waiting:
            self.screen.fill(BLACK)
            self.draw_text("CONTROL MANUAL", 50, YELLOW)
            self.draw_text("ARROWS : Move (8-Way)", 150)
            self.draw_text("SPACE  : Triple Forward Shot", 200)
            self.draw_text("X KEY  : OMNI-FIRE (4 Sides)", 250, BLUE)
            self.draw_text("L-SHIFT: Homing Target Lock", 300)
            self.draw_text("ESC    : Back to Menu", 450, RED)
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: waiting = False

    def quit_game(self):
        pygame.quit(); sys.exit()

    def show_stats(self):
        if not HAS_MATPLOTLIB: return
        history = self.state.data.get(self.state.user_name, [])
        if history:
            plt.figure("Performance"); plt.plot(history, color='lime'); plt.show()

    def run_game(self):
        player = Player()
        aliens, bullets, all_sprites = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(player)
        self.state.score, self.state.level = 0, 1

        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.quit_game()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.shoot_sound: self.shoot_sound.play()
                        for dx in [-3, 0, 3]:
                            b = Bullet(player.rect.centerx, player.rect.top, dx, -12)
                            bullets.add(b); all_sprites.add(b)
                    if event.key == pygame.K_x:
                        if self.shoot_sound: self.shoot_sound.play()
                        b1 = Bullet(player.rect.centerx, player.rect.top, 0, -12, BLUE)
                        b2 = Bullet(player.rect.centerx, player.rect.bottom, 0, 12, BLUE)
                        b3 = Bullet(player.rect.left, player.rect.centery, -12, 0, BLUE)
                        b4 = Bullet(player.rect.right, player.rect.centery, 12, 0, BLUE)
                        bullets.add(b1, b2, b3, b4); all_sprites.add(b1, b2, b3, b4)

            if len(aliens) < (4 + self.state.level):
                a = Alien(self.state.level, player, self.state.score)
                aliens.add(a); all_sprites.add(a)

            all_sprites.update()

            if pygame.sprite.groupcollide(aliens, bullets, True, True):
                if self.destroy_sound: self.destroy_sound.play()
                self.state.score += 5
                if self.state.score % 100 == 0: self.state.level += 1

            if pygame.sprite.spritecollide(player, aliens, False):
                if self.destroy_sound: self.destroy_sound.play()
                self.state.save_score_threaded()
                self.menu_active = True; self.main_menu()

            self.screen.fill(BLACK)
            all_sprites.draw(self.screen)
            self.draw_text(f"SCORE: {self.state.score} | LVL: {self.state.level}", 10)
            pygame.display.flip()

if __name__ == "__main__":
    game = AlienInvasion("Elite_Pilot")
    game.main_menu()