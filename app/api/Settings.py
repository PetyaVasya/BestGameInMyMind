STANDARD_SPAWN_RATE = 1
STANDARD_DMG = 1
STANDARD_HP = 1
STANDARD_LIFE_TIME = 5


class SessionAttributes:

    def __init__(self, spawn_rate=STANDARD_SPAWN_RATE, dmg=STANDARD_DMG, hp=STANDARD_HP,
                 life_time=STANDARD_LIFE_TIME):
        self.spawn_rate = spawn_rate
        self.mans_dmg = dmg
        self.mans_hp = hp
        self.life_time = life_time

    def upgrade_spawn_rate(self):
        return False

    def upgrade_dmg(self):
        return False

    def upgrade_hp(self):
        return False

    def upgrade_life_time(self):
        return False
