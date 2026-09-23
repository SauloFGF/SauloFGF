"""Generate a small GitHub-inspired Shoot 'em Up GIF.

The generated GIF is the product of this project. Python and Pillow are only
needed when the animation needs to be regenerated.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - helpful message for new users
    raise SystemExit(
        "Pillow is required to generate the GIF. Install it with: "
        "python -m pip install Pillow"
    ) from exc


WIDTH = 800
HEIGHT = 240
FRAME_COUNT = 48
FRAME_DURATION_MS = 80
OUTPUT = Path(__file__).with_name("github-shootemup.gif")

BACKGROUND = (5, 9, 18)
GRID = (12, 25, 42)
WHITE = (220, 231, 239)
MUTED = (112, 133, 153)
CYAN = (86, 220, 255)
GREEN = (57, 211, 83)
YELLOW = (255, 211, 105)
PINK = (255, 111, 145)

CONTRIBUTION_COLORS = (
    (14, 68, 41),
    (0, 109, 50),
    (38, 166, 65),
    (57, 211, 83),
)


def load_font(size: int) -> ImageFont.ImageFont:
    """Use a small monospace font when one is available."""

    candidates = (
        "DejaVuSansMono.ttf",
        "LiberationMono-Regular.ttf",
        "C:/Windows/Fonts/consola.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_glow_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    width: int = 3,
) -> None:
    """Draw a bright line with a cheap two-pass neon glow."""

    rounded_points = [(round(x), round(y)) for x, y in points]
    draw.line(rounded_points, fill=color, width=width + 4)
    draw.line(rounded_points, fill=(255, 255, 255), width=max(1, width - 1))


def draw_background(draw: ImageDraw.ImageDraw, time: float) -> None:
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=BACKGROUND)

    # A subtle technical grid gives the scene a dashboard/arcade feel.
    for x in range(0, WIDTH + 1, 40):
        draw.line((x, 0, x, HEIGHT), fill=GRID, width=1)
    for y in range(0, HEIGHT + 1, 30):
        draw.line((0, y, WIDTH, y), fill=GRID, width=1)

    # A dim contribution graph in the background makes the GitHub theme
    # readable without making it look like a literal GitHub screenshot.
    graph_x = 650
    graph_y = 47
    pattern = (
        (0, 1, 2, 1, 0, 3),
        (1, 2, 3, 2, 1, 2),
        (0, 2, 3, 3, 2, 1),
        (1, 3, 2, 1, 3, 0),
    )
    for row, values in enumerate(pattern):
        for column, value in enumerate(values):
            x = graph_x + column * 13
            y = graph_y + row * 13
            color = CONTRIBUTION_COLORS[value]
            draw.rectangle((x, y, x + 8, y + 8), fill=color)

    draw.text((650, 105), "CONTRIBUTION STREAM", fill=(68, 91, 112), font=load_font(9))

    # Slow vertical streaks create continuous motion and make the loop seam
    # feel like a normal conveyor rather than a scene cut.
    for index in range(22):
        x = (index * 83 + 17) % WIDTH
        speed = 0.55 + (index % 5) * 0.12
        y = (index * 47 + time * HEIGHT * speed * 1.8) % HEIGHT
        brightness = 55 + (index % 4) * 22
        length = 2 + (index % 3) * 3
        draw.line((x, y, x, y + length), fill=(brightness // 2, brightness, brightness), width=1)


def enemy_position(enemy: dict[str, float], time: float) -> tuple[float, float]:
    progress = (time + enemy["phase"]) % 1.0
    x = enemy["x"] + math.sin((time + enemy["phase"]) * math.tau * 1.4) * enemy["sway"]
    y = -28 + progress * (HEIGHT + 70)
    return x, y


def draw_enemy(draw: ImageDraw.ImageDraw, enemy: dict[str, float], time: float) -> None:
    x, y = enemy_position(enemy, time)
    cell = enemy["cell"]
    color = CONTRIBUTION_COLORS[int(enemy["color"])]

    # Enemies are little contribution squares arranged like a pixel ship.
    for row in range(2):
        for column in range(2):
            left = x + column * cell
            top = y + row * cell
            draw.rectangle(
                (left, top, left + cell - 2, top + cell - 2),
                fill=color,
                outline=(80, 235, 120),
            )

    # A bright center makes the incoming wave readable against the grid.
    center = x + cell / 2 - 1
    draw.rectangle(
        (center - 2, y + cell / 2 - 2, center + 2, y + cell / 2 + 2),
        fill=GREEN if enemy["color"] < 3 else YELLOW,
    )

    if enemy["accent"]:
        draw.line((x + cell / 2, y - 4, x + cell / 2, y + 2 * cell + 4), fill=CYAN)


def draw_explosion(
    draw: ImageDraw.ImageDraw,
    enemy: dict[str, float],
    time: float,
) -> bool:
    """Draw a short, deterministic explosion. Return whether it is active."""

    distance = (time - enemy["hit"]) % 1.0
    if distance >= 0.105:
        return False

    x, y = enemy_position(enemy, enemy["hit"])
    progress = distance / 0.105
    radius = 5 + progress * 23
    color = YELLOW if progress < 0.55 else PINK
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        outline=color,
        width=2,
    )

    for particle in range(10):
        angle = particle * math.tau / 10 + enemy["phase"] * 2
        distance_from_center = radius * (0.75 + (particle % 3) * 0.12)
        px = x + math.cos(angle) * distance_from_center
        py = y + math.sin(angle) * distance_from_center
        size = 2 + (particle % 2)
        draw.rectangle((px, py, px + size, py + size), fill=color)

    if progress > 0.35:
        draw.line((x - 9, y - 9, x + 9, y + 9), fill=WHITE, width=1)
        draw.line((x + 9, y - 9, x - 9, y + 9), fill=WHITE, width=1)
    return True


def draw_ship(draw: ImageDraw.ImageDraw, time: float) -> tuple[float, float]:
    x = 220 + math.sin(time * math.tau) * 78
    y = HEIGHT - 31 + math.sin(time * math.tau * 2) * 3

    # Engine glow and exhaust.
    draw.polygon(
        ((x - 7, y + 8), (x, y + 28 + 4 * math.sin(time * math.tau * 4)), (x + 7, y + 8)),
        fill=(30, 120, 180),
    )
    draw.line((x, y + 9, x, y + 24), fill=CYAN, width=2)

    # Small triangular player ship.
    draw.polygon(
        ((x, y - 18), (x - 18, y + 11), (x - 9, y + 7), (x, y + 13), (x + 9, y + 7), (x + 18, y + 11)),
        fill=(28, 104, 144),
        outline=CYAN,
    )
    draw.polygon(((x, y - 12), (x - 8, y + 5), (x + 8, y + 5)), fill=(82, 180, 205))
    draw.line((x - 15, y + 9, x - 9, y + 1), fill=WHITE, width=1)
    draw.line((x + 15, y + 9, x + 9, y + 1), fill=WHITE, width=1)
    draw.rectangle((x - 3, y - 5, x + 3, y + 2), fill=GREEN)
    return x, y


def draw_bullets(draw: ImageDraw.ImageDraw, time: float, ship_x: float, ship_y: float) -> None:
    for index in range(5):
        phase = (index * 0.17 + 0.04) % 1.0
        age = (time + phase) % 1.0
        x = ship_x + (index - 2) * 9
        y = ship_y - 20 - age * 190
        if y < -8:
            continue
        draw_glow_line(draw, [(x, y), (x, y - 8)], CYAN, width=2)
        draw.ellipse((x - 2, y - 11, x + 2, y - 7), fill=WHITE)


def draw_hud(draw: ImageDraw.ImageDraw, time: float) -> None:
    draw.rectangle((0, 0, WIDTH, 31), fill=(4, 9, 17))
    draw.line((0, 31, WIDTH, 31), fill=(35, 78, 99), width=1)
    font = load_font(11)
    small_font = load_font(9)

    draw.text((16, 8), "GITHUB // COMMITS", fill=GREEN, font=font)
    draw.text((286, 8), "SCORE 012840", fill=WHITE, font=font)
    draw.text((440, 8), "LEVEL 07", fill=YELLOW, font=font)
    draw.text((570, 8), "COMMITS 1284", fill=WHITE, font=font)
    draw.text((16, HEIGHT - 17), "AUTO-FIRE", fill=CYAN, font=small_font)
    draw.text((WIDTH - 92, HEIGHT - 17), "LOOP  ∞", fill=MUTED, font=small_font)

    # Tiny moving activity indicator in the HUD.
    indicator_x = 708 + int(math.sin(time * math.tau * 2) * 5)
    draw.rectangle((indicator_x, 10, indicator_x + 8, 18), fill=GREEN)


def make_frame(time: float, stars: list[dict[str, float]], enemies: list[dict[str, float]]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw_background(draw, time)

    for star in stars:
        x = star["x"]
        speed = star["speed"]
        y = (star["y"] + time * HEIGHT * speed) % HEIGHT
        brightness = int(star["brightness"])
        size = int(star["size"])
        color = (brightness // 2, brightness, min(255, brightness + 20))
        draw.rectangle((x, y, x + size, y + size), fill=color)
        if star["streak"]:
            draw.line((x, y - 4, x, y), fill=(30, 90, 115), width=1)

    for enemy in enemies:
        if not draw_explosion(draw, enemy, time):
            draw_enemy(draw, enemy, time)

    ship_x, ship_y = draw_ship(draw, time)
    draw_bullets(draw, time, ship_x, ship_y)
    draw_hud(draw, time)
    return image


def build_scene() -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    randomizer = random.Random(1284)
    stars = [
        {
            "x": randomizer.randrange(0, WIDTH),
            "y": randomizer.uniform(-HEIGHT, HEIGHT),
            "speed": randomizer.uniform(0.08, 0.32),
            "brightness": randomizer.randrange(35, 125),
            "size": randomizer.choice((1, 1, 1, 2)),
            "streak": randomizer.random() < 0.18,
        }
        for _ in range(75)
    ]

    enemies: list[dict[str, float]] = []
    for row in range(3):
        for column in range(4):
            index = row * 4 + column
            enemies.append(
                {
                    "x": 36 + column * 145 + (row % 2) * 25,
                    "phase": (index * 0.11 + row * 0.07) % 1.0,
                    "cell": 7 if row == 0 else 8,
                    "color": (index + row) % 4,
                    "sway": 5 + (index % 3) * 4,
                    "accent": index % 5 == 0,
                    "hit": 0.18 + (index * 0.073) % 0.66,
                }
            )
    return stars, enemies


def generate() -> Path:
    stars, enemies = build_scene()
    frames = [make_frame(index / FRAME_COUNT, stars, enemies) for index in range(FRAME_COUNT)]

    # A shared, reduced palette keeps the GIF small and gives the arcade art
    # a deliberate limited-color look.
    palette_frames = [frame.quantize(colors=128) for frame in frames]
    palette_frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=palette_frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return OUTPUT


if __name__ == "__main__":
    output = generate()
    print(f"Generated {output.name} ({OUTPUT.stat().st_size:,} bytes)")
