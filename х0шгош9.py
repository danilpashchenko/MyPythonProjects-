
# medieval_survival.py
# Исправленная, рабочая версия фиксированной карты 2D survival (пиксель-стиль).
# Требуется: Python 3.8+ и pygame
# Установка: pip install pygame
# Запуск: python medieval_survival.py

import pygame
import random
import math
import json
from pathlib import Path
import time
import sys

# ---------- Константы ----------
WIDTH, HEIGHT = 1200, 720
TILE = 32
MAP_W, MAP_H = 60, 40  # фиксированная карта
FPS = 60
SAVE_FILE = Path("savegame.json")
AUTOSAVE_INTERVAL = 30.0

# ---------- Утилиты ----------
def clamp(v, a, b):
    return max(a, min(b, v))

def save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print("Save error:", e)

def load_json(path: Path):
    try:
        txt = path.read_text(encoding="utf-8")
        return json.loads(txt)
    except Exception:
        return None

# ---------- Генерация простых пиксель-арт спрайтов (в памяти) ----------
def make_knight_sprite(scale=2):
    # 16x16 pixel base scaled by 'scale'
    base = pygame.Surface((16*scale, 16*scale), pygame.SRCALPHA)
    s = scale
    # helmet
    pygame.draw.rect(base, (90,90,140), (4*s,0*s,8*s,4*s))
    # face
    pygame.draw.rect(base, (220,200,170), (6*s,4*s,4*s,3*s))
    # body
    pygame.draw.rect(base, (80,100,150), (4*s,7*s,8*s,7*s))
    # shield left
    pygame.draw.rect(base, (160,130,70), (0*s,7*s,3*s,6*s))
    # sword right
    pygame.draw.rect(base, (200,200,220), (12*s,6*s,2*s,8*s))
    # boots
    pygame.draw.rect(base, (50,30,20), (5*s,14*s,3*s,2*s)); pygame.draw.rect(base, (50,30,20), (8*s,14*s,3*s,2*s))
    return base

def make_goblin_sprite(scale=2):
    base = pygame.Surface((16*scale, 16*scale), pygame.SRCALPHA)
    s=scale
    pygame.draw.rect(base, (110,160,80), (3*s,4*s,10*s,8*s))
    pygame.draw.rect(base, (20,20,20), (5*s,5*s,2*s,2*s))
    pygame.draw.rect(base, (20,20,20), (9*s,5*s,2*s,2*s))
    return base

def make_skeleton_sprite(scale=2):
    base = pygame.Surface((16*scale, 16*scale), pygame.SRCALPHA)
    s=scale
    pygame.draw.rect(base, (220,220,210), (3*s,4*s,10*s,8*s))
    pygame.draw.rect(base, (30,30,30), (5*s,5*s,2*s,2*s))
    pygame.draw.rect(base, (30,30,30), (9*s,5*s,2*s,2*s))
    return base

def make_tileset():
    # returns dict of tile surfaces: grass, dirt, stone, water, ruin, cave
    tsize = TILE
    tiles = {}
    g = pygame.Surface((tsize,tsize)); g.fill((36,120,46)); tiles['grass'] = g
    d = pygame.Surface((tsize,tsize)); d.fill((100,70,40)); tiles['dirt']=d
    st = pygame.Surface((tsize,tsize)); st.fill((90,90,100)); tiles['stone']=st
    w = pygame.Surface((tsize,tsize)); w.fill((18,40,85)); tiles['water']=w
    ru = pygame.Surface((tsize,tsize)); ru.fill((86,86,98)); tiles['ruin']=ru
    ca = pygame.Surface((tsize,tsize)); ca.fill((20,20,28)); tiles['cave']=ca
    fo = pygame.Surface((tsize,tsize)); fo.fill((18,72,22)); tiles['forest']=fo
    return tiles

def make_campfire_sprite(scale=2):
    base = pygame.Surface((10*scale,10*scale), pygame.SRCALPHA)
    s=scale
    pygame.draw.rect(base, (100,60,30), (3*s,6*s,4*s,2*s))
    pygame.draw.circle(base, (255,120,30), (5*s,4*s), 3*s)
    pygame.draw.circle(base, (255,220,120), (5*s,3*s), 1*s)
    return base

