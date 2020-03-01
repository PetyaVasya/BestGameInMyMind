import pygame
import Game
import json
import UI
import ptext

from constants import FPS

map = json.loads(open("test.json").read())


def main():
    pygame.init()
    pygame.font.init()
    size = width, height = 800, 600
    screen = pygame.display.set_mode(size)
    game = Game.Game()
    game.set_surface(screen)
    game.init_pygame_variables()
    running = True
    clock = pygame.time.Clock()
    game.create_fight(map)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                game.on_click(pygame.Vector2(event.pos))
                pass
        pressed = pygame.key.get_pressed()
        game.buttons_handler(pressed)
        game.tick()
        game.flip()
        if pygame.mouse.get_focused():
            game.mouse_flip(pygame.Vector2(pygame.mouse.get_pos()))
        pygame.display.flip()
        clock.tick(FPS)
        # size = width, height = pygame.display.get_surface().get_size()


def test_main():
    pygame.init()
    pygame.font.init()
    size = width, height = 800, 600
    # size = pygame.Vector2(size)
    screen = pygame.display.set_mode(size)
    size = pygame.Vector2(size)
    # game = Game.Game()
    # game.set_surface(screen)
    # game.init_pygame_variables()
    running = True
    clock = pygame.time.Clock()
    # game.create_fight(map)
    new = Game.ScreensSystem(screen)


    def func():
        new.current = "second"


    def second():
        new.current = "main"


    new.add_screen("main", Game.Screen(size).add_object(pygame.Vector2(size.x * 0.6, size.y * 0.3), UI.Button(None, None).set_background(ptext.getsurf("Second")).set_action(func))) \
        .add_screen("second", Game.Screen(size).add_object(pygame.Vector2(size.x * 0.6, size.y * 0.5),
                                                         UI.Button(None, None).set_background(
                                                             ptext.getsurf("First")).set_action(
                                                             second)))
    new.current = "main"
    while running:
        screen.fill(pygame.Color("black"))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # game.on_click(pygame.Vector2(event.pos))
                new.get_click(event.pos)

        # pressed = pygame.key.get_pressed()
        # game.buttons_handler(pressed)
        # game.tick()
        # game.flip()
        # if pygame.mouse.get_focused():
        #     game.mouse_flip(pygame.Vector2(pygame.mouse.get_pos()))
        new.flip()
        pygame.display.flip()
        clock.tick(FPS)
        # size = width, height = pygame.display.get_surface().get_size()

if __name__ == "__main__":
    main()
    # test_main()
