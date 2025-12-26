import random
from src.core.init import cfg, bot


class Cortana:
    """
    Represents a Cortana object with various functionalities.
    """

    def __init__(self):
        self.member = None
        self.name = None
        self.display_name = None
        self.color = None

    def init(self):
        self.member = bot.get_guild(cfg["guild_id"]).me
        self.display_name = self.member.display_name
        for name in cfg["cortana"]:
            if self.member.display_name == cfg["cortana"][name]["display_name"]:
                self.name = name
                self.color = cfg["cortana"][name]["color"]
                break

    async def shift(self, name):
        """
        Shifts the Cortana object to a different identity.

        Args:
            name (str): The name of the identity to shift to.
        """
        self.name = name
        self.display_name = cfg["cortana"][name]["display_name"]
        self.color = cfg["cortana"][name]["color"]
        with open(f"./src/assets/avatars/{self.name.lower()}.jpg", "rb") as fp:
            await bot.user.edit(avatar=fp.read())
        await self.member.edit(nick=self.display_name)
        for role in self.member.roles:
            if role.name == "Cortana":
                await role.edit(colour=self.color)
                break

    async def random_change(self):
        """
        Randomly changes the Cortana identity to a different identity.
        """
        names = list(cfg["cortana"])
        names.remove(self.name)
        await self.shift(random.choice(names))

    def get_emoji(self):
        """
        Returns the emoji associated with the current Cortana identity.

        Returns:
            str: The emoji.
        """
        return cfg["emoji"][self.name]

    def get_lyric(self, lyric_name):
        """
        Returns the lyrics associated with the given name for the current Cortana identity.

        Args:
            lyric_name (str): The name of the lyrics.

        Returns:
            str: The lyrics.
        """
        return cfg["cortana"][self.name][lyric_name]


cortana = Cortana()