# ---------- Фиксированная карта (вариант 2) ----------
def create_fixed_map():
    # создаём пустую карту grass, затем вручную добавляем регионы: лес, руины, замок, пещера
    grid = [['grass' for _ in range(MAP_H)] for _ in range(MAP_W)]
    # лес в левом верхнем
    for x in range(2, 18):
        for y in range(2, 16):
            if random.random() < 0.65: grid[x][y] = 'forest'
    # руины в центре
    cx, cy = MAP_W//2, MAP_H//2
    for x in range(cx-8, cx+8):
        for y in range(cy-6, cy+6):
            if random.random() < 0.75: grid[x][y] = 'ruin'
    # небольшой замок справа
    sx, sy = MAP_W-14, MAP_H//2 - 4
    for x in range(sx-4, sx+6):
        for y in range(sy-4, sy+6):
            if 0 <= x < MAP_W and 0 <= y < MAP_H:
                if (abs(x-sx) < 3 and abs(y-sy) < 3) or random.random() < 0.6:
                    grid[x][y] = 'ruin'
    # пещера снизу
    for x in range(12, 28):
        for y in range(MAP_H-10, MAP_H-4):
            if random.random() < 0.85: grid[x][y] = 'cave'
    # добавим каменные островки
    for _ in range(80):
        x = random.randrange(0, MAP_W); y = random.randrange(0, MAP_H)
        if random.random() < 0.04: grid[x][y] = 'stone'
    return grid

