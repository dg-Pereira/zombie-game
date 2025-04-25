import pygame
import sys
import math
import random

pygame.init()

# Screen setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Top-Down Shooter")

clock = pygame.time.Clock()

# Player setup
player_size = 40
player_x = WIDTH // 2
player_y = HEIGHT // 2
player_speed = 5

player_surface = pygame.Surface((player_size, player_size), pygame.SRCALPHA)
pygame.draw.polygon(
    player_surface,
    (0, 200, 0),
    [(player_size, player_size // 2), (0, 0), (0, player_size)]
)

# Bullet setup
bullets = []  # [x, y, dx, dy]
bullet_speed = 8
bullet_radius = 5
shoot_cooldown = 200
last_shot_time = pygame.time.get_ticks()

# Enemy setup
enemies = []  # [x, y, speed]
enemy_size = 30
enemy_speed = 2
spawn_cooldown = 1000  # ms
last_spawn_time = pygame.time.get_ticks()

def spawn_enemy():
    side = random.choice(['top', 'bottom', 'left', 'right'])
    if side == 'top':
        return [random.randint(0, WIDTH), 0, enemy_speed]
    elif side == 'bottom':
        return [random.randint(0, WIDTH), HEIGHT, enemy_speed]
    elif side == 'left':
        return [0, random.randint(0, HEIGHT), enemy_speed]
    else:  # right
        return [WIDTH, random.randint(0, HEIGHT), enemy_speed]

running = True
while running:
    dt = clock.tick(60)
    mouse_x, mouse_y = pygame.mouse.get_pos()
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]: player_y -= player_speed
    if keys[pygame.K_s]: player_y += player_speed
    if keys[pygame.K_a]: player_x -= player_speed
    if keys[pygame.K_d]: player_x += player_speed

    # Aim
    dx = mouse_x - player_x
    dy = mouse_y - player_y
    angle_rad = math.atan2(dy, dx)
    angle_deg = -math.degrees(angle_rad)

    rotated_surface = pygame.transform.rotate(player_surface, angle_deg)
    rotated_rect = rotated_surface.get_rect(center=(player_x, player_y))

    # Shoot bullets
    if pygame.mouse.get_pressed()[0]:
        if now - last_shot_time > shoot_cooldown:
            last_shot_time = now
            dir_x = math.cos(angle_rad)
            dir_y = math.sin(angle_rad)
            bullets.append([player_x, player_y, dir_x * bullet_speed, dir_y * bullet_speed])

    # Update bullets
    for bullet in bullets:
        bullet[0] += bullet[2]
        bullet[1] += bullet[3]
    bullets = [b for b in bullets if 0 <= b[0] <= WIDTH and 0 <= b[1] <= HEIGHT]

    # Spawn enemies
    if now - last_spawn_time > spawn_cooldown:
        last_spawn_time = now
        enemies.append(spawn_enemy())

    # Update enemies
    for enemy in enemies:
        dir_x = player_x - enemy[0]
        dir_y = player_y - enemy[1]
        length = math.hypot(dir_x, dir_y)
        if length != 0:
            dir_x /= length
            dir_y /= length
        enemy[0] += dir_x * enemy[2]
        enemy[1] += dir_y * enemy[2]

    # Collision detection: bullet vs enemy
    remaining_enemies = []
    for ex, ey, espeed in enemies:
        hit = False
        for bullet in bullets:
            bx, by = bullet[0], bullet[1]
            if math.hypot(bx - ex, by - ey) < enemy_size // 2 + bullet_radius:
                hit = True
                break
        if not hit:
            remaining_enemies.append([ex, ey, espeed])
    enemies = remaining_enemies

    # Draw
    screen.fill((30, 30, 30))
    screen.blit(rotated_surface, rotated_rect.topleft)

    for x, y, _, _ in bullets:
        pygame.draw.circle(screen, (255, 255, 0), (int(x), int(y)), bullet_radius)

    for x, y, _ in enemies:
        pygame.draw.circle(screen, (200, 0, 0), (int(x), int(y)), enemy_size // 2)

    pygame.display.flip()

pygame.quit()
sys.exit()
