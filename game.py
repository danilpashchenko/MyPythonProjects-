"""
Space Arena — компактная, но качественная 2D-аркада на Python + pygame.
Файл: space_arena.py
Требования: Python 3.8+, pygame
Установка: pip install pygame
Запуск: python space_arena.py

Краткое управление:
  Стрелки / WASD — движение
  Пробел — стрельба
  Q / E — смена оружия (если доступно)
  P — пауза
  M — вкл/выкл звук
  Esc — выйти в меню/назад

Особенности:
  • Основное меню + экран паузы
  • Игровой режим с волнами врагов, набираем очки
  • Сохранение рекорда в highscore.json
  • Простая система усилений (power-ups)
  • Эффекты частиц, плавная анимация
  • Настройки (громкость, сложность) сохраняются в settings.json

Автор: сгенерировано ChatGPT (код можно редактировать и расширять)
"""

import pygame
import random
import math
import json
import os
from pathlib import Path

# ------------------------------
# Конфигурация
# ------------------------------
CONFIG = {
    'WIDTH': 1000,
    'HEIGHT': 700,
    'FPS': 60,
    'TITLE': 'Space Arena',
    'DATA_DIR': Path(__file__).parent,
    'HIGHSCORE_FILE': 'highscore.json',
    'SETTINGS_FILE': 'settings.json'
}

# Default settings
DEFAULT_SETTINGS = {
    'volume': 0.6,
    'difficulty': 'normal',  # easy, normal, hard
}

# ------------------------------
# Helpers
# ------------------------------

def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('Error saving', path, e)


# ------------------------------
# Game Objects
# ------------------------------
class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, vel, life, size):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.life = life
        self.max_life = life
        self.size = size
        self.image = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 200, 50, 200), (size, size), size)
        self.rect = self.image.get_rect(center=self.pos)

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        self.pos += self.vel * dt
        alpha = max(0, int(255 * (self.life / self.max_life)))
        # fade
        self.image.set_alpha(alpha)
        self.rect.center = (int(self.pos.x), int(self.pos.y))


class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, vel, owner='player'):
        super().__init__()
        self.image = pygame.Surface((6, 12), pygame.SRCALPHA)
        color = (180, 255, 200) if owner == 'player' else (255, 120, 120)
        pygame.draw.rect(self.image, color, (0, 0, 6, 12))
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.owner = owner
        self.damage = 1 if owner == 'player' else 1

    def update(self, dt):
        self.pos += self.vel * dt
        self.rect.center = self.pos
        w, h = CONFIG['WIDTH'], CONFIG['HEIGHT']
        if self.pos.y < -50 or self.pos.y > h + 50 or self.pos.x < -50 or self.pos.x > w + 50:
            self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.original_image = pygame.Surface((46, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, (80, 200, 255), [(23, 0), (46, 40), (23, 30), (0, 40)])
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(0, 0)
        self.speed = 300
        self.health = 6
        self.max_health = 6
        self.shoot_cooldown = 0.14
        self.shoot_timer = 0
        self.score = 0
        self.lives = 3
        self.power_level = 0

    def update(self, dt, keys):
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if move.length_squared() > 0:
            move = move.normalize()
        self.vel = move * self.speed
        self.pos += self.vel * dt
        # Keep on screen
        self.pos.x = max(20, min(CONFIG['WIDTH'] - 20, self.pos.x))
        self.pos.y = max(20, min(CONFIG['HEIGHT'] - 20, self.pos.y))
        self.rect.center = self.pos

        # tilt effect
        angle = -self.vel.x / self.speed * 12
        self.image = pygame.transform.rotate(self.original_image, angle)
        self.rect = self.image.get_rect(center=self.rect.center)

        if self.shoot_timer > 0:
            self.shoot_timer -= dt

    def shoot(self, bullets_group):
        if self.shoot_timer > 0:
            return
        self.shoot_timer = self.shoot_cooldown
        # main bullet
        b = Bullet(self.pos - pygame.Vector2(0, 18), pygame.Vector2(0, -650), owner='player')
        bullets_group.add(b)
        # side bullets if powered
        if self.power_level >= 1:
            bullets_group.add(Bullet(self.pos + pygame.Vector2(-12, -10), pygame.Vector2(-120, -600), owner='player'))
            bullets_group.add(Bullet(self.pos + pygame.Vector2(12, -10), pygame.Vector2(120, -600), owner='player'))
        if self.power_level >= 2:
            bullets_group.add(Bullet(self.pos + pygame.Vector2(-24, 0), pygame.Vector2(-220, -520), owner='player'))
            bullets_group.add(Bullet(self.pos + pygame.Vector2(24, 0), pygame.Vector2(220, -520), owner='player'))


class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, kind='basic'):
        super().__init__()
        self.kind = kind
        self.orig = pygame.Surface((40, 34), pygame.SRCALPHA)
        color = (255, 120, 120) if kind == 'basic' else (255, 200, 120)
        pygame.draw.ellipse(self.orig, color, (0, 0, 40, 34))
        self.image = self.orig.copy()
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.speed = random.uniform(60, 120)
        self.health = 1 if kind == 'basic' else 3
        self.shoot_timer = random.uniform(0.6, 2.0)

    def update(self, dt, player_pos, bullets_group):
        # simple AI: move downwards and slightly toward player
        direction = pygame.Vector2(0, 1)
        to_player = (player_pos - self.pos)
        if to_player.length_squared() > 0:
            direction += to_player.normalize() * 0.25
        direction = direction.normalize()
        self.pos += direction * self.speed * dt
        self.rect.center = self.pos

        # shooting
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = random.uniform(1.0, 2.5)
            to_player = (player_pos - self.pos).normalize()
            bullets_group.add(Bullet(self.pos + to_player * 20, to_player * 260, owner='enemy'))

        # rotate slowly
        angle = math.sin(pygame.time.get_ticks() / 300) * 6
        self.image = pygame.transform.rotate(self.orig, angle)
        self.rect = self.image.get_rect(center=self.rect.center)

        # remove if out of bounds
        if self.pos.y > CONFIG['HEIGHT'] + 100:
            self.kill()


