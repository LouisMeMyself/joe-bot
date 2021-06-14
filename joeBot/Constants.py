# Server
TEST_SERVER_ID = 852632556137611334
LIVE_SERVER_ID = 830990443457806347

# Emojis
EMOJI_CHECK = "✅"
EMOJI_CROSS = "❌"
EMOJI_ACCEPT_GUIDELINES = "✅"

# Commands
COMMAND_BEARD = "beard"
PROFILE_PICTURE_COMMAND = "!joepic"

# Roles
ROLE_FOR_CMD = "Bot Master"
VERIFIED_USER_ROLE = "Joe"

# Errors
ERROR_ON_PROFILE_PICTURE ="""How to use joeBot for profile pictures:

1. Choose a HEX color or a RGB color in this format: `#00FFFF`. [(color picker)](https://htmlcolorcodes.com/color-picker/)

2. Enter this command `!joepic [color]` for the color of the jacket and `!joepic [color] [color]` for the color of the jacket and the skin with your selected color(s).
   Add `beard [color]` at the end of the command to also change the color of the beard!

3. Save image + add as your Discord profile photo !"""


class Channels:
    def __init__(self, server_id, bot):
        if server_id == LIVE_SERVER_ID:
            server_nb = 0
        elif server_id == TEST_SERVER_ID:
            server_nb = 1
        else:
            raise ValueError

        self.__channel = {}
        for server in bot.guilds:
            if server.id == server_id:
                for channel in server.channels:
                    self.__channel[channel.id] = channel

        self.JOEPIC_CHANNEL_ID = (852663823982788678, 852632612451123221)[server_nb]  # "👨🏻-profile-pictures"
        self.SUGGESTION_CHANNEL_ID = (843655526906593380, 852632695522459709)[server_nb]  # "👨🏻-profile-pictures"
        self.GUIDELINES_CHANNEL_ID = (830990443910529047, 852636664869158912)[server_nb]  # "📚-guidelines-and-resources"
        self.COMMAND_CHANNEL_ID = (852658830987100190, 853397123713204244)[server_nb]  # "🤖-bot-commands"
        self.GUIDELINES_MSG_ID = (843668142764589076, 852636768788021288)[server_nb]

    def get_channel(self, channel_id):
        return self.__channel[channel_id]

