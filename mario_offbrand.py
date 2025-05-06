import os
import math
import pygame
from os import listdir
from os.path import isfile, join

pygame.init()
pygame.font.init() # Initialize font module

pygame.display.set_caption("Mario Offbrand")

WIDTH, HEIGHT = 1000, 800
FPS = 60
PLAYER_VEL = 5
BLOCK_SIZE = 96 # Make block size a global constant

window = pygame.display.set_mode((WIDTH, HEIGHT))
FONT = pygame.font.SysFont("comicsans", 30) # Font for UI

# Game States
PLAYING = "playing"
LEVEL_TRANSITION = "transition"
GAME_OVER = "game_over"
GAME_WON = "game_won"

# --- Asset Loading Functions ---

def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]

def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    if not os.path.exists(path):
        print(f"Warning: Path not found {path}")
        return {} # Return empty if path doesn't exist
    try:
        images = [f for f in listdir(path) if isfile(join(path, f)) and f.lower().endswith(".png")]
    except FileNotFoundError:
        print(f"Error: Directory not found: {path}")
        return {}


    all_sprites = {}

    for image in images:
        try:
            sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

            sprites = []
            sheet_width = sprite_sheet.get_width()
            sheet_height = sprite_sheet.get_height() # Added for potential vertical spritesheets

            # Assuming sprites are arranged horizontally for now
            for i in range(sheet_width // width):
                surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
                rect = pygame.Rect(i * width, 0, width, height)
                surface.blit(sprite_sheet, (0, 0), rect)
                sprites.append(pygame.transform.scale2x(surface)) # Scale up 2x

            sprite_name = image.replace(".png", "")
            if direction:
                all_sprites[sprite_name + "_right"] = sprites
                all_sprites[sprite_name + "_left"] = flip(sprites)
            else:
                all_sprites[sprite_name] = sprites
        except pygame.error as e:
            print(f"Error loading image {join(path, image)}: {e}")
        except Exception as e:
             print(f"An unexpected error occurred loading {join(path, image)}: {e}")


    return all_sprites

# Function to load a single scaled image
def load_scaled_image(path, scale_factor=2):
    try:
        image = pygame.image.load(path).convert_alpha()
        size = image.get_size()
        scaled_size = (size[0] * scale_factor, size[1] * scale_factor)
        return pygame.transform.scale(image, scaled_size)
    except pygame.error as e:
        print(f"Error loading or scaling image {path}: {e}")
        # Return a placeholder surface if loading fails
        placeholder = pygame.Surface((32 * scale_factor, 32 * scale_factor), pygame.SRCALPHA)
        placeholder.fill((255, 0, 255)) # Bright pink to indicate missing asset
        return placeholder
    except Exception as e:
        print(f"An unexpected error occurred loading {path}: {e}")
        placeholder = pygame.Surface((32 * scale_factor, 32 * scale_factor), pygame.SRCALPHA)
        placeholder.fill((255, 0, 255))
        return placeholder


def get_block(size):
    path = join("assets", "Terrain", "Terrain.png")
    try:
        image = pygame.image.load(path).convert_alpha()
        # Use a different block appearance (e.g., the one at 96, 64 in the spritesheet)
        surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
        # Coordinates might need adjustment based on the actual Terrain.png layout
        # rect = pygame.Rect(96, 0, size, size) # Original brown block
        rect = pygame.Rect(192, 0, size, size) # Example: Trying a different terrain piece if available
        surface.blit(image, (0, 0), rect)
        return pygame.transform.scale2x(surface)
    except pygame.error as e:
        print(f"Error loading block from {path}: {e}")
        surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        surface.fill((100, 100, 100)) # Grey placeholder
        return surface
    except IndexError:
         print(f"Error: Rect coordinates out of bounds for {path}. Using default block.")
         surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
         surface.fill((100, 100, 100))
         return surface


# --- Game Object Classes ---

class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    SPRITES = load_sprite_sheets("MainCharacters", "NinjaFrog", 32, 32, True)
    ANIMATION_DELAY = 3
    MAX_HEALTH = 3
    INVINCIBILITY_DURATION = 1.5 # Seconds of invincibility after hit

    def __init__(self, x, y, width, height):
        super().__init__()
        self.starting_pos = (x, y) # Store starting position for reset
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "right" # Start facing right
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0

        self.max_health = self.MAX_HEALTH
        self.current_health = self.max_health
        self.is_invincible = False
        self.invincibility_timer = 0

    def reset(self):
        """Resets player to starting state for the level."""
        self.rect.topleft = self.starting_pos
        self.x_vel = 0
        self.y_vel = 0
        self.direction = "right"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.current_health = self.max_health
        self.is_invincible = False
        self.invincibility_timer = 0
        self.update_sprite() # Ensure correct sprite is set initially

    def jump(self):
        # Allow jump only if on ground or haven't double jumped
        if self.jump_count < 2:
            self.y_vel = -self.GRAVITY * 8 # Consistent jump height
            self.animation_count = 0
            self.jump_count += 1
            if self.jump_count == 1:
                self.fall_count = 0 # Reset fall count on first jump

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def take_damage(self, amount=1):
        """Reduces health if not invincible."""
        if not self.is_invincible:
            self.current_health -= amount
            self.hit = True # Trigger hit animation
            self.hit_count = 0
            self.is_invincible = True
            self.invincibility_timer = 0 # Reset invincibility timer
            # print(f"Player took damage! Health: {self.current_health}") # Debugging

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def loop(self, fps):
        # --- Handle Invincibility ---
        if self.is_invincible:
            self.invincibility_timer += 1 / fps
            if self.invincibility_timer >= self.INVINCIBILITY_DURATION:
                self.is_invincible = False
                self.invincibility_timer = 0
                # Also ensure hit animation stops if invincibility ends
                if self.hit and self.hit_count == 0: # Only stop if not already in hit animation cycle
                     self.hit = False


        # --- Handle Gravity ---
        # Apply gravity based on fall_count for terminal velocity effect
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)

        # --- Handle Hit Animation ---
        # This part seems redundant now that invincibility handles the state
        # Let's keep it simple: hit animation plays once when take_damage is called
        if self.hit:
           self.hit_count += 1
           # Make hit animation last ~0.5 seconds regardless of invincibility?
           if self.hit_count > fps * 0.5:
                self.hit = False
                self.hit_count = 0


        self.fall_count += 1
        self.update_sprite()

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        # self.count = 0 # 'count' was not defined, maybe meant fall_count or animation_count?
        self.fall_count = 0 # Reset fall count to prevent instant acceleration down
        self.y_vel *= -0.5 # Bounce off slightly, reduced intensity

    def update_sprite(self):
        # Determine sprite sheet based on state
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
            elif self.jump_count >= 2: # Use double_jump for second jump and beyond
                sprite_sheet = "double_jump"
        elif self.y_vel > self.GRAVITY * 1.5: # Lower threshold for fall animation
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        # Get the correct list of sprites
        sprite_sheet_name = sprite_sheet + "_" + self.direction
        if not self.SPRITES or sprite_sheet_name not in self.SPRITES:
             # print(f"Warning: Sprite key '{sprite_sheet_name}' not found. Defaulting to idle_right.")
             # Fallback if sprites didn't load or key is missing
             sprite_sheet_name = "idle_right"
             if sprite_sheet_name not in self.SPRITES: # Absolute fallback
                 self.sprite = pygame.Surface((self.rect.width, self.rect.height))
                 self.sprite.fill(self.COLOR)
                 self.update()
                 return


        sprites = self.SPRITES[sprite_sheet_name]
        if not sprites: # Check if the list of sprites is empty
            # print(f"Warning: Sprite list for '{sprite_sheet_name}' is empty.")
            self.sprite = pygame.Surface((self.rect.width, self.rect.height))
            self.sprite.fill(self.COLOR)
            self.update()
            return

        # Select the current sprite index based on animation count
        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1

        # Update rect and mask
        self.update()


    def update(self):
        # Adjust rect size based on the current sprite, keep position consistent (topleft)
        current_pos = self.rect.topleft
        self.rect = self.sprite.get_rect(topleft=current_pos)
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        # Optionally add visual feedback for invincibility (e.g., flashing)
        if not hasattr(self, 'sprite') or not self.sprite:
            # If sprite doesn't exist (shouldn't happen with proper init/update, but defensive)
            # Draw a placeholder rectangle instead of crashing
            placeholder_rect = self.rect.move(-offset_x, 0) # Adjust for scroll
            pygame.draw.rect(win, self.COLOR, placeholder_rect)
            # print("Warning: Player sprite missing, drawing placeholder.") # Optional debug
            return # Stop here to avoid blitting non-existent sprite
        if self.is_invincible:
            # Flash every few frames
            if pygame.time.get_ticks() % 200 < 100: # Adjust timing for desired flash speed
                 return # Skip drawing this frame to create a flash effect
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))

        # Draw Health Hearts (simple version)
        heart_img = load_scaled_image(join("assets", "Items", "Fruits", "Kiwi.png"), 1) # Example using Kiwi as heart
        if heart_img:
            heart_size = heart_img.get_width()
            for i in range(self.current_health):
                 win.blit(heart_img, (10 + i * (heart_size + 5), 10))