# ---------- Классы сущностей ----------
class Entity(pygame.sprite.Sprite):
    def __init__(self, surf, x, y):
        super().__init__()
        self.image = surf
        self.x = x
        self.y = y
    def world_rect(self):
        w,h = self.image.get_size()
        return pygame.Rect(self.x - w//2, self.y - h//2, w, h)

class Player(Entity):
    def __init__(self, surf, x, y):
        super().__init__(surf, x, y)
        self.max_hp = 30
        self.hp = self.max_hp
        self.max_stamina = 12.0
        self.stamina = self.max_stamina
        self.hunger = 0.0
        self.hunger_rate = 0.2  # per second
        self.speed = 180.0
        self.attack_cd = 0.45; self.attack_timer = 0.0
        self.blocking = False
        self.dodge_cd = 1.6; self.dodge_timer = 0.0
        self.inventory = {"food":3, "wood":0, "stone":0, "potion":0}
        self.equipped = {"weapon":"rusty","armor":"cloth"}
        self.xp = 0; self.level = 1

    def update(self, dt, keys):
        # hunger & stamina regen
        self.hunger = min(100, self.hunger + self.hunger_rate*dt)
        if self.stamina < self.max_stamina: self.stamina = min(self.max_stamina, self.stamina + dt*1.2)
        if self.attack_timer > 0: self.attack_timer = max(0, self.attack_timer - dt)
        if self.dodge_timer > 0: self.dodge_timer = max(0, self.dodge_timer - dt)

        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if dx != 0 or dy != 0:
            l = math.hypot(dx,dy)
            dx /= l; dy /= l
            sp = self.speed * (0.8 if self.hunger > 70 else 1.0)
            self.x += dx * sp * dt
            self.y += dy * sp * dt
        # bounds clamp
        self.x = clamp(self.x, 16, MAP_W*TILE-16)
        self.y = clamp(self.y, 16, MAP_H*TILE-16)

    def attack(self, game):
        if self.attack_timer > 0 or self.stamina < 1.0: return
        self.attack_timer = self.attack_cd
        self.stamina -= 1.6
        hits = []
        ar = pygame.Rect(self.x-44, self.y-44, 88, 88)
        for e in game.enemies:
            if e.alive and ar.colliderect(e.world_rect()):
                hits.append(e)
        for h in hits:
            dmg = 6 + (2 if self.equipped.get("weapon")=="steel" else 0)
            h.take_damage(dmg, game)
            # small xp per hit
            self.xp += 2

    def block(self):
        if self.stamina < 0.5: return False
        self.blocking = True
        self.stamina -= 0.5
        return True

    def dodge(self):
        if self.dodge_timer > 0 or self.stamina < 2.0: return False
        self.dodge_timer = self.dodge_cd
        self.stamina -= 2.0
        # simple dash forward based on random direction of current movement
        ang = random.uniform(0, math.tau)
        self.x += math.cos(ang)*48
        self.y += math.sin(ang)*48
        self.x = clamp(self.x, 16, MAP_W*TILE-16)
        self.y = clamp(self.y, 16, MAP_H*TILE-16)
        return True

    def pickup(self, item):
        self.inventory[item.kind] = self.inventory.get(item.kind, 0) + 1

class Enemy(Entity):
    def __init__(self, surf, x, y, kind="goblin"):
        super().__init__(surf, x, y)
        self.kind = kind
        if kind == "goblin":
            self.max_hp = 10; self.hp = 10; self.speed = 90; self.dmg = 2; self.xp = 6
        else:
            self.max_hp = 14; self.hp = 14; self.speed = 70; self.dmg = 3; self.xp = 10
        self.attack_timer = 0.0; self.attack_cd = 1.0
        self.alive = True

    def update(self, dt, player, game):
        if not self.alive: return
        dist = math.hypot(player.x - self.x, player.y - self.y)
        if dist < 220:
            dx = player.x - self.x; dy = player.y - self.y
            l = math.hypot(dx,dy) or 1
            self.x += dx/l * self.speed * dt
            self.y += dy/l * self.speed * dt
            if self.attack_timer <= 0 and dist < 28:
                self.attack(player)
                self.attack_timer = self.attack_cd
        else:
            # wander
            if random.random() < 0.01:
                self.x += random.uniform(-1,1) * TILE*0.2
                self.y += random.uniform(-1,1) * TILE*0.2
        if self.attack_timer > 0: self.attack_timer = max(0, self.attack_timer - dt)

    def attack(self, player):
        if player.blocking:
            actual = max(0, self.dmg - 2)
            player.hp -= actual
        else:
            player.hp -= self.dmg
        # small knockback
        player.x += random.choice([-6,6])
        if player.hp <= 0:
            player.hp = 0

    def take_damage(self, amount, game):
        self.hp -= amount
        game.spawn_particles((self.x, self.y), 8, (255,80,80))
        if self.hp <= 0:
            self.die(game)

    def die(self, game):
        self.alive = False
        # drop loot
        if random.random() < 0.6:
            it = Item(self.x, self.y, random.choice(["food","wood","stone"]))
            game.items.append(it)
        game.player.xp += self.xp

class Item:
    def __init__(self, x, y, kind="food"):
        self.x = x; self.y = y; self.kind = kind

# ---------- Основной Game класс ----------
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Medieval Survival — Fixed Map")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 16)
        self.big = pygame.font.SysFont("Consolas", 28)

        # assets in memory
        self.tiles = make_tileset()
        self.spr_knight = make_knight_sprite(scale=3)
        self.spr_goblin = make_goblin_sprite(scale=3)
        self.spr_skel = make_skeleton_sprite(scale=3)
        self.spr_camp = make_campfire_sprite(scale=3)

        # map & world
        self.map = create_fixed_map()
        self.specials = []  # can place interactive points if needed

        # player - attempt load save
        self.last_autosave = time.time()
        saved = load_json(SAVE_FILE)
        if saved and "player" in saved:
            p = saved["player"]
            self.player = Player(self.spr_knight, p.get("x", WIDTH//2), p.get("y", HEIGHT//2))
            self.player.hp = p.get("hp", self.player.max_hp)
            self.player.stamina = p.get("stamina", self.player.max_stamina)
            self.player.hunger = p.get("hunger", 0.0)
            self.player.inventory = p.get("inventory", self.player.inventory)
            self.player.equipped = p.get("equipped", self.player.equipped)
            self.player.xp = p.get("xp", 0)
            self.player.level = p.get("level", 1)
            self.time_of_day = saved.get("time_of_day", 9.0)
            print("Save loaded.")
        else:
            # default start
            self.player = Player(self.spr_knight, MAP_W*TILE//2, MAP_H*TILE//2)
            self.time_of_day = 9.0

        # camera
        self.camera_x = clamp(self.player.x - WIDTH//2, 0, MAP_W*TILE - WIDTH)
        self.camera_y = clamp(self.player.y - HEIGHT//2, 0, MAP_H*TILE - HEIGHT)

        # enemies/items/particles
        self.enemies = []
        self.items = []
        self.particles = []
        self.spawn_initial_enemies()

        # sounds (optionally) - none required
        self.snd_hit = None
        self.snd_swing = None

        # UI/messages
        self.messages = []
        self.paused = False
        self.running = True

    def spawn_initial_enemies(self):
        # spawn balanced set: clusters near forest and ruins
        # spawn goblins near left forest, skeletons near ruins
        for _ in range(18):
            # pick random tile of appropriate type
            for _ in range(60):
                x = random.randrange(0, MAP_W); y = random.randrange(0, MAP_H)
                t = self.map[x][y]
                if t == 'forest':
                    rx = x*TILE + TILE//2; ry = y*TILE + TILE//2
                    self.enemies.append(Enemy(self.spr_goblin, rx + random.randint(-20,20), ry + random.randint(-20,20), "goblin"))
                    break
        for _ in range(14):
            for _ in range(80):
                x = random.randrange(0, MAP_W); y = random.randrange(0, MAP_H)
                t = self.map[x][y]
                if t == 'ruin':
                    rx = x*TILE + TILE//2; ry = y*TILE + TILE//2
                    self.enemies.append(Enemy(self.spr_skel, rx + random.randint(-24,24), ry + random.randint(-24,24), "skeleton"))
                    break

    def spawn_particles(self, pos, count=10, color=(200,200,200)):
        for _ in range(count):
            ang = random.random()*math.tau
            speed = random.uniform(20,160)
            vx = math.cos(ang)*speed; vy = math.sin(ang)*speed
            life = random.uniform(0.3,1.2)
            self.particles.append({"x":pos[0],"y":pos[1],"vx":vx,"vy":vy,"life":life,"col":color})

    def world_to_screen(self, wx, wy):
        return int(wx - self.camera_x), int(wy - self.camera_y)

    def try_pickup(self):
        for it in list(self.items):
            if math.hypot(self.player.x - it.x, self.player.y - it.y) < 28:
                self.player.pickup(it)
                self.items.remove(it)
                self.message(f"Picked up {it.kind}")

    def craft(self):
        inv = self.player.inventory
        # simple recipes
        if inv.get("wood",0) >= 4 and inv.get("stone",0) >= 1:
            inv["wood"] -= 4; inv["stone"] -= 1
            self.player.inventory["potion"] = self.player.inventory.get("potion",0) + 1
            self.message("Crafted: potion")
        elif inv.get("wood",0) >= 6:
            inv["wood"] -= 6
            self.player.equipped["weapon"] = "steel"
            self.message("Crafted: steel weapon")

    def message(self, txt, t=4.0):
        self.messages.append({"text":txt, "t":t})

    def save_game(self):
        data = {
            "player": {
                "x": self.player.x, "y": self.player.y,
                "hp": self.player.hp, "stamina": self.player.stamina,
                "hunger": self.player.hunger, "inventory": self.player.inventory,
                "equipped": self.player.equipped, "xp": self.player.xp, "level": self.player.level
            },
            "time_of_day": self.time_of_day
        }
        save_json(SAVE_FILE, data)
        self.last_autosave = time.time()
        self.message("Game saved.")

    def autosave_tick(self):
        if time.time() - self.last_autosave > AUTOSAVE_INTERVAL:
            self.save_game()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.save_game(); self.running = False
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        self.save_game(); self.running = False
                    if ev.key == pygame.K_p:
                        self.paused = not self.paused
                    if ev.key == pygame.K_e:
                        self.try_pickup()
                        # small chance to create campfire item at player
                        if random.random() < 0.08:
                            self.items.append(Item(self.player.x + 6, self.player.y + 6, "campfire"))
                    if ev.key == pygame.K_c:
                        self.craft()
                    if ev.key == pygame.K_i:
                        print("Inventory:", self.player.inventory)
                        self.message("Inventory printed to console")
                    if ev.key == pygame.K_j or ev.key == pygame.K_SPACE:
                        self.player.attack(self)
                    if ev.key == pygame.K_k:
                        self.player.block()
                    if ev.key == pygame.K_l:
                        self.player.dodge()
                    if ev.key == pygame.K_o:
                        # use potion
                        if self.player.inventory.get("potion",0) > 0:
                            self.player.inventory["potion"] -= 1
                            self.player.hp = min(self.player.max_hp, self.player.hp + 12)
                            self.message("Used potion")
            if not self.paused:
                keys = pygame.key.get_pressed()
                self.player.blocking = False
                self.player.update(dt, keys)
                # update enemies
                for e in list(self.enemies):
                    e.update(dt, self.player, self)
                    if not e.alive:
                        try: self.enemies.remove(e)
                        except: pass
                # spawn occasional small mobs at night
                if random.random() < (0.006 if (self.time_of_day > 20 or self.time_of_day < 5) else 0.002):
                    x = random.randint(0, MAP_W*TILE); y = random.randint(0, MAP_H*TILE)
                    kind = random.choice(["goblin","skeleton"])
                    surf = self.spr_goblin if kind == "goblin" else self.spr_skel
                    self.enemies.append(Enemy(surf, x, y, kind))
                # particles
                for p in list(self.particles):
                    p["life"] -= dt
                    if p["life"] <= 0: self.particles.remove(p); continue
                    p["x"] += p["vx"]*dt; p["y"] += p["vy"]*dt
                # items spawn occasionally
                if random.random() < 0.002:
                    self.items.append(Item(random.randint(0,MAP_W*TILE), random.randint(0,MAP_H*TILE), random.choice(["wood","stone","food"])))
                # time progression
                self.time_of_day = (self.time_of_day + dt*0.02) % 24
                # hunger damage
                if self.player.hunger > 98:
                    self.player.hp = max(0, self.player.hp - 0.2*dt)
            # update camera
            self.camera_x = clamp(self.player.x - WIDTH//2, 0, max(0, MAP_W*TILE - WIDTH))
            self.camera_y = clamp(self.player.y - HEIGHT//2, 0, max(0, MAP_H*TILE - HEIGHT))
            # autosave
            self.autosave_tick()
            # draw
            self.draw()
        pygame.quit()

    def draw(self):
        # world
        self.screen.fill((6,6,12))
        world = pygame.Surface((WIDTH, HEIGHT))
        # draw tiles
        cam_tx0 = int(self.camera_x // TILE); cam_ty0 = int(self.camera_y // TILE)
        ncols = WIDTH // TILE + 3; nrows = HEIGHT // TILE + 3
        for ix in range(cam_tx0, cam_tx0 + ncols):
            for jy in range(cam_ty0, cam_ty0 + nrows):
                if 0 <= ix < MAP_W and 0 <= jy < MAP_H:
                    tkind = self.map[ix][jy]
                    if tkind == 'grass':
                        color = (36,120,46)
                        tile_surf = self.tiles['grass']
                    elif tkind == 'forest':
                        color = (18,72,22)
                        tile_surf = self.tiles['forest']
                    elif tkind == 'ruin':
                        color = (86,86,98)
                        tile_surf = self.tiles['ruin']
                    elif tkind == 'cave':
                        color = (20,20,26)
                        tile_surf = self.tiles['cave']
                    elif tkind == 'stone':
                        color = (90,90,100)
                        tile_surf = self.tiles['stone']
                    else:
                        color = (40,90,40)
                        tile_surf = self.tiles['dirt']
                    rx = ix*TILE - self.camera_x; ry = jy*TILE - self.camera_y
                    world.blit(tile_surf, (rx, ry))
                    # small decoration: occasional tree dot for forest tiles
                    if tkind == 'forest' and random.random() < 0.02:
                        pygame.draw.circle(world, (40,120,40), (int(rx+12), int(ry+10)), 4)
        # draw items
        for it in self.items:
            sx, sy = self.world_to_screen(it.x, it.y)
            if it.kind == "campfire":
                world.blit(self.spr_camp, self.spr_camp.get_rect(center=(sx,sy)))
            else:
                col = (255,200,80) if it.kind == "food" else (150,110,70)
                pygame.draw.circle(world, col, (sx,sy), 6)
        # draw enemies
        for e in self.enemies:
            if not e.alive: continue
            sx, sy = self.world_to_screen(e.x, e.y)
            world.blit(e.image, e.image.get_rect(center=(sx,sy)))
            # hp bar
            hpw = int(28 * (e.hp / e.max_hp))
            pygame.draw.rect(world, (0,0,0), (sx-14, sy-22, 28, 5))
            pygame.draw.rect(world, (180,70,70), (sx-14, sy-22, hpw, 5))
        # draw player
        px, py = self.world_to_screen(self.player.x, self.player.y)
        world.blit(self.player.image, self.player.image.get_rect(center=(px,py)))
        # draw particles
        for p in self.particles:
            sx, sy = self.world_to_screen(p["x"], p["y"])
            pygame.draw.circle(world, p["col"], (int(sx), int(sy)), 3)
        # lighting: dark overlay for night, light around player and campfires
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if self.time_of_day > 19 or self.time_of_day < 6:
            alpha = 180
        elif self.time_of_day > 17 or self.time_of_day < 8:
            alpha = 90
        else:
            alpha = 30
        dark.fill((6,6,12, alpha))
        # subtract light circle at player
        pygame.draw.circle(dark, (6,6,12,0), (px,py), 140)
        # campfire lights
        for it in self.items:
            if it.kind == "campfire":
                sx, sy = self.world_to_screen(it.x, it.y)
                pygame.draw.circle(dark, (6,6,12,0), (sx,sy), 90)
        # blit world and dark overlay
        self.screen.blit(world, (0,0))
        self.screen.blit(dark, (0,0))
        # HUD
        self.draw_hud()
        # messages
        for i, m in enumerate(list(self.messages)[-5:]):
            self.screen.blit(self.font.render(m["text"], True, (220,220,200)), (18, HEIGHT-22 - i*20))
            m["t"] -= 1.0 / FPS
            if m["t"] <= 0:
                try: self.messages.remove(m)
                except: pass
        pygame.display.flip()

    def draw_hud(self):
        # panel
        pygame.draw.rect(self.screen, (12,12,18), (10,10, 340, 88), border_radius=6)
        # HP
        hpw = int(332 * (self.player.hp / max(1, self.player.max_hp)))
        pygame.draw.rect(self.screen, (180,60,60), (14,14, hpw, 24), border_radius=5)
        self.screen.blit(self.font.render(f"HP: {int(self.player.hp)}/{self.player.max_hp}", True, (240,240,240)), (18,16))
        # stamina/hunger
        self.screen.blit(self.font.render(f"STAM: {int(self.player.stamina)}/{int(self.player.max_stamina)}", True, (220,220,220)), (18,44))
        self.screen.blit(self.font.render(f"Hunger: {int(self.player.hunger)}", True, (220,220,220)), (200,44))
        # inventory short
        inv_text = " ".join([f"{k}:{v}" for k,v in self.player.inventory.items()])
        self.screen.blit(self.font.render(inv_text, True, (200,200,160)), (18,64))
        # time
        tod = f"{int(self.time_of_day):02d}:00"
        self.screen.blit(self.font.render("Time: "+tod, True, (200,200,200)), (WIDTH-140, 18))

# ---------- Точка входа ----------
if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        print("Critical error:", e)
        pygame.quit()
        raise
