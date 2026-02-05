import json
import os
import random
import time
import traceback

from tkinter import messagebox

from PIL import Image, ImageDraw

try:
    from ursina import (  # type: ignore
        AmbientLight,
        Button,
        DirectionalLight,
        Entity,
        Text,
        Ursina,
        Vec3,
        application,
        camera,
        color,
        curve,
        destroy,
        held_keys,
        invoke,
        load_texture,
        mouse,
        raycast,
        time as utime,
        window,
    )
    from ursina.prefabs.first_person_controller import FirstPersonController  # type: ignore
    from ursina.shaders import unlit_shader  # type: ignore
except Exception:
    raise SystemExit(
        "Не найдена библиотека ursina. Установи её командой:\n"
        "  py -m pip install ursina\n"
        "Потом запусти снова: py main.py"
    )


ROOT = os.path.dirname(__file__)
ASSETS = os.path.join(ROOT, "assets")
SAVE_PATH = os.path.join(ROOT, "save_3d.json")

os.makedirs(ASSETS, exist_ok=True)


def _save_png(path: str, img: Image.Image) -> None:
    img.save(path, format="PNG")


def _make_star_sky(size: int = 512) -> Image.Image:
    img = Image.new("RGB", (size, size), (8, 10, 18))
    dr = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(10 + (2 * (1 - t)))
        g = int(12 + (6 * (1 - t)))
        b = int(18 + (20 * (1 - t)))
        dr.line([(0, y), (size, y)], fill=(r, g, b))
    for _ in range(1400):
        x = random.randrange(0, size)
        y = random.randrange(0, size)
        if random.random() < 0.7:
            c = random.randint(190, 255)
            img.putpixel((x, y), (c, c, c))
        else:
            c = random.randint(150, 230)
            img.putpixel((x, y), (c, c, 255))
    return img


def _make_menu_bg(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (8, 10, 14, 255))
    dr = ImageDraw.Draw(img)
    c1 = (40, 80, 190)
    c2 = (180, 60, 200)
    c3 = (20, 180, 140)
    for y in range(size):
        t = y / max(1, size - 1)
        if t < 0.5:
            k = t / 0.5
            r = int(c1[0] * (1 - k) + c2[0] * k)
            g = int(c1[1] * (1 - k) + c2[1] * k)
            b = int(c1[2] * (1 - k) + c2[2] * k)
        else:
            k = (t - 0.5) / 0.5
            r = int(c2[0] * (1 - k) + c3[0] * k)
            g = int(c2[1] * (1 - k) + c3[1] * k)
            b = int(c2[2] * (1 - k) + c3[2] * k)
        dr.line([(0, y), (size, y)], fill=(r, g, b, 255))
    for _ in range(int(size * size * 0.02)):
        x = random.randrange(0, size)
        y = random.randrange(0, size)
        if random.random() < 0.6:
            img.putpixel((x, y), (0, 0, 0, random.randint(18, 55)))
        else:
            img.putpixel((x, y), (255, 255, 255, random.randint(6, 18)))
    return img


def _make_cursor_tex(size: int = 128) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = size // 2
    cy = size // 2
    r = int(size * 0.32)
    w = max(2, size // 32)
    dr.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(255, 255, 255, 230), width=w)
    dr.ellipse([(cx - r - 2, cy - r - 2), (cx + r + 2, cy + r + 2)], outline=(40, 190, 255, 140), width=max(1, w // 2))
    dot = max(2, size // 20)
    dr.ellipse([(cx - dot, cy - dot), (cx + dot, cy + dot)], fill=(255, 255, 255, 240))
    for _ in range(int(size * 18)):
        if random.random() < 0.15:
            x = random.randrange(0, size)
            y = random.randrange(0, size)
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) < (r + 4) * (r + 4):
                img.putpixel((x, y), (180, 230, 255, random.randint(20, 70)))
    return img


def _make_weapon_tex_variant(label: str, base_rgb, accent_rgb, size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (base_rgb[0], base_rgb[1], base_rgb[2], 255))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([(28, 28), (size - 28, size - 28)], radius=70, fill=(base_rgb[0], base_rgb[1], base_rgb[2], 255), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255), width=10)
    dr.rectangle([(70, int(size * 0.30)), (size - 70, int(size * 0.40))], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255))
    dr.rectangle([(70, int(size * 0.55)), (size - 70, int(size * 0.60))], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255))
    dr.text((80, int(size * 0.70)), label, fill=(10, 14, 18, 255))
    for _ in range(int(size * size * 0.012)):
        if random.random() < 0.06:
            x = random.randrange(0, size)
            y = random.randrange(0, size)
            img.putpixel((x, y), (max(0, base_rgb[0] - 6), max(0, base_rgb[1] - 6), max(0, base_rgb[2] - 6), 255))
    return img


def _make_weapon_tex(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (20, 22, 28, 255))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([(10, 10), (size - 10, size - 10)], radius=22, fill=(26, 28, 34, 255), outline=(90, 110, 140, 255), width=6)
    dr.rectangle([(30, 70), (size - 30, 110)], fill=(55, 65, 80, 255))
    dr.rectangle([(30, 140), (size - 30, 160)], fill=(55, 65, 80, 255))
    dr.rectangle([(40, 188), (size - 40, 214)], fill=(80, 160, 255, 255))
    dr.text((44, 192), "RIFLE", fill=(10, 14, 18, 255))
    for _ in range(900):
        x = random.randrange(0, size)
        y = random.randrange(0, size)
        if random.random() < 0.06:
            img.putpixel((x, y), (28, 30, 36, 255))
    return img