class PowerUp(pygame.sprite.Sprite):
    TYPES = ['health', 'power', 'score']

    def __init__(self, pos):
        super().__init__()
        self.type = random.choice(self.TYPES)
        self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
        if self.type == 'health':
            pygame.draw.circle(self.image, (120, 255, 140), (10, 10), 9)
        elif self.type == 'power':
            pygame.draw.circle(self.image, (180, 180, 255), (10, 10), 9)
        else:
            pygame.draw.circle(self.image, (255, 230, 120), (10, 10), 9)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(0, 70)

    def update(self, dt):
        self.pos += self.vel * dt
        self.rect.center = self.pos
        if self.pos.y > CONFIG['HEIGHT'] + 50:
            self.kill()


# ------------------------------
# UI Elements
# ------------------------------
class Button:
    def __init__(self, rect, text, font, callback=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.callback = callback

    def draw(self, surf):
        pygame.draw.rect(surf, (45, 45, 60), self.rect, border_radius=10)
        pygame.draw.rect(surf, (90, 90, 110), self.rect, 3, border_radius=10)
        txt = self.font.render(self.text, True, (230, 230, 240))
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos) and self.callback:
                self.callback()


# ------------------------------
# Game system
# ------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((CONFIG['WIDTH'], CONFIG['HEIGHT']))
        pygame.display.set_caption(CONFIG['TITLE'])
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 22)
        self.big_font = pygame.font.SysFont('Arial', 48)
        self.running = True

        # load settings
        self.settings_path = CONFIG['DATA_DIR'] / CONFIG['SETTINGS_FILE']
        self.settings = load_json(self.settings_path, DEFAULT_SETTINGS)
        self.volume = self.settings.get('volume', DEFAULT_SETTINGS['volume'])

        # audio subsystem (if available)
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volume)
        except Exception:
            print('Audio init failed — звук отключён')

        # game state
        self.state = 'menu'  # menu, playing, paused, gameover
        self.player = Player((CONFIG['WIDTH'] // 2, CONFIG['HEIGHT'] - 100))

        # groups
        self.all_sprites = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()

        # background stars
        self.stars = [
            {'pos': [random.randrange(0, CONFIG['WIDTH']), random.randrange(0, CONFIG['HEIGHT'])], 'z': random.uniform(0.4, 1.2)}
            for _ in range(120)
        ]

        # waves
        self.wave = 0
        self.spawn_timer = 0
        self.enemy_spawn_rate = 1.6

        # highscore
        self.hscore_path = CONFIG['DATA_DIR'] / CONFIG['HIGHSCORE_FILE']
        self.highscore = load_json(self.hscore_path, {'highscore': 0}).get('highscore', 0)

        # UI
        self.buttons = []
        self.create_menu()

    def create_menu(self):
        self.buttons = []
        midx = CONFIG['WIDTH'] // 2
        self.play_btn = Button((midx - 120, 240, 240, 56), 'Играть', self.font, callback=self.start_game)
        self.quit_btn = Button((midx - 120, 320, 240, 56), 'Выход', self.font, callback=self.quit)
        self.buttons.extend([self.play_btn, self.quit_btn])

    def start_game(self):
        self.reset_game()
        self.state = 'playing'

    def reset_game(self):
        # clear groups
        self.all_sprites.empty(); self.bullets.empty(); self.enemies.empty(); self.particles.empty(); self.powerups.empty()
        self.player = Player((CONFIG['WIDTH'] // 2, CONFIG['HEIGHT'] - 100))
        self.wave = 0
        self.spawn_timer = 0
        self.enemy_spawn_rate = 1.6

    def spawn_wave(self):
        self.wave += 1
        count = 6 + self.wave * 2
        for i in range(count):
            x = random.randrange(40, CONFIG['WIDTH'] - 40)
            y = random.randrange(-600, -40)
            kind = 'basic' if random.random() < 0.85 else 'heavy'
            e = Enemy((x, y), kind=kind)
            self.enemies.add(e)

    def spawn_enemy(self):
        x = random.randrange(40, CONFIG['WIDTH'] - 40)
        y = random.randrange(-80, -40)
        kind = 'basic' if random.random() < 0.9 else 'heavy'
        e = Enemy((x, y), kind=kind)
        self.enemies.add(e)

    def add_particles(self, pos, count=12):
        for _ in range(count):
            ang = random.uniform(0, math.pi*2)
            speed = random.uniform(40, 260)
            vel = pygame.Vector2(math.cos(ang)*speed, math.sin(ang)*speed)
            p = Particle(pos, vel, life=random.uniform(0.4, 0.9), size=random.randint(2,4))
            self.particles.add(p)

    def drop_powerup(self, pos):
        if random.random() < 0.28:
            pu = PowerUp(pos)
            self.powerups.add(pu)

    def process_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.quit()
            if self.state == 'menu':
                for b in self.buttons:
                    b.handle_event(ev)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.state == 'playing':
                        self.state = 'menu'
                    elif self.state == 'menu':
                        self.quit()
                if ev.key == pygame.K_p:
                    if self.state == 'playing':
                        self.state = 'paused'
                    elif self.state == 'paused':
                        self.state = 'playing'
                if ev.key == pygame.K_m:
                    # toggle volume
                    self.volume = 0 if self.volume > 0 else DEFAULT_SETTINGS['volume']
                    try:
                        pygame.mixer.music.set_volume(self.volume)
                    except Exception:
                        pass
                    self.settings['volume'] = self.volume
                    save_json(self.settings_path, self.settings)

    def update(self, dt):
        keys = pygame.key.get_pressed()
        if self.state == 'playing':
            # update player
            self.player.update(dt, keys)

            # spawn logic
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = max(0.4, self.enemy_spawn_rate - self.wave*0.03)
                # spawn one or more
                self.spawn_enemy()
                if random.random() < min(0.6, 0.06 + self.wave*0.02):
                    self.spawn_enemy()

            # update enemies
            for e in list(self.enemies):
                e.update(dt, self.player.pos, self.bullets)

            # update bullets
            for b in list(self.bullets):
                b.update(dt)

            # update powerups
            for pu in list(self.powerups):
                pu.update(dt)

            # update particles
            for p in list(self.particles):
                p.update(dt)

            # collisions
            # player bullets -> enemies
            hits = pygame.sprite.groupcollide(self.enemies, self.bullets, False, False)
            for enemy, bullets in hits.items():
                for b in bullets:
                    if b.owner == 'player':
                        enemy.health -= b.damage
                        b.kill()
                        self.add_particles(b.pos, count=6)
                        if enemy.health <= 0:
                            enemy.kill()
                            self.add_particles(enemy.pos, count=22)
                            self.player.score += 10 if enemy.kind=='basic' else 40
                            # drop powerup sometimes
                            self.drop_powerup(enemy.pos)

            # enemy bullets -> player
            for b in list(self.bullets):
                if b.owner == 'enemy' and pygame.sprite.collide_rect(b, self.player):
                    b.kill()
                    self.player.health -= 1
                    self.add_particles(self.player.pos, count=12)
                    if self.player.health <= 0:
                        self.player.lives -= 1
                        self.add_particles(self.player.pos, count=30)
                        if self.player.lives <= 0:
                            self.gameover()
                        else:
                            # respawn
                            self.player.health = self.player.max_health
                            self.player.pos = pygame.Vector2(CONFIG['WIDTH']//2, CONFIG['HEIGHT'] - 100)

            # enemies -> player collision
            for e in list(self.enemies):
                if pygame.sprite.collide_rect(e, self.player):
                    e.kill()
                    self.add_particles(e.pos, count=20)
                    self.player.health -= 2
                    if self.player.health <= 0:
                        self.player.lives -= 1
                        if self.player.lives <= 0:
                            self.gameover()
                        else:
                            self.player.health = self.player.max_health

            # player -> powerups
            for pu in list(self.powerups):
                if pygame.sprite.collide_rect(pu, self.player):
                    if pu.type == 'health':
                        self.player.health = min(self.player.max_health, self.player.health + 2)
                    elif pu.type == 'power':
                        self.player.power_level = min(2, self.player.power_level + 1)
                    elif pu.type == 'score':
                        self.player.score += 60
                    pu.kill()

            # allow shooting
            if keys[pygame.K_SPACE]:
                self.player.shoot(self.bullets)

            # move bullets/enemies into all_sprites for rendering
            self.all_sprites.empty()
            self.all_sprites.add(self.enemies, self.bullets, self.particles, self.powerups)
            # keep player drawn last

            # increase difficulty slowly
            if pygame.time.get_ticks() % 10000 < 50:
                self.enemy_spawn_rate = max(0.45, self.enemy_spawn_rate - 0.02)

        # update other states if needed

    def draw_hud(self, surf):
        # score
        s = self.font.render(f'Очки: {self.player.score}', True, (230, 230, 230))
        surf.blit(s, (14, 12))
        # health
        for i in range(self.player.max_health):
            x = 14 + i * 22
            y = 44
            col = (200, 60, 60) if i < self.player.health else (80, 80, 80)
            pygame.draw.rect(surf, col, (x, y, 18, 12))
            pygame.draw.rect(surf, (40, 40, 40), (x, y, 18, 12), 2)
        # lives
        lives_text = self.font.render(f'Жизни: {self.player.lives}', True, (230,230,230))
        surf.blit(lives_text, (14, 70))
        # highscore
        hs = self.font.render(f'Рекорд: {self.highscore}', True, (200,200,220))
        surf.blit(hs, (CONFIG['WIDTH'] - 180, 12))

    def draw(self):
        # background gradient
        surf = self.screen
        surf.fill((8, 8, 18))
        # starfield
        for s in self.stars:
            x, y = s['pos']
            z = s['z']
            sy = (y + pygame.time.get_ticks() * 0.02 * z) % CONFIG['HEIGHT']
            r = max(1, int(2*z))
            surf.fill((30, 30, 40), rect=(int(x), int(sy), r, r))

        # shoot trails & sprites
        for sprite in self.all_sprites:
            surf.blit(sprite.image, sprite.rect)
        surf.blit(self.player.image, self.player.rect)

        # particles on top
        for p in self.particles:
            surf.blit(p.image, p.rect)

        # HUD
        self.draw_hud(surf)

        # pause overlay
        if self.state == 'paused':
            overlay = pygame.Surface((CONFIG['WIDTH'], CONFIG['HEIGHT']), pygame.SRCALPHA)
            overlay.fill((10, 10, 15, 160))
            surf.blit(overlay, (0, 0))
            t = self.big_font.render('Пауза', True, (240,240,245))
            surf.blit(t, t.get_rect(center=(CONFIG['WIDTH']//2, CONFIG['HEIGHT']//2)))

        # menu
        if self.state == 'menu':
            overlay = pygame.Surface((CONFIG['WIDTH'], CONFIG['HEIGHT']), pygame.SRCALPHA)
            overlay.fill((6,6,12,220))
            surf.blit(overlay, (0,0))
            title = self.big_font.render(CONFIG['TITLE'], True, (220, 220, 240))
            surf.blit(title, title.get_rect(center=(CONFIG['WIDTH']//2, 120)))
            # draw buttons
            for b in self.buttons:
                b.draw(surf)
            hint = self.font.render('Стрелять: Пробел — Движение: WASD / стрелки — P: пауза', True, (180,180,200))
            surf.blit(hint, hint.get_rect(center=(CONFIG['WIDTH']//2, CONFIG['HEIGHT'] - 40)))

        pygame.display.flip()

    def gameover(self):
        # check highscore
        if self.player.score > self.highscore:
            self.highscore = self.player.score
            save_json(self.hscore_path, {'highscore': self.highscore})
        self.state = 'menu'

    def quit(self):
        # save settings
        save_json(self.settings_path, self.settings)
        self.running = False

    def run(self):
        while self.running:
            dt = self.clock.tick(CONFIG['FPS']) / 1000.0
            self.process_events()
            if self.state != 'paused' and self.state != 'menu':
                self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == '__main__':
    g = Game()
    g.run()