class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        # Ensure image is created *before* setting mask
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name
        # Set mask after image is potentially modified by subclasses
        # self.mask = pygame.mask.from_surface(self.image) # Moved to subclasses

    def draw(self, win, offset_x):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))

    # Add a dummy loop method for compatibility if needed by main loop iteration
    def loop(self, *args):
        pass


class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size * 2, size * 2) # Size is doubled due to scale2x in get_block
        block_surface = get_block(size) # get_block now returns a 2x scaled surface
        self.image.blit(block_surface, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width * 2, height * 2, "fire") # Adjust size for scaling
        # Load spritesheets expects original dimensions
        self.fire_sprites = load_sprite_sheets("Traps", "Fire", width, height)
        self.animation_count = 0
        self.animation_name = "off" # Start off by default
        # Set initial image and mask
        if "off" in self.fire_sprites and self.fire_sprites["off"]:
            self.image = self.fire_sprites["off"][0]
        else:
             # Fallback if sprites missing
             self.image.fill((255,100,0, 150)) # Orange placeholder
        self.mask = pygame.mask.from_surface(self.image)


    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    def loop(self, *args): # Accept optional arguments like fps
        if not self.fire_sprites or self.animation_name not in self.fire_sprites:
            return # Cannot animate if sprites are missing

        sprites = self.fire_sprites[self.animation_name]
        if not sprites: return # Skip if specific animation list is empty

        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        # Update rect and mask (important if animation size changes, though unlikely here)
        current_pos = self.rect.topleft
        self.rect = self.image.get_rect(topleft=current_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Reset animation loop (optional, prevents huge numbers) - corrected logic
        # if self.animation_count >= len(sprites) * self.ANIMATION_DELAY:
        #      self.animation_count = 0 # Reset smoothly


# --- New Trap: Spikes ---
class Spike(Object):
    def __init__(self, x, y, width=16, height=16): # Default size based on typical spike assets
        # Assuming spikes point up, adjust position slightly if needed
        # The loaded image will be scaled 2x
        img_path = join("assets", "Traps", "Spikes", "Idle.png") # Use the static spike image
        self.spike_img = load_scaled_image(img_path)
        scaled_width = self.spike_img.get_width()
        scaled_height = self.spike_img.get_height()
        # Adjust y position so the base aligns with where it should be placed
        adjusted_y = y + BLOCK_SIZE - scaled_height # Place it relative to block grid bottom

        super().__init__(x, adjusted_y, scaled_width, scaled_height, "spike")
        self.image.blit(self.spike_img, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)

# --- Goal Object ---
class Goal(Object):
    def __init__(self, x, y, width=32, height=32): # Adjust size as needed
         # Use a checkpoint or specific goal asset
         img_path = join("assets", "Items", "Checkpoints", "End", "End (Idle).png")
         self.goal_img = load_scaled_image(img_path)
         scaled_width = self.goal_img.get_width()
         scaled_height = self.goal_img.get_height()
         # Adjust y position to align nicely
         adjusted_y = y + BLOCK_SIZE - scaled_height

         super().__init__(x, adjusted_y, scaled_width, scaled_height, "goal")
         self.image.blit(self.goal_img, (0,0))
         self.mask = pygame.mask.from_surface(self.image)


# --- Background Handling ---
def get_background(name):
    try:
        path = join("assets", "Background", name)
        image = pygame.image.load(path).convert() # Use convert for performance
        _, _, width, height = image.get_rect()

        if width == 0 or height == 0:
             print(f"Warning: Background image {name} has zero dimension.")
             return [], pygame.Surface((WIDTH, HEIGHT)) # Return empty list and blank surface

        tiles = []
        # Ensure we cover the screen even if dimensions are small
        for i in range(math.ceil(WIDTH / width)): # Use ceil to ensure coverage
            for j in range(math.ceil(HEIGHT / height)):
                pos = (i * width, j * height)
                tiles.append(pos)

        return tiles, image
    except pygame.error as e:
        print(f"Error loading background {name}: {e}")
        # Return a plain color background as fallback
        fallback_surface = pygame.Surface((WIDTH, HEIGHT))
        fallback_surface.fill((100, 100, 200)) # Blueish fallback
        return [(0, 0)], fallback_surface # Single tile covering screen
    except Exception as e:
         print(f"An unexpected error occurred loading background {name}: {e}")
         fallback_surface = pygame.Surface((WIDTH, HEIGHT))
         fallback_surface.fill((100, 100, 200))
         return [(0, 0)], fallback_surface


# --- Drawing Function ---
def draw_text(window, text, font, color, x, y):
    text_surface = font.render(text, True, color)
    window.blit(text_surface, (x, y))

def draw(window, background, bg_image, player, objects, offset_x, current_level, game_state):
    # Draw background
    for tile in background:
        window.blit(bg_image, tile)

    # Draw all objects
    for obj in objects:
        obj.draw(window, offset_x)

    # Draw player (handles its own health display now)
    player.draw(window, offset_x)

    # Draw Level Number
    draw_text(window, f"Level: {current_level + 1}", FONT, (255, 255, 255), 10, 50) # Below health

    # --- Draw Game State Messages ---
    if game_state == GAME_OVER:
        draw_text(window, "GAME OVER", FONT, (255, 0, 0), WIDTH // 2 - 100, HEIGHT // 2 - 50)
        draw_text(window, "Press R to Restart", FONT, (255, 255, 255), WIDTH // 2 - 150, HEIGHT // 2)
    elif game_state == GAME_WON:
        draw_text(window, "YOU WON!", FONT, (0, 255, 0), WIDTH // 2 - 100, HEIGHT // 2 - 50)
        draw_text(window, "Press Q to Quit", FONT, (255, 255, 255), WIDTH // 2 - 150, HEIGHT // 2)
    elif game_state == LEVEL_TRANSITION:
         draw_text(window, f"Level {current_level + 1} Complete!", FONT, (255, 255, 0), WIDTH // 2 - 150, HEIGHT // 2 - 50)
         # Optional: Add a small delay visual here


    pygame.display.update()

# --- Collision Handling ---
def handle_vertical_collision(player, objects, dy):
    collided_objects_data = [] # Store tuples of (object, collision_point) if needed later
    original_bottom = player.rect.bottom # Store position before potential adjustment

    # Check collision against all objects
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            # --- Vertical Collision Logic ---
            if dy > 0: # Player is moving down
                 # If colliding while moving down, assume landing ON TOP of the object (if it's a block)
                 # or hitting a trap from above.
                if isinstance(obj, Block): # Check if it's a solid block
                    # Force player's bottom to align with the object's top
                    player.rect.bottom = obj.rect.top
                    player.landed() # Reset vertical velocity, fall count, jump count
                    collided_objects_data.append(obj) # Mark as collided vertically
                    # print(f"Landed on Block at {obj.rect.topleft}") # Debug print

                elif obj.name in ["fire", "spike"]:
                    # Player landed on a trap
                    if obj.name == "fire":
                        if hasattr(obj, 'animation_name') and obj.animation_name == "on":
                            player.take_damage(1)
                    else: # Spike always deals damage
                        player.take_damage(1)
                    # Don't necessarily stop falling if landing on a trap (unless it's also a Block)
                    # But add to collided list if needed
                    collided_objects_data.append(obj)


            elif dy < 0: # Player is moving up
                if isinstance(obj, Block): # Check if it's a solid block
                    # Force player's top to align with the object's bottom
                    player.rect.top = obj.rect.bottom
                    player.hit_head() # Reverse velocity, reset counters
                    collided_objects_data.append(obj) # Mark as collided vertically
                    # print(f"Hit Head on Block at {obj.rect.topleft}") # Debug print

                elif obj.name in ["fire", "spike"]:
                     # Player hit a trap from below
                     if obj.name == "fire":
                         if hasattr(obj, 'animation_name') and obj.animation_name == "on":
                              player.take_damage(1)
                     else: # Spike always deals damage
                         player.take_damage(1)
                     # Add to collided list if needed
                     collided_objects_data.append(obj)


            # --- Horizontal Collision Logic (Added Check) ---
            # Sometimes vertical movement causes slight horizontal overlap too.
            # Check if player is primarily overlapping horizontally after vertical adjustment.
            # This might need further refinement if causing issues.
            # else: # If dy == 0 or vertical adjustment didn't occur
            if isinstance(obj, Block): # Only check against solid blocks here
                 # Check horizontal overlap more carefully if no vertical collision was resolved
                 # Use player's center x for clarity
                 player_center_x = player.rect.centerx
                 obj_center_x = obj.rect.centerx

                 # Check if player center is within obj bounds horizontally after any vertical adjust
                 if obj.rect.left < player.rect.centerx < obj.rect.right:
                      # If we are here, it means mask collided, but not resolved vertically.
                      # This could be a side collision during vertical movement.
                      # Let the horizontal collision handle this more precisely if needed.
                      # For now, just note the collision occurred.
                      if obj not in collided_objects_data: # Avoid duplicates
                            collided_objects_data.append(obj)
                      # print(f"Side overlap with Block {obj.rect.topleft} during vertical check") # Debug print

                 elif obj.name in ["fire", "spike"]: # Handle side collision with traps too
                    if obj not in collided_objects_data:
                        # Player brushed side of trap
                        if obj.name == "fire":
                            if hasattr(obj, 'animation_name') and obj.animation_name == "on":
                                player.take_damage(1)
                        else: # Spike always deals damage
                            player.take_damage(1)
                        collided_objects_data.append(obj)


    # Re-check vertical position *after* iterating through all objects,
    # as multiple collisions might occur. Ensure player isn't pushed below ground again.
    # This part might be overly complex - let's rely on the per-object check for now.
    # If issues persist, we might need a post-collision adjustment phase.

    return collided_objects_data # Return list of objects collided with (useful for handle_move)


def collide(player, objects, dx):
    """Checks for horizontal collision *after* moving."""
    player.move(dx, 0)
    player.update() # Update mask after moving
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
             # Check if it's a harmful object
             if obj.name in ["fire", "spike"]:
                 if obj.name == "fire":
                     if hasattr(obj, 'animation_name') and obj.animation_name == "on":
                          player.take_damage(1)
                 else:
                      player.take_damage(1)
             # If it's a solid block, mark as collided
             if isinstance(obj, Block):
                  collided_object = obj
                  break # Stop checking once a solid collision occurs

    # Move back regardless of what was hit, prevents sticking
    player.move(-dx, 0)
    player.update()
    return collided_object # Return only the *solid* object collided with horizontally


# --- Movement Handling ---
def handle_move(player, objects):
    keys = pygame.key.get_pressed()

    player.x_vel = 0 # Reset horizontal velocity each frame

    # Check for horizontal collisions *before* applying movement
    collide_left_obj = collide(player, objects, -PLAYER_VEL)
    collide_right_obj = collide(player, objects, PLAYER_VEL) # collide now returns the solid object hit

    # Apply horizontal movement based on keys and collisions
    if keys[pygame.K_LEFT] and not collide_left_obj:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not collide_right_obj:
        player.move_right(PLAYER_VEL)

    # Handle vertical collisions *after* gravity/jump velocity is applied (in player.loop)
    vertically_collided_objects = handle_vertical_collision(player, objects, player.y_vel)

    # Check for collision with the goal (ensure it wasn't handled as a block collision)
    goal_reached = False
    for obj in objects: # Check all objects again for the goal specifically
        if isinstance(obj, Goal) and pygame.sprite.collide_mask(player, obj):
            goal_reached = True
            # print("Goal Reached!") # Debug
            break

    # Damage for horizontal collisions (if not already handled vertically)
    # Note: collide() function already handles damage for traps during its check
    # We might not need extra checks here unless traps can only be hit horizontally.
    # The current collide() handles damage on horizontal overlap test.

    return goal_reached # Return True if goal is reached


# --- Level Definitions ---
# Define levels as dictionaries or lists of objects/parameters
# Coordinates are based on top-left corner. Y=0 is top, Y=HEIGHT is bottom.

level_definitions = [
    # --- LEVEL 1 ---
    {
        "background": "Blue.png",
        "player_start": (100, HEIGHT - BLOCK_SIZE * 2), # Start on the ground
        "blocks": [
            # Floor
            *[(i * BLOCK_SIZE, HEIGHT - BLOCK_SIZE) for i in range(-5, 15)],
            # Platforms
            (0, HEIGHT - BLOCK_SIZE * 3),
            (BLOCK_SIZE, HEIGHT - BLOCK_SIZE * 3),
            (BLOCK_SIZE * 3, HEIGHT - BLOCK_SIZE * 4),
            (BLOCK_SIZE * 5, HEIGHT - BLOCK_SIZE * 5),
            (BLOCK_SIZE * 7, HEIGHT - BLOCK_SIZE * 5),
            (BLOCK_SIZE * 8, HEIGHT - BLOCK_SIZE * 5),
        ],
        "fires": [
            # Place fire traps (x, y, width, height) - using original asset size
            (BLOCK_SIZE * 4, HEIGHT - BLOCK_SIZE - 64, 16, 32), # On the floor
        ],
        "spikes": [
             # Place spikes (x, y) - y adjusted automatically
             (BLOCK_SIZE * 6, HEIGHT - BLOCK_SIZE),
        ],
        "goal": (BLOCK_SIZE * 9, HEIGHT - BLOCK_SIZE * 5) # Goal Position (x, y)
    },
    # --- LEVEL 2 ---
    {
        "background": "Purple.png", # Different background
        "player_start": (50, HEIGHT - BLOCK_SIZE * 2),
        "blocks": [
             # Floor sections
            *[(i * BLOCK_SIZE, HEIGHT - BLOCK_SIZE) for i in range(-2, 4)],
            *[(i * BLOCK_SIZE, HEIGHT - BLOCK_SIZE) for i in range(8, 18)],
            # Floating platforms and walls
             (BLOCK_SIZE * 5, HEIGHT - BLOCK_SIZE * 3),
             (BLOCK_SIZE * 6, HEIGHT - BLOCK_SIZE * 4), # Step up
             (BLOCK_SIZE * 7, HEIGHT - BLOCK_SIZE * 4),
             # Wall jump section?
             (BLOCK_SIZE * 10, HEIGHT - BLOCK_SIZE * 5),
             (BLOCK_SIZE * 10, HEIGHT - BLOCK_SIZE * 6),
             (BLOCK_SIZE * 12, HEIGHT - BLOCK_SIZE * 7), # High platform
        ],
        "fires": [
             (BLOCK_SIZE * 3, HEIGHT - BLOCK_SIZE - 64, 16, 32), # Near start
             (BLOCK_SIZE * 9, HEIGHT - BLOCK_SIZE - 64, 16, 32), # On second floor part
             (BLOCK_SIZE * 6, HEIGHT - BLOCK_SIZE * 4 - 64, 16, 32), # On platform
        ],
         "spikes": [
             # Spike gap
             (BLOCK_SIZE * 4, HEIGHT - BLOCK_SIZE),
             (BLOCK_SIZE * 7, HEIGHT - BLOCK_SIZE),
             # Spike on platform
             (BLOCK_SIZE * 11, HEIGHT - BLOCK_SIZE * 4), # Added difficulty
         ],
         "goal": (BLOCK_SIZE * 14, HEIGHT - BLOCK_SIZE * 2) # Goal further away
    }
]

# --- Level Loading Function ---
def load_level(level_index):
    if level_index >= len(level_definitions):
        print("Error: Level index out of bounds!")
        return None, None, None, None # Indicate error

    level_data = level_definitions[level_index]

    # Load Background
    background, bg_image = get_background(level_data["background"])

    # Create Player
    player_start_pos = level_data["player_start"]
    # Assuming player sprite is roughly 32x32, scaled to 64x64
    player = Player(player_start_pos[0], player_start_pos[1], 64, 64) # Use scaled size

    # Create Blocks
    blocks = [Block(pos[0], pos[1], BLOCK_SIZE // 2) for pos in level_data["blocks"]] # Pass original size

    # Create Fires
    fires = []
    for fire_data in level_data.get("fires", []): # Use .get for safety
         fire = Fire(fire_data[0], fire_data[1], fire_data[2], fire_data[3])
         fire.on() # Make fires active by default in levels
         fires.append(fire)


    # Create Spikes
    spikes = [Spike(pos[0], pos[1]) for pos in level_data.get("spikes", [])]

    # Create Goal
    goal_pos = level_data["goal"]
    goal = Goal(goal_pos[0], goal_pos[1])

    # Combine all objects
    objects = [*blocks, *fires, *spikes, goal] # Goal is also an object for drawing/collision

    return player, objects, background, bg_image


# --- Main Game Function ---
def main(window):
    clock = pygame.time.Clock()
    current_level_index = 0
    game_state = PLAYING

    # Load initial level
    load_result = load_level(current_level_index)
    if load_result is None:
        print("Failed to load initial level. Exiting.")
        pygame.quit()
        quit()
    player, objects, background, bg_image = load_result

    active_objects = [obj for obj in objects if hasattr(obj, 'loop')] # Objects that need updating (like Fire)


    offset_x = 0
    scroll_area_width = 200

    run = True
    while run:
        clock.tick(FPS)

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if event.type == pygame.KEYDOWN:
                if game_state == PLAYING:
                    if event.key == pygame.K_SPACE: # Keep jump control simple
                        player.jump()
                elif game_state == GAME_OVER:
                     if event.key == pygame.K_r: # Restart game from level 1
                         current_level_index = 0
                         game_state = PLAYING
                         offset_x = 0
                         load_result = load_level(current_level_index)
                         if load_result:
                             player, objects, background, bg_image = load_result
                             active_objects = [obj for obj in objects if hasattr(obj, 'loop')]
                         else: # Failed loading after restart attempt
                              run = False
                              break
                elif game_state == GAME_WON:
                     if event.key == pygame.K_q: # Quit game
                          run = False
                          break

        if not run: # Exit loop if run became False
            break


        # --- Game Logic based on State ---
        if game_state == PLAYING:
            # Update Player
            player.loop(FPS)

             # Update active objects (like Fire animations)
            for obj in active_objects:
                 obj.loop(FPS) # Pass FPS if needed by the object's loop

            # Handle Movement and Goal Check
            goal_reached = handle_move(player, objects) # Pass all objects for collision checks

            # Check for Death
            if player.current_health <= 0:
                game_state = GAME_OVER
                # print("Player Died!") # Debug
                # No need to reset here, GAME_OVER state handles display/restart

            # Check for Level Completion
            elif goal_reached:
                 current_level_index += 1
                 if current_level_index < len(level_definitions):
                     # Optional: Add a brief transition state/delay
                     # game_state = LEVEL_TRANSITION
                     # pygame.time.delay(1000) # Pause for 1 second (example)

                     # Load next level
                     game_state = PLAYING # Go back to playing state for next level
                     offset_x = 0 # Reset scroll
                     load_result = load_level(current_level_index)
                     if load_result:
                         player, objects, background, bg_image = load_result
                         active_objects = [obj for obj in objects if hasattr(obj, 'loop')]
                     else: # Failed loading next level
                          print(f"Error loading level {current_level_index + 1}")
                          run = False # Or handle error differently
                 else:
                     game_state = GAME_WON # All levels completed
                     # print("Game Won!") # Debug

            # Update scroll offset
            if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0):
                offset_x += player.x_vel
            elif ((player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
                offset_x += player.x_vel # x_vel is negative, so this subtracts


        # --- Drawing ---
        # Draw regardless of state to show messages (Game Over, Win)
        draw(window, background, bg_image, player, objects, offset_x, current_level_index, game_state)


    pygame.quit()
    quit()


# --- Entry Point ---
if __name__ == "__main__":
    # Ensure 'assets' directory exists relative to the script
    if not os.path.isdir("assets"):
         print("Error: 'assets' directory not found in the current location.")
         print("Please make sure the 'assets' folder with all subfolders (Background, MainCharacters, Items, Traps, etc.) is in the same directory as the python script.")
         quit()
    elif not os.path.exists(join("assets", "MainCharacters", "NinjaFrog")):
         print("Error: 'assets/MainCharacters/NinjaFrog' directory not found.")
         print("Please ensure the character assets are correctly placed.")
         quit()
    elif not os.path.exists(join("assets", "Terrain", "Terrain.png")):
          print("Error: 'assets/Terrain/Terrain.png' not found.")
          quit()
    # Add more checks if necessary for specific assets used

    main(window)