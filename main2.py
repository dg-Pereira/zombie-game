import pygame
import sys
import math
import random
import time

pygame.init()
pygame.font.init()

# Screen setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zombie Survival Roguelike")

clock = pygame.time.Clock()
font = pygame.font.SysFont('Arial', 24)
small_font = pygame.font.SysFont('Arial', 18)

# Game states
MENU = 0
GAME = 1
GAME_OVER = 2
game_state = MENU

# Player setup
player_size = 40
player_x = WIDTH // 2
player_y = HEIGHT // 2
player_speed = 5
player_health = 100
player_max_health = 100
player_score = 0
player_kills = 0
player_level = 1
player_xp = 0
player_xp_to_level = 100
player_damage = 25

player_surface = pygame.Surface((player_size, player_size), pygame.SRCALPHA)
pygame.draw.polygon(
    player_surface,
    (0, 200, 0),
    [(player_size, player_size // 2), (0, 0), (0, player_size)]
)

# Weapon setup
weapons = {
    "pistol": {"damage": 25, "cooldown": 400, "bullet_speed": 8, "bullet_size": 5, "bullet_color": (255, 255, 0)},
    "shotgun": {"damage": 15, "cooldown": 800, "bullet_speed": 7, "bullet_size": 4, "bullet_color": (255, 200, 0),
                "spread": 5, "bullets": 5},
    "rifle": {"damage": 40, "cooldown": 200, "bullet_speed": 12, "bullet_size": 3, "bullet_color": (255, 100, 0)},
    "sniper": {"damage": 100, "cooldown": 1200, "bullet_speed": 20, "bullet_size": 7, "bullet_color": (200, 0, 200)}
}
current_weapon = "pistol"
ammo = {
    "pistol": 100,
    "shotgun": 20,
    "rifle": 60,
    "sniper": 10
}

# Bullet setup
bullets = []  # [x, y, dx, dy, damage, radius, color]
last_shot_time = pygame.time.get_ticks()

# Zombie setup
zombies = []  # [x, y, speed, health, type]
zombie_types = {
    "normal": {"size": 30, "speed": 2, "health": 50, "damage": 10, "color": (200, 0, 0), "xp": 10},
    "fast": {"size": 25, "speed": 3.5, "health": 30, "damage": 5, "color": (150, 0, 0), "xp": 15},
    "tank": {"size": 40, "speed": 1, "health": 150, "damage": 20, "color": (100, 0, 0), "xp": 25}
}
spawn_cooldown = 1000  # ms
last_spawn_time = pygame.time.get_ticks()
wave = 1
zombies_per_wave = 10
zombies_killed_in_wave = 0
wave_cleared = False
wave_start_time = 0
wave_break_duration = 5000  # 5 seconds between waves

# Add this near the top of your code with other initialization
# Load zombie sprites
zombie_frames = []
for i in range(1, 18):  # Assuming you have images 1-17
    try:
        # Load each frame - adjust path as needed
        frame = pygame.image.load(f"sprites/skeleton-move_{i}.png").convert_alpha()
        zombie_frames.append(frame)
    except:
        print(f"Failed to load zombie sprite {i}")

# Map setup
map_size = 2000
map_tiles = {}
tile_size = 200
visible_tiles = []

for x in range(0, map_size, tile_size):
    for y in range(0, map_size, tile_size):
        # Create random terrain (0=grass, 1=dirt, 2=sand)
        terrain_type = random.randint(0, 2)
        map_tiles[(x, y)] = {
            "type": terrain_type,
            "objects": []
        }

        # Add random objects (trees, rocks, etc)
        if random.random() < 0.3:
            obj_type = random.choice(["tree", "rock", "bush"])
            obj_x = x + random.randint(20, tile_size - 20)
            obj_y = y + random.randint(20, tile_size - 20)
            map_tiles[(x, y)]["objects"].append({"type": obj_type, "x": obj_x, "y": obj_y})

# Camera offset
camera_x = 0
camera_y = 0

# Powerups
powerups = []  # [x, y, type, duration]
powerup_types = {
    "health": {"color": (0, 255, 0), "size": 15, "effect": "heal", "value": 50},
    "speed": {"color": (0, 255, 255), "size": 15, "effect": "speed", "value": 2, "duration": 10000},
    "damage": {"color": (255, 0, 255), "size": 15, "effect": "damage", "value": 1.5, "duration": 15000},
    "ammo": {"color": (255, 255, 255), "size": 15, "effect": "ammo",
             "value": {"pistol": 50, "shotgun": 10, "rifle": 30, "sniper": 5}}
}
active_powerups = []  # [type, end_time, value]
last_powerup_time = pygame.time.get_ticks()
powerup_spawn_cooldown = 20000  # 20 seconds

# Blood splatter effects
blood_splatters = []  # [x, y, size, time]
blood_duration = 10000  # how long blood stays on ground

# Sounds
try:
    pygame.mixer.init()
    shoot_sound = pygame.mixer.Sound("sounds/guns/shoot.wav")
    hit_sound = pygame.mixer.Sound("sounds/zombies/zombie-hit-7.wav")
    #zombie_sound = pygame.mixer.Sound("sounds/zombies/zombie-hit-7.wav") unused
    powerup_sound = pygame.mixer.Sound("sounds/player/powerup.wav")
    hurt_sound = pygame.mixer.Sound("sounds/player/hurt.wav")
    sounds_loaded = True

except:
    sounds_loaded = False
    print(False)


# Helper functions
def world_to_screen(wx, wy):
    """Convert world coordinates to screen coordinates"""
    return wx - camera_x, wy - camera_y


def screen_to_world(sx, sy):
    """Convert screen coordinates to world coordinates"""
    return sx + camera_x, sy + camera_y


def spawn_zombie():
    """Spawn a zombie at the edge of the visible area"""
    # Determine zombie type based on wave difficulty
    weights = [0.8, 0.15, 0.05]  # normal, fast, tank
    if wave > 5:
        weights = [0.6, 0.3, 0.1]
    if wave > 10:
        weights = [0.4, 0.4, 0.2]
    if wave > 15:
        weights = [0.2, 0.5, 0.3]

    zombie_type = random.choices(["normal", "fast", "tank"], weights=weights)[0]

    # Spawn distance from player
    min_distance = 400
    max_distance = 600

    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(min_distance, max_distance)

    zombie_x = player_x + math.cos(angle) * distance
    zombie_y = player_y + math.sin(angle) * distance

    # Get zombie stats from type
    stats = zombie_types[zombie_type]

    # Scale health and damage based on wave
    health_scale = 1 + (wave * 0.1)
    damage_scale = 1 + (wave * 0.05)

    zombies.append([
        zombie_x,
        zombie_y,
        stats["speed"],
        stats["health"] * health_scale,
        zombie_type
    ])


def draw_health_bar(x, y, health, max_health, width=40, height=5):
    """Draw health bar at position"""
    ratio = health / max_health
    pygame.draw.rect(screen, (200, 0, 0), (x - width // 2, y - 20, width, height))
    pygame.draw.rect(screen, (0, 200, 0), (x - width // 2, y - 20, int(width * ratio), height))


def spawn_powerup():
    """Spawn a random powerup near the player"""
    powerup_type = random.choice(list(powerup_types.keys()))
    distance = random.uniform(100, 300)
    angle = random.uniform(0, 2 * math.pi)

    powerup_x = player_x + math.cos(angle) * distance
    powerup_y = player_y + math.sin(angle) * distance

    powerups.append([powerup_x, powerup_y, powerup_type, pygame.time.get_ticks()])


def draw_mini_map(size=150):
    """Draw a mini-map in the corner"""
    map_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    map_surface.fill((0, 0, 0, 150))

    # Draw player
    pygame.draw.circle(map_surface, (0, 255, 0), (size // 2, size // 2), 4)

    # Draw zombies
    map_scale = size / 1200  # Show 1200x1200 area on minimap

    for zx, zy, _, _, ztype in zombies:
        relative_x = (zx - player_x) * map_scale + size // 2
        relative_y = (zy - player_y) * map_scale + size // 2

        if 0 < relative_x < size and 0 < relative_y < size:
            pygame.draw.circle(map_surface, zombie_types[ztype]["color"], (int(relative_x), int(relative_y)), 2)

    # Draw powerups
    for px, py, ptype, _ in powerups:
        relative_x = (px - player_x) * map_scale + size // 2
        relative_y = (py - player_y) * map_scale + size // 2

        if 0 < relative_x < size and 0 < relative_y < size:
            pygame.draw.circle(map_surface, powerup_types[ptype]["color"], (int(relative_x), int(relative_y)), 2)

    screen.blit(map_surface, (WIDTH - size - 10, 10))
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH - size - 10, 10, size, size), 1)


def draw_info_panel():
    """Draw player stats and game info"""
    # Background panel
    panel = pygame.Surface((200, 95), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 150))
    screen.blit(panel, (10, 10))

    # Health
    health_text = f"Health: {int(player_health)}/{player_max_health}"
    health_surf = font.render(health_text, True, (255, 255, 255))
    screen.blit(health_surf, (20, 15))

    # Wave
    wave_text = f"Wave: {wave}"
    wave_surf = font.render(wave_text, True, (255, 255, 255))
    screen.blit(wave_surf, (20, 40))

    # Score
    score_text = f"Score: {player_score}"
    score_surf = font.render(score_text, True, (255, 255, 255))
    screen.blit(score_surf, (20, 65))

    # Weapon and ammo
    weapon_text = f"{current_weapon.capitalize()}: {ammo[current_weapon]}"
    weapon_surf = small_font.render(weapon_text, True, (255, 255, 255))
    screen.blit(weapon_surf, (WIDTH - 150, HEIGHT - 30))

    # Active powerups
    y_offset = 110
    for i, (ptype, end_time, _) in enumerate(active_powerups):
        time_left = max(0, (end_time - pygame.time.get_ticks()) / 1000)
        if time_left > 0:
            powerup_text = f"{ptype.capitalize()}: {time_left:.1f}s"
            powerup_surf = small_font.render(powerup_text, True, powerup_types[ptype]["color"])
            screen.blit(powerup_surf, (20, y_offset + i * 20))


def initialize_game():
    """Reset all game variables for a new game"""
    global player_x, player_y, player_health, player_max_health, player_score
    global player_kills, player_level, player_xp, player_xp_to_level, player_damage
    global zombies, bullets, powerups, active_powerups, wave, current_weapon
    global zombies_killed_in_wave, wave_cleared, wave_start_time, camera_x, camera_y
    global zombie_animation_speed, zombie_last_frame_time, zombie_current_frame

    # Add this to your main game variables
    zombie_animation_speed = 100  # ms per frame
    zombie_last_frame_time = pygame.time.get_ticks()
    zombie_current_frame = 0

    player_x = WIDTH // 2
    player_y = HEIGHT // 2
    player_health = 100
    player_max_health = 100
    player_score = 0
    player_kills = 0
    player_level = 1
    player_xp = 0
    player_xp_to_level = 100
    player_damage = 25

    zombies = []
    bullets = []
    powerups = []
    active_powerups = []
    blood_splatters = []
    wave = 1
    zombies_killed_in_wave = 0
    wave_cleared = False
    wave_start_time = pygame.time.get_ticks()

    camera_x = 0
    camera_y = 0

    current_weapon = "pistol"
    ammo = {
        "pistol": 100,
        "shotgun": 20,
        "rifle": 60,
        "sniper": 10
    }


# Add this function to your code
def get_zombie_frame():
    global zombie_current_frame, zombie_last_frame_time

    now = pygame.time.get_ticks()
    if now - zombie_last_frame_time > zombie_animation_speed:
        zombie_last_frame_time = now
        zombie_current_frame = (zombie_current_frame + 1) % len(zombie_frames)

    return zombie_frames[zombie_current_frame]

def process_level_up():
    """Handle player level up"""
    global player_level, player_xp, player_xp_to_level, player_max_health, player_damage

    player_level += 1
    player_xp -= player_xp_to_level
    player_xp_to_level = 100 * player_level

    # Improve player stats
    player_max_health += 10
    player_health = player_max_health  # Heal on levelup
    player_damage *= 1.1  # 10% damage increase


def handle_powerup_effects():
    """Process active powerups and their effects"""
    global active_powerups, player_speed

    now = pygame.time.get_ticks()
    remaining_powerups = []

    # Reset speed to default (will be re-applied if speed powerup is active)
    player_speed = 5

    for ptype, end_time, value in active_powerups:
        if now < end_time:
            # Apply continuous effects
            if ptype == "speed":
                player_speed = 5 * value
            remaining_powerups.append([ptype, end_time, value])

    active_powerups = remaining_powerups


running = True
while running:
    dt = clock.tick(60)
    now = pygame.time.get_ticks()

    # Process all events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Handle key presses
        if event.type == pygame.KEYDOWN:
            if game_state == MENU and event.key == pygame.K_SPACE:
                game_state = GAME
                initialize_game()
            elif game_state == GAME_OVER and event.key == pygame.K_SPACE:
                game_state = MENU

            # Weapon switching
            if game_state == GAME:
                if event.key == pygame.K_1:
                    current_weapon = "pistol"
                elif event.key == pygame.K_2:
                    current_weapon = "shotgun"
                elif event.key == pygame.K_3:
                    current_weapon = "rifle"
                elif event.key == pygame.K_4:
                    current_weapon = "sniper"

    # Menu state
    if game_state == MENU:
        screen.fill((30, 30, 30))

        title = font.render("ZOMBIE SURVIVAL ROGUELIKE", True, (255, 0, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 50))

        instructions = font.render("Press SPACE to start", True, (255, 255, 255))
        screen.blit(instructions, (WIDTH // 2 - instructions.get_width() // 2, HEIGHT // 2 + 50))

        controls = small_font.render("WASD: Move | Mouse: Aim | Click: Shoot | 1-4: Change Weapon", True,
                                     (200, 200, 200))
        screen.blit(controls, (WIDTH // 2 - controls.get_width() // 2, HEIGHT // 2 + 100))

    # Game Over state
    elif game_state == GAME_OVER:
        screen.fill((30, 0, 0))

        gameover_text = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(gameover_text, (WIDTH // 2 - gameover_text.get_width() // 2, HEIGHT // 2 - 50))

        score_text = font.render(f"Score: {player_score}", True, (255, 255, 255))
        screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2))

        wave_text = font.render(f"Survived to Wave: {wave}", True, (255, 255, 255))
        screen.blit(wave_text, (WIDTH // 2 - wave_text.get_width() // 2, HEIGHT // 2 + 30))

        restart_text = font.render("Press SPACE to return to menu", True, (255, 255, 255))
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 80))

    # Main Game state
    elif game_state == GAME:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse_x, world_mouse_y = screen_to_world(mouse_x, mouse_y)

        # Apply powerup effects
        handle_powerup_effects()

        # Handle wave mechanics
        if wave_cleared:
            # Break between waves
            if now - wave_start_time > wave_break_duration:
                wave += 1
                zombies_per_wave = 10 + (wave * 3)
                wave_cleared = False
                zombies_killed_in_wave = 0
                spawn_powerup()  # Spawn powerup at start of new wave
        else:
            # Check if wave is cleared
            if zombies_killed_in_wave >= zombies_per_wave and len(zombies) == 0:
                wave_cleared = True
                wave_start_time = now
                player_score += wave * 100  # Bonus for clearing wave

        # Movement with boundary checking
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]: player_y -= player_speed
        if keys[pygame.K_s]: player_y += player_speed
        if keys[pygame.K_a]: player_x -= player_speed
        if keys[pygame.K_d]: player_x += player_speed

        # Calculate camera position (center on player)
        camera_x = player_x - WIDTH // 2
        camera_y = player_y - HEIGHT // 2

        # Aim
        dx = world_mouse_x - player_x
        dy = world_mouse_y - player_y
        angle_rad = math.atan2(dy, dx)
        angle_deg = -math.degrees(angle_rad)

        rotated_surface = pygame.transform.rotate(player_surface, angle_deg)
        player_screen_x, player_screen_y = world_to_screen(player_x, player_y)
        rotated_rect = rotated_surface.get_rect(center=(player_screen_x, player_screen_y))

        # Shoot bullets
        weapon = weapons[current_weapon]
        if pygame.mouse.get_pressed()[0]:
            if now - last_shot_time > weapon["cooldown"] and ammo[current_weapon] > 0:
                last_shot_time = now
                ammo[current_weapon] -= 1

                # Handle different weapon types
                if current_weapon == "shotgun":
                    # Shotgun shoots multiple bullets in a spread
                    for _ in range(weapon["bullets"]):
                        spread_angle = angle_rad + random.uniform(-0.15, 0.15)
                        dir_x = math.cos(spread_angle)
                        dir_y = math.sin(spread_angle)
                        bullets.append([
                            player_x, player_y,
                            dir_x * weapon["bullet_speed"],
                            dir_y * weapon["bullet_speed"],
                            weapon["damage"] * player_damage / 100,
                            weapon["bullet_size"],
                            weapon["bullet_color"]
                        ])
                else:
                    # Regular single bullet weapons
                    dir_x = math.cos(angle_rad)
                    dir_y = math.sin(angle_rad)
                    bullets.append([
                        player_x, player_y,
                        dir_x * weapon["bullet_speed"],
                        dir_y * weapon["bullet_speed"],
                        weapon["damage"] * player_damage / 100,
                        weapon["bullet_size"],
                        weapon["bullet_color"]
                    ])

                if sounds_loaded:
                    shoot_sound.play()

        # Update bullets
        for bullet in bullets:
            bullet[0] += bullet[2]  # x += dx
            bullet[1] += bullet[3]  # y += dy

        # Remove bullets that are too far from player
        bullets = [b for b in bullets if math.hypot(b[0] - player_x, b[1] - player_y) < 1000]

        # Spawn zombies if wave is active and we're below the spawn limit
        if not wave_cleared and len(zombies) < max(5, wave * 2) and zombies_killed_in_wave < zombies_per_wave:
            if now - last_spawn_time > max(200, spawn_cooldown - wave * 50):  # Speed up spawning in later waves
                last_spawn_time = now
                spawn_zombie()

        # Update zombies
        for zombie in zombies:
            # Move towards player
            dir_x = player_x - zombie[0]
            dir_y = player_y - zombie[1]
            length = math.hypot(dir_x, dir_y)
            if length != 0:
                dir_x /= length
                dir_y /= length

            zombie[0] += dir_x * zombie[2]
            zombie[1] += dir_y * zombie[2]

            # Check collision with player
            if math.hypot(player_x - zombie[0], player_y - zombie[1]) < (
                    player_size / 2 + zombie_types[zombie[4]]["size"] / 2):
                player_health -= zombie_types[zombie[4]]["damage"] / 10  # Damage per frame
                if sounds_loaded and random.random() < 0.1:  # Don't play sound every frame
                    hurt_sound.play()

        # Spawn powerups occasionally
        if now - last_powerup_time > powerup_spawn_cooldown:
            last_powerup_time = now
            spawn_powerup()

        # Collision detection: bullet vs zombie
        remaining_zombies = []
        for zx, zy, zspeed, zhealth, ztype in zombies:
            z_hit = False
            z_size = zombie_types[ztype]["size"]

            # Check each bullet
            remaining_bullets = []
            for bullet in bullets:
                bx, by, _, _, damage, bradius, _ = bullet

                # Calculate distance between bullet and zombie
                distance = math.hypot(bx - zx, by - zy)

                if distance < z_size / 2 + bradius:
                    zhealth -= damage
                    z_hit = True

                    # Create blood splatter
                    blood_splatters.append([bx, by, random.randint(5, 15), now])

                    if sounds_loaded:
                        hit_sound.play()
                else:
                    remaining_bullets.append(bullet)

            bullets = remaining_bullets

            # If zombie still alive, keep it
            if zhealth > 0:
                remaining_zombies.append([zx, zy, zspeed, zhealth, ztype])
            else:
                # Zombie killed - award score and XP
                player_score += zombie_types[ztype]["xp"] * wave
                player_xp += zombie_types[ztype]["xp"]
                zombies_killed_in_wave += 1
                player_kills += 1

                # Create death blood splatter
                for _ in range(5):
                    offset_x = random.randint(-20, 20)
                    offset_y = random.randint(-20, 20)
                    blood_splatters.append([zx + offset_x, zy + offset_y, random.randint(10, 25), now])

                # Small chance to drop powerup on death
                if random.random() < 0.1:
                    powerups.append([zx, zy, random.choice(list(powerup_types.keys())), now])

        zombies = remaining_zombies

        # Check for level up
        if player_xp >= player_xp_to_level:
            process_level_up()

        # Check powerup collisions
        remaining_powerups = []
        for px, py, ptype, ptime in powerups:
            if math.hypot(player_x - px, player_y - py) < player_size / 2 + powerup_types[ptype]["size"]:
                # Apply powerup effect
                if ptype == "health":
                    player_health = min(player_max_health, player_health + powerup_types[ptype]["value"])
                elif ptype == "ammo":
                    for weapon, amount in powerup_types[ptype]["value"].items():
                        ammo[weapon] += amount
                else:
                    # Timed powerups
                    duration = powerup_types[ptype]["duration"]
                    value = powerup_types[ptype]["value"]
                    active_powerups.append([ptype, now + duration, value])

                if sounds_loaded:
                    powerup_sound.play()
            else:
                # Keep powerups that last less than 30 seconds
                if now - ptime < 30000:
                    remaining_powerups.append([px, py, ptype, ptime])

        powerups = remaining_powerups

        # Remove old blood splatters
        blood_splatters = [b for b in blood_splatters if now - b[3] < blood_duration]

        # Check game over condition
        if player_health <= 0:
            game_state = GAME_OVER

        # Draw everything
        screen.fill((30, 30, 30))

        # Draw world tiles visible on screen
        for x in range(0, map_size, tile_size):
            for y in range(0, map_size, tile_size):
                # Check if tile is visible on screen
                tx, ty = world_to_screen(x, y)
                if -tile_size <= tx <= WIDTH and -tile_size <= ty <= HEIGHT:
                    tile_info = map_tiles.get((x, y), {"type": 0, "objects": []})

                    # Draw terrain
                    if tile_info["type"] == 0:  # Grass
                        color = (50, 100, 50)
                    elif tile_info["type"] == 1:  # Dirt
                        color = (100, 80, 50)
                    else:  # Sand
                        color = (200, 180, 140)

                    pygame.draw.rect(screen, color, (tx, ty, tile_size, tile_size))

                    # Draw objects in tile
                    for obj in tile_info["objects"]:
                        obj_x, obj_y = world_to_screen(obj["x"], obj["y"])

                        if obj["type"] == "tree":
                            pygame.draw.circle(screen, (30, 80, 30), (int(obj_x), int(obj_y)), 20)
                            pygame.draw.rect(screen, (80, 50, 20), (int(obj_x) - 5, int(obj_y) + 10, 10, 20))
                        elif obj["type"] == "rock":
                            pygame.draw.circle(screen, (100, 100, 100), (int(obj_x), int(obj_y)), 15)
                        elif obj["type"] == "bush":
                            pygame.draw.circle(screen, (50, 100, 50), (int(obj_x), int(obj_y)), 10)

        # Draw blood splatters
        for bx, by, bsize, btime in blood_splatters:
            # Fade out over time
            alpha = 255 * (1 - (now - btime) / blood_duration)

            screen_x, screen_y = world_to_screen(bx, by)

            # Draw blood splatter
            blood_surf = pygame.Surface((bsize * 2, bsize * 2), pygame.SRCALPHA)
            pygame.draw.circle(blood_surf, (200, 0, 0, int(alpha)), (bsize, bsize), bsize)
            screen.blit(blood_surf, (int(screen_x - bsize), int(screen_y - bsize)))

        # Draw bullets
        for x, y, _, _, _, radius, color in bullets:
            screen_x, screen_y = world_to_screen(x, y)
            pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), radius)

        # Draw player
        screen.blit(rotated_surface, rotated_rect.topleft)

        # Replace the zombie drawing code in your main game loop
        # Find the section where zombies are drawn and replace with:
        for x, y, _, health, ztype in zombies:
            screen_x, screen_y = world_to_screen(x, y)
            z_size = zombie_types[ztype]["size"]

            # Get direction to player for sprite facing
            dx = player_x - x
            dy = player_y - y
            angle_rad = math.atan2(dy, dx)
            angle_deg = -math.degrees(angle_rad)

            # Get current animation frame
            zombie_frame = get_zombie_frame()

            # Scale sprite to match zombie size
            scaled_frame = pygame.transform.scale(zombie_frame, (z_size, z_size))

            # Rotate sprite to face player
            rotated_frame = pygame.transform.rotate(scaled_frame, angle_deg)

            # Position sprite
            frame_rect = rotated_frame.get_rect(center=(screen_x, screen_y))

            # Draw zombie sprite
            screen.blit(rotated_frame, frame_rect.topleft)

            # Draw health bar above zombie
            draw_health_bar(screen_x, screen_y, health, zombie_types[ztype]["health"], width=z_size)

        # Draw powerups
        for x, y, ptype, _ in powerups:
            screen_x, screen_y = world_to_screen(x, y)
            info = powerup_types[ptype]

            # Make powerups pulse to draw attention
            size_mod = math.sin(now / 200) * 2
            size = info["size"] + size_mod

            # Draw powerup
            pygame.draw.circle(screen, info["color"], (int(screen_x), int(screen_y)), int(size))

            # Inner highlight
            pygame.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), int(size) // 2)

        # Draw UI elements
        draw_info_panel()
        draw_mini_map()

        # Draw wave information
        if wave_cleared:
            time_to_next = max(0, (wave_break_duration - (now - wave_start_time)) / 1000)
            wave_text = f"Wave {wave} cleared! Next wave in {time_to_next:.1f}s"
            wave_surf = font.render(wave_text, True, (255, 255, 255))
            screen.blit(wave_surf, (WIDTH // 2 - wave_surf.get_width() // 2, 50))
        else:
            progress = zombies_killed_in_wave / zombies_per_wave * 100
            wave_text = f"Wave {wave}: {progress:.1f}% ({zombies_killed_in_wave}/{zombies_per_wave})"
            wave_surf = font.render(wave_text, True, (255, 255, 255))
            screen.blit(wave_surf, (WIDTH // 2 - wave_surf.get_width() // 2, 50))

        # XP bar
        xp_ratio = player_xp / player_xp_to_level
        pygame.draw.rect(screen, (50, 50, 100), (10, HEIGHT - 20, 200, 10))
        pygame.draw.rect(screen, (100, 100, 255), (10, HEIGHT - 20, int(200 * xp_ratio), 10))
        xp_text = f"Level {player_level} - XP: {player_xp}/{player_xp_to_level}"
        xp_surf = small_font.render(xp_text, True, (255, 255, 255))
        screen.blit(xp_surf, (220, HEIGHT - 20))

        # Wave progress bar
        if not wave_cleared:
            progress_ratio = zombies_killed_in_wave / zombies_per_wave
            pygame.draw.rect(screen, (100, 50, 50), (WIDTH // 2 - 100, 30, 200, 5))
            pygame.draw.rect(screen, (200, 100, 100), (WIDTH // 2 - 100, 30, int(200 * progress_ratio), 5))

        # Add weapon selector UI
        weapon_panel = pygame.Surface((400, 30), pygame.SRCALPHA)
        weapon_panel.fill((0, 0, 0, 150))
        screen.blit(weapon_panel, (WIDTH // 2 - 200, HEIGHT - 40))

        weapons_list = ["pistol", "shotgun", "rifle", "sniper"]
        for i, weapon in enumerate(weapons_list):
            # Highlight current weapon
            bg_color = (100, 100, 100, 150) if weapon == current_weapon else (50, 50, 50, 150)
            weapon_bg = pygame.Surface((95, 25), pygame.SRCALPHA)
            weapon_bg.fill(bg_color)
            screen.blit(weapon_bg, (WIDTH // 2 - 190 + i * 100, HEIGHT - 37))

            # Display weapon name and ammo
            weapon_text = f"{weapon.capitalize()}: {ammo[weapon]}"
            weapon_color = (255, 255, 255) if ammo[weapon] > 0 else (255, 100, 100)
            weapon_surf = small_font.render(weapon_text, True, weapon_color)
            screen.blit(weapon_surf, (WIDTH // 2 - 180 + i * 100, HEIGHT - 35))

            # Key hint
            key_surf = small_font.render(f"[{i + 1}]", True, (200, 200, 200))
            screen.blit(key_surf, (WIDTH // 2 - 190 + i * 100, HEIGHT - 35))

    pygame.display.flip()

pygame.quit()
sys.exit()