def _make_bullet_tex(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = size // 2
    cy = size // 2
    max_r = int(size * 0.45)
    for i in range(20):
        t = i / 19
        r = int(max_r * (1 - t))
        a = int(220 * (1 - t) ** 2)
        dr.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 210, 90, a))
    core = int(size * 0.10)
    dr.ellipse([(cx - core, cy - core), (cx + core, cy + core)], fill=(255, 255, 255, 240))
    gl = int(size * 0.18)
    dr.ellipse([(cx - gl, cy - gl), (cx + gl, cy + gl)], outline=(255, 245, 220, 120), width=max(1, size // 96))
    for _ in range(int(size * 10)):
        if random.random() < 0.15:
            x = random.randrange(0, size)
            y = random.randrange(0, size)
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) < max_r * max_r:
                img.putpixel((x, y), (255, 240, 190, random.randint(30, 80)))
    return img


def _make_enemy_tex(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (22, 18, 26, 255))
    dr = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(30 + 80 * (1 - t))
        g = int(20 + 30 * (1 - t))
        b = int(35 + 90 * (1 - t))
        dr.line([(0, y), (size, y)], fill=(r, g, b, 255))

    dr.rounded_rectangle([(12, 12), (size - 12, size - 12)], radius=int(size * 0.12), outline=(255, 120, 160, 255), width=max(3, size // 80))
    dr.rounded_rectangle([(20, 20), (size - 20, size - 20)], radius=int(size * 0.10), outline=(80, 220, 255, 120), width=max(2, size // 140))

    ex1 = int(size * 0.30)
    ex2 = int(size * 0.70)
    ey = int(size * 0.40)
    er = int(size * 0.10)
    dr.ellipse([(ex1 - er, ey - er), (ex1 + er, ey + er)], fill=(10, 10, 12, 255))
    dr.ellipse([(ex2 - er, ey - er), (ex2 + er, ey + er)], fill=(10, 10, 12, 255))
    pr = int(size * 0.035)
    dr.ellipse([(ex1 - pr, ey - pr), (ex1 + pr, ey + pr)], fill=(220, 255, 255, 255))
    dr.ellipse([(ex2 - pr, ey - pr), (ex2 + pr, ey + pr)], fill=(220, 255, 255, 255))
    dr.ellipse([(ex1 - pr // 2, ey - pr // 2), (ex1 + pr // 2, ey + pr // 2)], fill=(255, 60, 90, 200))
    dr.ellipse([(ex2 - pr // 2, ey - pr // 2), (ex2 + pr // 2, ey + pr // 2)], fill=(255, 60, 90, 200))

    my = int(size * 0.70)
    dr.arc([(int(size * 0.22), int(size * 0.52)), (int(size * 0.78), int(size * 0.92))], start=210, end=-30, fill=(20, 10, 10, 255), width=max(4, size // 45))
    dr.arc([(int(size * 0.22), int(size * 0.52)), (int(size * 0.78), int(size * 0.92))], start=210, end=-30, fill=(255, 80, 120, 140), width=max(2, size // 110))
    dr.line([(int(size * 0.25), my), (int(size * 0.75), my)], fill=(255, 140, 170, 120), width=max(1, size // 180))

    for _ in range(int(size * size * 0.015)):
        x = random.randrange(0, size)
        y = random.randrange(0, size)
        if random.random() < 0.25:
            img.putpixel((x, y), (random.randint(10, 50), random.randint(10, 40), random.randint(20, 70), 255))
        else:
            img.putpixel((x, y), (random.randint(110, 200), random.randint(30, 60), random.randint(80, 170), 70))
    return img


def _make_crystal_tex(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = size // 2
    top = (cx, int(size * 0.06))
    left = (int(size * 0.18), cx)
    bottom = (cx, int(size * 0.94))
    right = (int(size * 0.82), cx)
    base = (40, 220, 200)
    dark = (10, 140, 135)
    glow = (190, 255, 250)

    for i in range(18):
        t = i / 17
        y = int(size * 0.08 + t * size * 0.84)
        r = int(base[0] * (1 - t) + dark[0] * t)
        g = int(base[1] * (1 - t) + dark[1] * t)
        b = int(base[2] * (1 - t) + dark[2] * t)
        x0 = int(size * 0.30 - t * size * 0.06)
        x1 = int(size * 0.70 + t * size * 0.06)
        dr.line([(x0, y), (x1, y)], fill=(r, g, b, 95))

    dr.polygon([top, right, bottom, left], fill=(base[0], base[1], base[2], 230))
    dr.polygon([top, (cx + int(size * 0.15), cx), bottom, (cx, cx + int(size * 0.10)), (cx - int(size * 0.15), cx)], fill=(dark[0], dark[1], dark[2], 210))

    dr.line([top, bottom], fill=(glow[0], glow[1], glow[2], 180), width=max(2, size // 70))
    dr.line([left, right], fill=(glow[0], glow[1], glow[2], 140), width=max(2, size // 85))
    dr.polygon(
        [
            (cx, int(size * 0.10)),
            (cx + int(size * 0.08), int(size * 0.42)),
            (cx, int(size * 0.58)),
            (cx - int(size * 0.08), int(size * 0.42)),
        ],
        fill=(255, 255, 255, 120),
    )

    for _ in range(int(size * 18)):
        x = random.randrange(int(size * 0.22), int(size * 0.78))
        y = random.randrange(int(size * 0.10), int(size * 0.92))
        if random.random() < 0.06:
            img.putpixel((x, y), (glow[0], glow[1], glow[2], random.randint(50, 120)))
        elif random.random() < 0.15:
            img.putpixel((x, y), (base[0], base[1], base[2], random.randint(20, 60)))
    return img


def _make_gate_tex(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (40, 60, 110, 255))
    dr = ImageDraw.Draw(img)
    dr.rectangle([(12, 12), (size - 12, size - 12)], outline=(160, 210, 255, 255), width=8)
    for y in range(24, size - 24, 18):
        dr.line([(24, y), (size - 24, y)], fill=(70, 110, 190, 255), width=3)
    for x in range(24, size - 24, 22):
        dr.line([(x, 24), (x, size - 24)], fill=(70, 110, 190, 255), width=2)
    dr.ellipse([(size - 70, size // 2 - 10), (size - 46, size // 2 + 14)], fill=(255, 220, 120, 255))
    return img


def _make_ground_tex(size: int = 512) -> Image.Image:
    img = Image.new("RGB", (size, size), (155, 150, 140))
    dr = ImageDraw.Draw(img)
    for y in range(0, size, 64):
        dr.line([(0, y), (size, y)], fill=(120, 115, 110), width=3)
    for x in range(0, size, 64):
        dr.line([(x, 0), (x, size)], fill=(120, 115, 110), width=3)
    for _ in range(2200):
        x = random.randrange(0, size)
        y = random.randrange(0, size)
        c = random.randint(120, 175)
        img.putpixel((x, y), (c, c - 5, c - 10))
    return img


def _make_wall_tex(size: int = 512) -> Image.Image:
    img = Image.new("RGB", (size, size), (120, 100, 90))
    dr = ImageDraw.Draw(img)
    brick_h = 46
    brick_w = 92
    for row, y in enumerate(range(0, size + brick_h, brick_h)):
        offset = (brick_w // 2) if (row % 2 == 1) else 0
        for x in range(-offset, size + brick_w, brick_w):
            r = random.randint(95, 135)
            g = random.randint(75, 110)
            b = random.randint(65, 95)
            dr.rectangle([(x + 2, y + 2), (x + brick_w - 2, y + brick_h - 2)], fill=(r, g, b))
    for y in range(0, size, brick_h):
        dr.line([(0, y), (size, y)], fill=(55, 45, 40), width=3)
    return img


def _has_png_signature(path: str) -> bool:
    try:
        with open(path, 'rb') as f:
            sig = f.read(8)
        return sig == b'\x89PNG\r\n\x1a\n'
    except Exception:
        return False


def _ensure_valid_png(path: str, fallback_img_factory) -> None:
    # If file exists but is not a real PNG (often jpg/webp renamed to .png),
    # convert it to a proper PNG. If conversion fails, overwrite with fallback.
    if not os.path.exists(path):
        try:
            _save_png(path, fallback_img_factory())
        except Exception:
            return
        return

    if _has_png_signature(path):
        return

    tmp = path + '.tmp.png'
    try:
        with Image.open(path) as im:
            im.load()
            if im.mode not in ('RGB', 'RGBA'):
                im = im.convert('RGBA')
            im.save(tmp, format='PNG')
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        try:
            _save_png(path, fallback_img_factory())
        except Exception:
            return


def ensure_textures() -> None:
    random.seed(12345)
    # These must always be loadable, otherwise Ursina will crash on texture import.
    mapping = {
        "ground.png": lambda: _make_ground_tex(512),
        "wall.png": lambda: _make_wall_tex(512),
        "sky.png": lambda: _make_star_sky(512),
        "weapon.png": lambda: _make_weapon_tex(256),
        "weapon_rifle.png": lambda: _make_weapon_tex_variant("RIFLE", (20, 22, 28), (80, 160, 255), 1024),
        "weapon_smg.png": lambda: _make_weapon_tex_variant("SMG", (18, 20, 24), (120, 255, 180), 1024),
        "weapon_shotgun.png": lambda: _make_weapon_tex_variant("SHOTGUN", (24, 20, 18), (255, 190, 90), 1024),
        "weapon_sword.png": lambda: _make_weapon_tex_variant("SWORD", (20, 18, 24), (220, 120, 255), 1024),
        "bullet.png": lambda: _make_bullet_tex(256),
        "cursor.png": lambda: _make_cursor_tex(128),
        "menu_bg.png": lambda: _make_menu_bg(1024),
        "enemy.png": lambda: _make_enemy_tex(256),
        "enemy_hd.png": lambda: _make_enemy_tex(512),
        "crystal.png": lambda: _make_crystal_tex(256),
        "crystal_hd.png": lambda: _make_crystal_tex(512),
        "gate.png": lambda: _make_gate_tex(256),
    }
    for name, fn in mapping.items():
        _ensure_valid_png(os.path.join(ASSETS, name), fn)


def tex(filename: str, fallback: str):
    path = os.path.join(ASSETS, filename)
    if os.path.exists(path):
        return f"assets/{filename}"
    return fallback


class MissionState:
    def __init__(self):
        self.collected = 0
        self.collect_goal = 5
        self.killed = 0
        self.kill_goal = 6
        self.exit_unlocked = False

    def to_dict(self):
        return {
            "collected": self.collected,
            "collect_goal": self.collect_goal,
            "killed": self.killed,
            "kill_goal": self.kill_goal,
            "exit_unlocked": self.exit_unlocked,
        }

    @staticmethod
    def from_dict(d):
        ms = MissionState()
        ms.collected = int(d.get("collected", 0))
        ms.collect_goal = int(d.get("collect_goal", 5))
        ms.killed = int(d.get("killed", 0))
        ms.kill_goal = int(d.get("kill_goal", 6))
        ms.exit_unlocked = bool(d.get("exit_unlocked", False))
        return ms


class Enemy(Entity):
    def __init__(self, game, pos: Vec3):
        super().__init__(
            model="cube",
            color=color.rgba(0, 0, 0, 0),
            texture=None,
            scale=Vec3(1, 2, 1),
            position=pos,
            collider="box",
        )
        self.game = game
        self.shader = unlit_shader
        t = tex("enemy_hd.png", tex("enemy.png", "white_cube"))
        self.body_torso = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(0, 0.0, 0), scale=Vec3(0.9, 1.1, 0.55))
        self.body_head = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(0, 0.75, 0), scale=Vec3(0.55, 0.55, 0.55))
        self.body_arm_l = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(-0.65, 0.10, 0), scale=Vec3(0.25, 0.9, 0.25))
        self.body_arm_r = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(0.65, 0.10, 0), scale=Vec3(0.25, 0.9, 0.25))
        self.body_leg_l = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(-0.25, -0.85, 0), scale=Vec3(0.3, 1.0, 0.3))
        self.body_leg_r = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(0.25, -0.85, 0), scale=Vec3(0.3, 1.0, 0.3))
        for part in (self.body_torso, self.body_head, self.body_arm_l, self.body_arm_r, self.body_leg_l, self.body_leg_r):
            part.shader = unlit_shader
        self.max_hp = 35
        self.hp = 35
        self.speed = 3.2
        self.aggro_range = 18
        self.attack_range = 1.6
        self.attack_cooldown = 0.55
        self._next_attack = 0.0
        self.wander_target = self.position
        self._next_wander = time.time() + random.uniform(1.0, 2.5)

    def take_damage(self, dmg: int):
        self.hp = max(0, self.hp - dmg)
        if self.hp == 0:
            self.game.on_enemy_killed(self)

    def _can_see_player(self) -> bool:
        p = self.game.player
        if (p.position - self.position).length() > self.aggro_range:
            return False
        origin = self.world_position + Vec3(0, 0.8, 0)
        dir_vec = (p.world_position + Vec3(0, 0.8, 0)) - origin
        hit = raycast(origin, dir_vec.normalized(), distance=dir_vec.length(), ignore=(self,))
        return hit.entity == p

    def _try_attack(self):
        now = time.time()
        if now < self._next_attack:
            return
        self._next_attack = now + self.attack_cooldown
        self.game.damage_player(6)

    def _wander(self):
        if time.time() < self._next_wander:
            return
        self._next_wander = time.time() + random.uniform(1.0, 2.5)
        r = 8
        self.wander_target = Vec3(
            self.position.x + random.uniform(-r, r),
            1,
            self.position.z + random.uniform(-r, r),
        )

    def update(self):
        if self.hp <= 0:
            return

        p = self.game.player
        dist = (p.position - self.position).length()

        repel = Vec3(0, 0, 0)
        for other in self.game.enemies:
            if other is self or other.hp <= 0:
                continue
            d = (self.position - other.position)
            dl = d.length()
            if 0 < dl < 1.4:
                repel += d.normalized() * (1.4 - dl)
        if repel.length() > 0:
            self.position += Vec3(repel.x, 0, repel.z) * 0.7 * utime.dt

        if self._can_see_player():
            self.look_at(p.position)
            if dist <= self.attack_range:
                self._try_attack()
                return

            step = (p.position - self.position).normalized() * self.speed * utime.dt
            hit = raycast(self.position + Vec3(0, 0.5, 0), step.normalized(), distance=step.length() + 0.2, ignore=(self, p))
            if not hit.hit:
                self.position += Vec3(step.x, 0, step.z)
            else:
                side = Vec3(-step.z, 0, step.x)
                hit2 = raycast(self.position + Vec3(0, 0.5, 0), side.normalized(), distance=0.8, ignore=(self, p))
                if not hit2.hit:
                    self.position += side.normalized() * self.speed * utime.dt
            return

        self._wander()
        to_t = self.wander_target - self.position
        if to_t.length() > 0.8:
            step = to_t.normalized() * (self.speed * 0.65) * utime.dt
            hit = raycast(self.position + Vec3(0, 0.5, 0), step.normalized(), distance=step.length() + 0.2, ignore=(self, p))
            if not hit.hit:
                self.position += Vec3(step.x, 0, step.z)


class Bullet(Entity):
    def __init__(self, game, origin: Vec3, direction: Vec3):
        super().__init__(
            model="quad",
            scale=0.38,
            color=color.white,
            texture=tex("bullet.png", "white_cube"),
            double_sided=True,
            billboard=True,
            position=origin,
        )
        self.game = game
        self.shader = unlit_shader
        self.dir = direction.normalized()
        self.speed = 28.0
        self.life = 1.1

    def update(self):
        step = self.dir * self.speed * utime.dt
        hit = raycast(self.world_position, self.dir, distance=step.length() + 0.3, ignore=(self, self.game.player))
        if hit.hit:
            if hasattr(hit.entity, 'take_damage'):
                try:
                    hit.entity.take_damage(int(getattr(self, 'dmg', 18)))
                except Exception:
                    pass
            destroy(self)
            return
        self.position += step
        self.life -= utime.dt
        if self.life <= 0:
            destroy(self)


class Boss(Entity):
    def __init__(self, game, pos: Vec3):
        super().__init__(
            model="cube",
            color=color.rgba(0, 0, 0, 0),
            texture=None,
            scale=Vec3(2.2, 3.6, 2.0),
            position=pos,
            collider="box",
        )
        self.game = game
        self.shader = unlit_shader
        t = tex("enemy_hd.png", tex("enemy.png", "white_cube"))
        self.body_torso = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(0, 0.1, 0), scale=Vec3(1.9, 2.2, 1.1))
        self.body_head = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(0, 1.55, 0), scale=Vec3(1.05, 1.05, 1.05))
        self.body_arm_l = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(-1.35, 0.4, 0), scale=Vec3(0.45, 1.8, 0.45))
        self.body_arm_r = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(1.35, 0.4, 0), scale=Vec3(0.45, 1.8, 0.45))
        self.body_leg_l = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(-0.55, -1.55, 0), scale=Vec3(0.55, 2.0, 0.55))
        self.body_leg_r = Entity(parent=self, model='cube', texture=t, color=color.white, position=Vec3(0.55, -1.55, 0), scale=Vec3(0.55, 2.0, 0.55))
        for part in (self.body_torso, self.body_head, self.body_arm_l, self.body_arm_r, self.body_leg_l, self.body_leg_r):
            part.shader = unlit_shader

        self.max_hp = 320
        self.hp = 320
        self.speed = 2.3
        self.aggro_range = 34
        self.laser_range = 28
        self.laser_cooldown = 1.25
        self._next_laser = time.time() + 1.0

    def take_damage(self, dmg: int):
        self.hp = max(0, self.hp - int(dmg))
        if self.hp == 0:
            destroy(self)
            self.game.ui_hint.text = "Босс повержен!"

    def _can_see_player(self) -> bool:
        p = self.game.player
        if (p.position - self.position).length() > self.aggro_range:
            return False
        origin = self.world_position + Vec3(0, 1.6, 0)
        dir_vec = (p.world_position + Vec3(0, 0.9, 0)) - origin
        hit = raycast(origin, dir_vec.normalized(), distance=dir_vec.length(), ignore=(self,))
        return hit.entity == p

    def _shoot_laser(self):
        now = time.time()
        if now < self._next_laser:
            return
        self._next_laser = now + self.laser_cooldown
        p = self.game.player
        origin = self.world_position + Vec3(0, 1.6, 0)
        dir_vec = (p.world_position + Vec3(0, 0.9, 0)) - origin
        dist = min(self.laser_range, max(1.0, dir_vec.length()))
        hit = raycast(origin, dir_vec.normalized(), distance=dist, ignore=(self,))
        end = origin + dir_vec.normalized() * dist
        if hit.hit:
            end = hit.world_point
            if hit.entity == p:
                self.game.damage_player(12)

        beam = Entity(
            model='cube',
            color=color.rgba(255, 60, 90, 220),
            position=(origin + end) * 0.5,
            scale=Vec3(0.08, 0.08, (end - origin).length()),
        )
        beam.look_at(end)
        beam.shader = unlit_shader
        invoke(destroy, beam, delay=0.08)

    def update(self):
        if self.hp <= 0:
            return
        p = self.game.player
        dist = (p.position - self.position).length()
        if self._can_see_player():
            self.look_at(p.position)
            if dist <= self.laser_range:
                self._shoot_laser()
            desired = 12
            if dist > desired:
                step = (p.position - self.position).normalized() * self.speed * utime.dt
                hit = raycast(self.position + Vec3(0, 1.0, 0), step.normalized(), distance=step.length() + 0.4, ignore=(self, p))
                if not hit.hit:
                    self.position += Vec3(step.x, 0, step.z)
            return


class Crystal(Entity):
    def __init__(self, game, pos: Vec3):
        super().__init__(
            model="quad",
            color=color.white,
            texture=tex("crystal_hd.png", tex("crystal.png", "white_cube")),
            scale=1.25,
            position=pos,
            double_sided=True,
            billboard=True,
            collider="box",
        )
        self.game = game
        self.shader = unlit_shader
        self.spin = random.uniform(-140, 140)

    def update(self):
        self.rotation_y += self.spin * utime.dt
        if (self.game.player.position - self.position).length() < 1.2:
            self.game.on_crystal_collected(self)


class Medkit(Entity):
    def __init__(self, game, pos: Vec3):
        super().__init__(
            model="cube",
            color=color.rgb(255, 240, 240),
            scale=0.6,
            position=pos,
            collider="box",
        )
        self.game = game
        self.shader = unlit_shader
        self.rotation_y = random.uniform(0, 360)
        self.amount = 30

    def update(self):
        self.rotation_y += 90 * utime.dt
        if (self.game.player.position - self.position).length() < 1.2:
            self.game.on_medkit(self)


class AmmoBox(Entity):
    def __init__(self, game, pos: Vec3):
        super().__init__(
            model="cube",
            color=color.rgb(255, 209, 102),
            scale=0.6,
            position=pos,
            collider="box",
        )
        self.game = game
        self.shader = unlit_shader
        self.rotation_y = random.uniform(0, 360)
        self.amount = 45

    def update(self):
        self.rotation_y += 70 * utime.dt
        if (self.game.player.position - self.position).length() < 1.2:
            self.game.on_ammo(self)


class ExitGate(Entity):
    def __init__(self, game, pos: Vec3):
        super().__init__(
            model="cube",
            color=color.white,
            texture=tex("gate.png", "white_cube"),
            scale=Vec3(3.2, 3.2, 0.6),
            position=pos,
            collider="box",
        )
        self.game = game
        self.shader = unlit_shader
        self.enabled = False
        self.visible = False

    def update(self):
        if not self.enabled:
            return
        if (self.game.player.position - self.position).length() < 2.0:
            self.game.on_victory()


class Game:
    def __init__(self):
        ensure_textures()

        self.app = Ursina()
        window.title = "Ursina 3D Mission Game"
        window.fps_counter.enabled = True
        window.exit_button.visible = False
        window.fullscreen = True
        window.color = color.rgb(8, 10, 14)
        camera.clear_color = color.rgb(8, 10, 14)

        self.light_sun = DirectionalLight(color=color.rgb(255, 255, 255))
        self.light_sun.look_at(Vec3(1, -1.5, 1))
        self.light_amb = AmbientLight(color=color.rgba(80, 90, 120, 120))

        self.sky = Entity(
            model='sphere',
            scale=500,
            texture=tex('sky.png', 'white_cube'),
            double_sided=True,
        )
        self.sky.shader = unlit_shader
        self.sky.color = color.white

        self.ground = Entity(
            model="plane",
            collider="box",
            scale=80,
            texture=tex("ground.png", "grass"),
            texture_scale=(20, 20),
            color=color.white,
        )
        self.ground.shader = unlit_shader

        self.walls = []
        self.enemies = []
        self.crystals = []
        self.medkits = []
        self.ammoboxes = []

        self.player = FirstPersonController(
            position=Vec3(0, 2, 0),
            speed=6,
            origin_y=-0.5,
        )
        self.base_speed = 6
        self.sprint_speed = 11
        self.sprint_toggle = False
        self._last_sprint_toggle = 0.0
        self.player.gravity = 1
        self.player.cursor.visible = False
        self.player.collider = "box"
        self.player.health = 100
        self.player.max_health = 100
        self.player.jump_height = 2
        self.player.jump_duration = 0.3

        camera.fov = 85

        self.ms = MissionState()
        self.exit_gate = ExitGate(self, Vec3(0, 1.6, 34))

        self.ui_hp = Text(text="", position=(-0.86, 0.46), origin=(0, 0), scale=1.2)
        self.ui_m = Text(text="", position=(-0.86, 0.36), origin=(0, 0), scale=1.05)
        self.ui_hint = Text(text="", position=(-0.86, 0.18), origin=(0, 0), scale=0.95)
        self.ui_weapon = Text(text="", position=(-0.86, 0.08), origin=(0, 0), scale=1.0)
        self.crosshair = Text(text="+", position=(0, 0), origin=(0, 0), scale=1.8, color=color.rgba(255, 255, 255, 220))
        self.debug_text = Text(text="", position=(0, -0.42), origin=(0, 0), scale=1.1, color=color.rgba(255, 255, 255, 220))
        self.ui_input = Text(text="", position=(0.55, 0.46), origin=(0, 0), scale=0.85, color=color.rgba(255, 255, 255, 200))
        self._last_key = ""

        self.is_paused = False
        self.is_crashed = False
        self.pause_text = Text(text="PAUSED (P)\nTAB — lock/unlock мышь\nESC — отпустить мышь", position=(0, 0.15), origin=(0, 0), scale=1.7, color=color.rgba(255, 255, 255, 240))
        self.pause_text.enabled = False
        self.error_text = Text(text="", position=(0, 0), origin=(0, 0), scale=1.05, color=color.rgba(255, 110, 110, 240))
        self.error_text.enabled = False

        self.menu_open = False
        self.shop_open = False
        self.menu_root = None
        self.shop_root = None
        self.btn_load = None

        self.splash_active = False
        self.splash_root = None

        mouse.visible = False
        self.custom_cursor = Entity(
            parent=camera.ui,
            model='quad',
            texture=tex('cursor.png', 'white_cube'),
            color=color.white,
            scale=0.032,
            z=-0.01,
            enabled=False,
        )
        self.custom_cursor.shader = unlit_shader
        self.custom_cursor.always_on_top = True

        self.weapon_model = Entity(
            parent=camera,
            model='cube',
            texture=tex('weapon_rifle.png', 'white_cube'),
            color=color.white,
            position=Vec3(0.55, -0.36, 1.05),
            rotation=Vec3(-8, -18, 8),
            scale=Vec3(0.35, 0.18, 0.75),
        )
        self.weapon_model.shader = unlit_shader
        self._weapon_base_pos = Vec3(self.weapon_model.x, self.weapon_model.y, self.weapon_model.z)
        self._weapon_base_rot = Vec3(self.weapon_model.rotation_x, self.weapon_model.rotation_y, self.weapon_model.rotation_z)
        self._weapon_kick = 0.0

        self.player_model = Entity(parent=self.player, position=Vec3(0, -0.95, 0), scale=1)
        pt = tex('weapon.png', 'white_cube')
        self.player_torso = Entity(parent=self.player_model, model='cube', texture=pt, color=color.white, position=Vec3(0, 0.0, 0), scale=Vec3(0.95, 1.2, 0.6))
        self.player_head = Entity(parent=self.player_model, model='cube', texture=pt, color=color.white, position=Vec3(0, 0.85, 0), scale=Vec3(0.55, 0.55, 0.55))
        self.player_arm_l = Entity(parent=self.player_model, model='cube', texture=pt, color=color.white, position=Vec3(-0.7, 0.10, 0), scale=Vec3(0.25, 0.95, 0.25))
        self.player_arm_r = Entity(parent=self.player_model, model='cube', texture=pt, color=color.white, position=Vec3(0.7, 0.10, 0), scale=Vec3(0.25, 0.95, 0.25))
        self.player_leg_l = Entity(parent=self.player_model, model='cube', texture=pt, color=color.white, position=Vec3(-0.25, -0.95, 0), scale=Vec3(0.3, 1.05, 0.3))
        self.player_leg_r = Entity(parent=self.player_model, model='cube', texture=pt, color=color.white, position=Vec3(0.25, -0.95, 0), scale=Vec3(0.3, 1.05, 0.3))
        for part in (self.player_torso, self.player_head, self.player_arm_l, self.player_arm_r, self.player_leg_l, self.player_leg_r):
            part.shader = unlit_shader
        self.player_model.enabled = False

        self._cooldown_shot = 0.0
        self.mag_size = 30
        self.ammo_in_mag = 30
        self.ammo_reserve = 120
        self.reload_time = 1.15
        self._reloading_until = 0.0
        self.fire_rate = 0.11
        self.spread = 0.012
        self._cooldown_melee = 0.0

        self.weapons = [
            {
                'id': 'rifle',
                'name': 'Rifle',
                'kind': 'bullet',
                'texture': 'weapon_rifle.png',
                'mag': 30,
                'in_mag': 30,
                'reserve': 120,
                'reload': 1.15,
                'rate': 0.11,
                'spread': 0.012,
                'pellets': 1,
                'damage': 18,
                'vm_pos': Vec3(0.55, -0.36, 1.05),
                'vm_rot': Vec3(-8, -18, 8),
                'vm_scale': Vec3(0.35, 0.18, 0.75),
            },
            {
                'id': 'smg',
                'name': 'SMG',
                'kind': 'bullet',
                'texture': 'weapon_smg.png',
                'mag': 40,
                'in_mag': 40,
                'reserve': 200,
                'reload': 1.25,
                'rate': 0.07,
                'spread': 0.020,
                'pellets': 1,
                'damage': 12,
                'vm_pos': Vec3(0.56, -0.34, 1.0),
                'vm_rot': Vec3(-6, -18, 8),
                'vm_scale': Vec3(0.33, 0.17, 0.7),
            },
            {
                'id': 'shotgun',
                'name': 'Shotgun',
                'kind': 'bullet',
                'texture': 'weapon_shotgun.png',
                'mag': 8,
                'in_mag': 8,
                'reserve': 48,
                'reload': 1.55,
                'rate': 0.55,
                'spread': 0.055,
                'pellets': 7,
                'damage': 10,
                'vm_pos': Vec3(0.58, -0.38, 1.1),
                'vm_rot': Vec3(-10, -18, 10),
                'vm_scale': Vec3(0.42, 0.20, 0.95),
            },
            {
                'id': 'sword',
                'name': 'Sword',
                'kind': 'melee',
                'texture': 'weapon_sword.png',
                'mag': 0,
                'in_mag': 0,
                'reserve': 0,
                'reload': 0.0,
                'rate': 0.38,
                'spread': 0.0,
                'pellets': 0,
                'damage': 42,
                'vm_pos': Vec3(0.62, -0.44, 0.95),
                'vm_rot': Vec3(22, -30, 40),
                'vm_scale': Vec3(0.12, 0.65, 0.12),
            },
        ]
        self.active_weapon_index = 0
        self._equip_weapon(0, animate=False)

        self._build_level()
        self._load_save_if_any()

        self.boss = Boss(self, Vec3(0, 1.0, 44))

        self.debug_cube = Entity(
            model='cube',
            color=color.rgb(255, 0, 120),
            position=Vec3(0, 2.2, 6),
            scale=Vec3(1.2, 1.2, 1.2),
        )
        self.debug_cube.shader = unlit_shader
        self.debug_cube.enabled = False
        self.debug_text.enabled = False

        self._update_ui()

        self._create_menu_ui()
        self._create_shop_ui()
        self._create_splash_ui()
        self.show_splash()

    def on_crash(self, exc: Exception):
        self.is_crashed = True
        mouse.locked = False
        self.pause_text.enabled = False
        self.error_text.enabled = True
        msg = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        short = msg
        if len(short) > 1400:
            short = short[-1400:]
        self.error_text.text = "CRASH (Q/ESC to quit)\n" + short

    def on_medkit(self, m: Medkit):
        if m in self.medkits:
            self.medkits.remove(m)
        healed = min(m.amount, int(self.player.max_health - self.player.health))
        self.player.health = int(min(self.player.max_health, self.player.health + m.amount))
        m.enabled = False
        destroy(m)
        self._update_ui()
        if healed > 0:
            self.ui_hint.text = f"Аптечка: +{healed} HP"

    def on_ammo(self, a: AmmoBox):
        if a in self.ammoboxes:
            self.ammoboxes.remove(a)
        self.ammo_reserve += int(a.amount)
        a.enabled = False
        destroy(a)
        self._update_ui()
        self.ui_hint.text = f"Патроны: +{a.amount}"

    def input(self, key):
        self._last_key = str(key)

        if self.splash_active:
            if key in ('space', 'enter'):
                self._end_splash()
            return

        if key == 'f11':
            window.fullscreen = not window.fullscreen
            return

        if key == 'm':
            if not self.is_crashed:
                self.show_menu()
            return

        if key == 'p' and not (self.menu_open or self.shop_open):
            self.is_paused = not self.is_paused
            self.pause_text.enabled = self.is_paused
            if self.is_paused:
                mouse.locked = False
                mouse.visible = True
                self.custom_cursor.enabled = True
            else:
                mouse.visible = False
                self.custom_cursor.enabled = False
            return

        if self.is_crashed:
            if key in ('escape', 'q'):
                application.quit()
            return

        if self.is_paused and not (self.menu_open or self.shop_open):
            if key in ('tab', 'escape'):
                if key == 'escape':
                    mouse.locked = False
                if key == 'tab':
                    mouse.locked = not mouse.locked
            return

        gameplay_blocked = self.menu_open or self.shop_open or self.is_paused

        if key == 'escape':
            mouse.locked = False
        if key == 'tab':
            mouse.locked = not mouse.locked

        if not gameplay_blocked:
            if key == 'f5':
                self.save()
            if key == 'r':
                self.try_reload()
            if key in ('1', '2', '3', '4'):
                self._equip_weapon(int(key) - 1, animate=True)
            if key == 'f2':
                self.debug_cube.enabled = not self.debug_cube.enabled
                self.debug_text.enabled = not self.debug_text.enabled

        if not gameplay_blocked:
            if key in ('shift', 'left shift', 'right shift'):
                now = time.time()
                if now - self._last_sprint_toggle > 0.25:
                    self.sprint_toggle = not self.sprint_toggle
                    self._last_sprint_toggle = now

            if key == 'v':
                self.player_model.enabled = not self.player_model.enabled

            if key == 'left mouse down':
                if not mouse.locked:
                    mouse.locked = True
                self.try_shoot()

    def _build_level(self):
        random.seed(7)

        def add_wall(x, z, sx, sz, y=1.0):
            w = Entity(
                model="cube",
                collider="box",
                texture=tex("wall.png", "brick"),
                color=color.white,
                scale=Vec3(sx, 2.6, sz),
                position=Vec3(x, y, z),
            )
            w.shader = unlit_shader
            self.walls.append(w)

        for i in range(-22, 23):
            add_wall(i * 1.8, -22 * 1.8, 1.8, 1.8)
            add_wall(i * 1.8, 22 * 1.8, 1.8, 1.8)
        for i in range(-21, 22):
            add_wall(-22 * 1.8, i * 1.8, 1.8, 1.8)
            add_wall(22 * 1.8, i * 1.8, 1.8, 1.8)

        for _ in range(42):
            x = random.uniform(-30, 30)
            z = random.uniform(-28, 28)
            if abs(x) < 4 and abs(z) < 4:
                continue
            sx = random.choice([1.8, 3.6, 5.4])
            sz = random.choice([1.8, 3.6, 5.4])
            add_wall(x, z, sx, sz)

        for _ in range(self.ms.collect_goal):
            x = random.uniform(-26, 26)
            z = random.uniform(-24, 24)
            if abs(x) < 4 and abs(z) < 4:
                continue
            self.crystals.append(Crystal(self, Vec3(x, 1.2, z)))

        self.medkits = []
        self.ammoboxes = []

        for _ in range(4):
            x = random.uniform(-26, 26)
            z = random.uniform(-24, 24)
            if abs(x) < 4 and abs(z) < 4:
                continue
            self.medkits.append(Medkit(self, Vec3(x, 1.1, z)))

        for _ in range(5):
            x = random.uniform(-26, 26)
            z = random.uniform(-24, 24)
            if abs(x) < 4 and abs(z) < 4:
                continue
            self.ammoboxes.append(AmmoBox(self, Vec3(x, 1.1, z)))

        for _ in range(self.ms.kill_goal):
            x = random.uniform(-26, 26)
            z = random.uniform(-24, 24)
            if abs(x) < 5 and abs(z) < 5:
                continue
            self.enemies.append(Enemy(self, Vec3(x, 1.0, z)))

    def _update_ui(self):
        hp = self.player.health
        mhp = self.player.max_health
        self.ui_hp.text = f"HP: {hp}/{mhp}    WASD/стрелки — движение, SPACE — прыжок, ЛКМ — выстрел, R — перезарядка"
        self.ui_m.text = (
            f"Миссии: Кристаллы {self.ms.collected}/{self.ms.collect_goal}   "
            f"Враги {self.ms.killed}/{self.ms.kill_goal}"
        )
        if self.ms.exit_unlocked:
            self.ui_hint.text = "Выход открыт: доберись до ворот (синяя дверь)."
        else:
            self.ui_hint.text = "Собери кристаллы и уничтожь врагов, чтобы открыть выход."

        now = time.time()
        sprint = "ON" if self.sprint_toggle else "OFF"
        if now < self._reloading_until:
            self.ui_weapon.text = f"Оружие: {self.weapons[self.active_weapon_index]['name']}    SPRINT: {sprint}    Перезарядка... ({self.ammo_in_mag}/{self.mag_size} | {self.ammo_reserve})"
        else:
            if self.weapons[self.active_weapon_index]['kind'] == 'melee':
                self.ui_weapon.text = f"Оружие: {self.weapons[self.active_weapon_index]['name']}    SPRINT: {sprint}"
            else:
                self.ui_weapon.text = f"Оружие: {self.weapons[self.active_weapon_index]['name']}    SPRINT: {sprint}    Ammo: {self.ammo_in_mag}/{self.mag_size} | {self.ammo_reserve}"

        gt = self.ground.texture
        if isinstance(gt, str):
            gtn = gt
        else:
            gtn = getattr(gt, 'name', 'texture')
        self.debug_text.text = (
            f"pos: ({self.player.x:.1f}, {self.player.y:.1f}, {self.player.z:.1f})   mouse_locked: {mouse.locked}\n"
            f"ground_texture: {gtn} (assets/ground.png должен заменять grass)"
        )

        lmb = int(bool(held_keys['left mouse'] or held_keys['mouse1'] or held_keys['mouse left']))
        self.ui_input.text = (
            f"WASD: {int(held_keys['w'])}{int(held_keys['a'])}{int(held_keys['s'])}{int(held_keys['d'])}  "
            f"SPACE:{int(held_keys['space'])}  SHIFT:{int(held_keys['shift'])}  V:{int(held_keys['v'])}\n"
            f"LMB:{lmb}  locked:{mouse.locked}  last:{self._last_key}"
        )

    def on_crystal_collected(self, c: Crystal):
        if c in self.crystals:
            self.crystals.remove(c)
        destroy(c)
        self.ms.collected += 1
        self._check_missions()
        self._update_ui()

    def on_enemy_killed(self, e: Enemy):
        if e in self.enemies:
            self.enemies.remove(e)
        destroy(e)
        self.ms.killed += 1
        self._check_missions()
        self._update_ui()

    def _check_missions(self):
        if self.ms.collected >= self.ms.collect_goal and self.ms.killed >= self.ms.kill_goal:
            self.ms.exit_unlocked = True
            self.exit_gate.enabled = True
            self.exit_gate.visible = True

    def damage_player(self, dmg: int):
        self.player.health = max(0, int(self.player.health - dmg))
        self._update_ui()
        if self.player.health == 0:
            self.on_defeat()

    def _sync_active_weapon_to_slot(self):
        w = self.weapons[self.active_weapon_index]
        w['in_mag'] = int(self.ammo_in_mag)
        w['reserve'] = int(self.ammo_reserve)

    def _equip_weapon(self, index: int, animate: bool = True):
        if index < 0 or index >= len(self.weapons):
            return
        if hasattr(self, 'active_weapon_index') and index == self.active_weapon_index:
            return
        if hasattr(self, 'active_weapon_index'):
            self._sync_active_weapon_to_slot()
        self.active_weapon_index = index
        w = self.weapons[self.active_weapon_index]

        self.mag_size = int(w['mag'])
        self.ammo_in_mag = int(w['in_mag'])
        self.ammo_reserve = int(w['reserve'])
        self.reload_time = float(w['reload'])
        self.fire_rate = float(w['rate'])
        self.spread = float(w['spread'])

        self.weapon_model.texture = tex(str(w['texture']), 'white_cube')
        self.weapon_model.color = color.white
        self.weapon_model.shader = unlit_shader

        self.weapon_model.scale = w['vm_scale']
        self.weapon_model.rotation = w['vm_rot']
        self.weapon_model.position = w['vm_pos']

        self._weapon_base_pos = Vec3(self.weapon_model.x, self.weapon_model.y, self.weapon_model.z)
        self._weapon_base_rot = Vec3(self.weapon_model.rotation_x, self.weapon_model.rotation_y, self.weapon_model.rotation_z)
        self._weapon_kick = 0.0

        if animate:
            down = self.weapon_model.position + Vec3(0, -0.18, 0)
            self.weapon_model.position = down
            self.weapon_model.animate_position(self._weapon_base_pos, duration=0.12, curve=curve.out_quad)

    def on_defeat(self):
        mouse.locked = False
        ok = messagebox.askyesno("Поражение", "Ты проиграл. Начать заново?")
        if ok:
            self.reset()
        else:
            application.quit()

    def on_victory(self):
        mouse.locked = False
        messagebox.showinfo("Победа", "Ты выполнил миссии и добрался до выхода. Победа!")
        application.quit()

    def reset(self):
        for e in list(self.enemies):
            destroy(e)
        for c in list(self.crystals):
            destroy(c)
        for m in list(self.medkits):
            destroy(m)
        for a in list(self.ammoboxes):
            destroy(a)
        self.enemies = []
        self.crystals = []
        self.medkits = []
        self.ammoboxes = []
        self.ms = MissionState()
        self.exit_gate.enabled = False
        self.exit_gate.visible = False
        self.player.position = Vec3(0, 2, 0)
        self.player.health = self.player.max_health
        self.ammo_in_mag = self.mag_size
        self.ammo_reserve = 120
        self._reloading_until = 0.0
        self._build_level()
        self._update_ui()

    def try_reload(self):
        now = time.time()
        if now < self._reloading_until:
            return
        if self.ammo_in_mag >= self.mag_size:
            return
        if self.ammo_reserve <= 0:
            return
        self._reloading_until = now + self.reload_time

    def _finish_reload_if_ready(self):
        now = time.time()
        if self._reloading_until == 0.0:
            return
        if now < self._reloading_until:
            return
        need = self.mag_size - self.ammo_in_mag
        take = min(need, self.ammo_reserve)
        self.ammo_in_mag += take
        self.ammo_reserve -= take
        self._reloading_until = 0.0

    def try_shoot(self):
        now = time.time()
        w = self.weapons[self.active_weapon_index]
        if w['kind'] == 'melee':
            self._try_melee()
            return
        if now < self._reloading_until:
            return
        if now < self._cooldown_shot:
            return
        if self.ammo_in_mag <= 0:
            self.try_reload()
            return

        self._cooldown_shot = now + self.fire_rate
        self.ammo_in_mag -= 1

        self._weapon_kick = min(1.0, self._weapon_kick + 0.75)

        origin = self.player.camera_pivot.world_position
        base_dir = self.player.camera_pivot.forward
        pellets = int(w.get('pellets', 1))
        dmg = int(w.get('damage', 18))
        for _ in range(max(1, pellets)):
            direction = Vec3(
                base_dir.x + random.uniform(-self.spread, self.spread),
                base_dir.y + random.uniform(-self.spread, self.spread),
                base_dir.z + random.uniform(-self.spread, self.spread),
            )
            b = Bullet(self, origin + direction.normalized() * 0.9, direction)
            b.dmg = dmg

    def _try_melee(self):
        now = time.time()
        if now < self._cooldown_melee:
            return
        self._cooldown_melee = now + float(self.weapons[self.active_weapon_index]['rate'])
        self._weapon_kick = min(1.0, self._weapon_kick + 1.0)

        origin = self.player.camera_pivot.world_position
        direction = self.player.camera_pivot.forward
        hit = raycast(origin, direction, distance=2.1, ignore=(self.player,))
        if hit.hit and hasattr(hit.entity, 'take_damage'):
            try:
                hit.entity.take_damage(int(self.weapons[self.active_weapon_index]['damage']))
            except Exception:
                pass

    def save(self):
        data = {
            "player": {
                "x": float(self.player.x),
                "y": float(self.player.y),
                "z": float(self.player.z),
                "health": int(self.player.health),
            },
            "missions": self.ms.to_dict(),
        }
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_save_if_any(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            p = data.get("player", {})
            self.player.position = Vec3(float(p.get("x", 0)), float(p.get("y", 2)), float(p.get("z", 0)))
            self.player.health = int(p.get("health", 100))
            self.ms = MissionState.from_dict(data.get("missions", {}))
            self._check_missions()
        except Exception:
            return

    def update(self):
        mp = getattr(mouse, 'position', None)
        if mp is not None:
            self.custom_cursor.position = Vec3(float(mp[0]), float(mp[1]), self.custom_cursor.z)
        else:
            self.custom_cursor.position = Vec3(mouse.x, mouse.y, self.custom_cursor.z)
        if self.is_crashed:
            return
        if self.is_paused:
            self._update_ui()
            return
        self._finish_reload_if_ready()

        held_keys['w'] = 1 if (held_keys['w'] or held_keys['up arrow'] or held_keys['ц']) else 0
        held_keys['a'] = 1 if (held_keys['a'] or held_keys['left arrow'] or held_keys['ф']) else 0
        held_keys['s'] = 1 if (held_keys['s'] or held_keys['down arrow'] or held_keys['ы']) else 0
        held_keys['d'] = 1 if (held_keys['d'] or held_keys['right arrow'] or held_keys['в']) else 0

        self.player.speed = self.sprint_speed if self.sprint_toggle else self.base_speed

        if self._weapon_kick > 0:
            self._weapon_kick = max(0.0, self._weapon_kick - 6.0 * utime.dt)
        kick = self._weapon_kick
        self.weapon_model.position = self._weapon_base_pos + Vec3(0, 0, -0.10 * kick)
        self.weapon_model.rotation_x = self._weapon_base_rot.x - 9.0 * kick

        self.sky.rotation_y += 3 * utime.dt

        lmb = bool(held_keys['left mouse'] or held_keys['mouse1'] or held_keys['mouse left'])
        if lmb:
            if not mouse.locked:
                mouse.locked = True
            self.try_shoot()

        if self.player.y < -10:
            self.damage_player(999)

        self._update_ui()

    def _set_gameplay_enabled(self, enabled: bool) -> None:
        self.player.enabled = enabled
        self.weapon_model.enabled = enabled
        self.crosshair.enabled = enabled

        self.sky.enabled = enabled
        self.ground.enabled = enabled
        self.exit_gate.enabled = enabled if self.ms.exit_unlocked else False
        self.exit_gate.visible = enabled if self.ms.exit_unlocked else False

        for w in self.walls:
            w.enabled = enabled
        for e in self.enemies:
            e.enabled = enabled
        for c in self.crystals:
            c.enabled = enabled
        for m in self.medkits:
            m.enabled = enabled
        for a in self.ammoboxes:
            a.enabled = enabled

        if hasattr(self, 'boss') and self.boss is not None:
            try:
                self.boss.enabled = enabled
            except Exception:
                pass

        self.ui_hp.enabled = enabled
        self.ui_m.enabled = enabled
        self.ui_hint.enabled = enabled
        self.ui_weapon.enabled = enabled

    def _create_menu_ui(self) -> None:
        self.menu_root = Entity(parent=camera.ui, enabled=False)
        bg = Entity(parent=self.menu_root, model='quad', texture=tex('menu_bg.png', 'white_cube'), color=color.rgba(255, 255, 255, 220), scale=Vec3(1.8, 1.1, 1))
        bg.shader = unlit_shader

        Text(text='Ursina 3D Shooter', parent=self.menu_root, position=(0, 0.32), origin=(0, 0), scale=2.6, color=color.rgba(255, 255, 255, 240))
        Text(text='Start / Load / Shop', parent=self.menu_root, position=(0, 0.22), origin=(0, 0), scale=1.2, color=color.rgba(200, 210, 230, 220))

        def mk_btn(label: str, y: float, fn):
            b = Button(text=label, parent=self.menu_root, scale=(0.46, 0.08), position=(0, y), color=color.rgba(40, 50, 70, 220), highlight_color=color.rgba(70, 90, 130, 240), pressed_color=color.rgba(25, 30, 40, 240))
            b.on_click = fn
            return b

        b_start = mk_btn('START (new)', 0.06, self.start_new_game)
        b_start.color = color.rgba(40, 170, 120, 230)
        b_start.highlight_color = color.rgba(60, 210, 150, 240)

        self.btn_load = mk_btn('LOAD', -0.05, self.load_game)
        self.btn_load.color = color.rgba(40, 120, 200, 230)
        self.btn_load.highlight_color = color.rgba(80, 160, 240, 240)

        b_shop = mk_btn('SHOP', -0.16, self.open_shop)
        b_shop.color = color.rgba(170, 70, 220, 230)
        b_shop.highlight_color = color.rgba(200, 110, 255, 240)

        b_exit = mk_btn('EXIT', -0.27, application.quit)
        b_exit.color = color.rgba(210, 60, 80, 230)
        b_exit.highlight_color = color.rgba(240, 90, 110, 240)

    def _create_shop_ui(self) -> None:
        self.shop_root = Entity(parent=camera.ui, enabled=False)
        bg = Entity(parent=self.shop_root, model='quad', texture=tex('menu_bg.png', 'white_cube'), color=color.rgba(255, 255, 255, 220), scale=Vec3(1.8, 1.1, 1))
        bg.shader = unlit_shader
        Text(text='SHOP', parent=self.shop_root, position=(0, 0.32), origin=(0, 0), scale=2.6, color=color.rgba(255, 255, 255, 240))
        Text(text='Скоро будет магазин. Здесь появятся улучшения, скины и оружие.', parent=self.shop_root, position=(0, 0.18), origin=(0, 0), scale=1.05, color=color.rgba(210, 220, 240, 220))
        back = Button(text='BACK', parent=self.shop_root, scale=(0.46, 0.08), position=(0, -0.25), color=color.rgba(40, 50, 70, 220), highlight_color=color.rgba(70, 90, 130, 240), pressed_color=color.rgba(25, 30, 40, 240))
        back.color = color.rgba(40, 120, 200, 230)
        back.highlight_color = color.rgba(80, 160, 240, 240)
        back.on_click = self.show_menu

    def _create_splash_ui(self) -> None:
        self.splash_root = Entity(parent=camera.ui, enabled=False)
        bg = Entity(parent=self.splash_root, model='quad', texture=tex('menu_bg.png', 'white_cube'), color=color.rgba(255, 255, 255, 255), scale=Vec3(1.8, 1.1, 1))
        bg.shader = unlit_shader
        Text(text='Pashchenko SoftWare Corporation', parent=self.splash_root, position=(0, 0.05), origin=(0, 0), scale=2.0, color=color.rgba(255, 255, 255, 245))
        Text(text='presents', parent=self.splash_root, position=(0, -0.08), origin=(0, 0), scale=1.2, color=color.rgba(210, 220, 240, 230))
        Text(text='(press ENTER/SPACE)', parent=self.splash_root, position=(0, -0.32), origin=(0, 0), scale=0.9, color=color.rgba(210, 220, 240, 200))

    def show_splash(self) -> None:
        self.splash_active = True
        self.is_paused = True
        self.pause_text.enabled = False
        self.menu_open = False
        self.shop_open = False
        mouse.locked = False
        mouse.visible = False
        self.custom_cursor.enabled = False
        if self.menu_root is not None:
            self.menu_root.enabled = False
        if self.shop_root is not None:
            self.shop_root.enabled = False
        if self.splash_root is not None:
            self.splash_root.enabled = True
        self._set_gameplay_enabled(False)
        invoke(self._end_splash, delay=1.8)

    def _end_splash(self) -> None:
        if not self.splash_active:
            return
        self.splash_active = False
        if self.splash_root is not None:
            self.splash_root.enabled = False
        self.show_menu()

    def show_menu(self) -> None:
        if self.is_crashed:
            return
        self.menu_open = True
        self.shop_open = False
        self.is_paused = True
        self.pause_text.enabled = False
        mouse.locked = False
        mouse.visible = True
        self.custom_cursor.enabled = True
        if self.menu_root is not None:
            self.menu_root.enabled = True
        if self.shop_root is not None:
            self.shop_root.enabled = False
        if self.btn_load is not None:
            self.btn_load.enabled = os.path.exists(SAVE_PATH)
        self._set_gameplay_enabled(False)

    def hide_menu(self) -> None:
        self.menu_open = False
        self.shop_open = False
        self.is_paused = False
        if self.menu_root is not None:
            self.menu_root.enabled = False
        if self.shop_root is not None:
            self.shop_root.enabled = False
        self._set_gameplay_enabled(True)
        mouse.locked = True
        mouse.visible = False
        self.custom_cursor.enabled = False

    def open_shop(self) -> None:
        if self.is_crashed:
            return
        self.menu_open = False
        self.shop_open = True
        self.is_paused = True
        self.pause_text.enabled = False
        mouse.locked = False
        mouse.visible = True
        self.custom_cursor.enabled = True
        if self.menu_root is not None:
            self.menu_root.enabled = False
        if self.shop_root is not None:
            self.shop_root.enabled = True
        self._set_gameplay_enabled(False)

    def start_new_game(self) -> None:
        self.reset()
        self.hide_menu()

    def load_game(self) -> None:
        if not os.path.exists(SAVE_PATH):
            self.ui_hint.text = 'Нет сохранения.'
            return
        self.reset()
        self._load_save_if_any()
        self.hide_menu()

    def run(self):
        mouse.locked = True
        self.app.run()


def main():
    global _game
    _game = Game()
    _game.run()


_game = None


def update():
    if _game is not None:
        try:
            _game.update()
        except Exception as e:
            try:
                _game.on_crash(e)
            except Exception:
                application.quit()


def input(key):
    if _game is not None:
        try:
            _game.input(key)
        except Exception as e:
            try:
                _game.on_crash(e)
            except Exception:
                application.quit()


if __name__ == "__main__":
    main()
