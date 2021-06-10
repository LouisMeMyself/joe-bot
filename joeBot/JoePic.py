import re
import discord
import numpy as np
from cairosvg import svg2png
from constants import Constants


class JoePic:
    def __init__(self):
        self.hex_regex = re.compile("^[0-9a-fA-F]{6}")
        with open("utils/joe-logo.svg", "rb") as f:
            self.joeSVG = f.read().decode("utf-8")
        self.joe_skin = str(self.joeSVG).find("#BD967F;}")
        self.joe_clothes = str(self.joeSVG).find("#DB5B54;}")
        self.joeSVG = list(self.joeSVG)


    def str2hex(self, new_color):
        if new_color.replace(" ", "").replace(",", "") == "":  # handles empty messages
            return """Please write a HEX color or a RGB color. in these formats: '#00FFFF', '00FFFF', '0 255 255' or '0,255,255\nThe command should look like this: `!joepic [color]`"""
        if new_color[0] == "#" and self.hex_regex.match(new_color[1:]) is not None and len(
                new_color) == 7:  # handles the "#XXXXXX" hex colours
            new_color = new_color[1:]
        elif " " in new_color or "," in new_color:
            if " " in new_color and "," in new_color:  # handles the "R,        G,    B" colours
                new_color = new_color.replace(" ", "")
            elif "," in new_color:  # handles the "R,G,B" colours
                new_color = np.array(new_color.split(","), dtype=int)
            elif " " in new_color:  # handles the "R G B" colours
                new_color = np.array(new_color.split(" "), dtype=int)
            if isinstance(new_color, np.ndarray) and len(new_color) == 3 and np.any(new_color >= 0) and np.any(
                    new_color <= 255):
                new_color = "%02x%02x%02x" % tuple(new_color)
            else:
                return "RGB colours are between 0 and 255 and need 3 integers, like '127 255 212' or '127,255,212'"
        if self.hex_regex.match(new_color) is not None and len(new_color) == 6:
            return new_color
        raise ValueError

    def do_profile_picture(self, content):
        try:
            if Constants.PROFILE_PICTURE_COMMAND in content:
                colors = str(content.replace(Constants.PROFILE_PICTURE_COMMAND, "")[1:])
                colors = colors.split(" ")
                if len(colors) == 6:  # R G B and R G B
                    colors = (",".join(colors[:3]), ",".join(colors[3:]))
                elif len(colors) == 2:  # Hexa/Hexa or R,G,B/R,G,B or Hexa/R,G,B or R,G,B/Hexa
                    colors = (colors[0], colors[1])
                elif len(colors) == 4:
                    if len(colors[0]) >= 6:  # Hexa/R G B
                        colors = (colors[0], ",".join(colors[1:]))
                    elif len(colors[3]) >= 6:  # R G B/Hexa
                        colors = (",".join(colors[:3]), colors[3])
                elif len(colors) == 3: #R G B
                    colors = (",".join(colors[:3]),)
                elif len(colors) == 1: #Hexa
                    colors = colors
                else:
                    raise ValueError
                self.joeSVG[self.joe_clothes + 1: self.joe_clothes + 7] = self.str2hex(colors[0])
                if len(colors) == 2:
                    self.joeSVG[self.joe_skin + 1: self.joe_skin + 7] = self.str2hex(colors[1])
                else:
                    self.joeSVG[self.joe_skin + 1: self.joe_skin + 7] = "BD967F"
            svg2png("".join(self.joeSVG), write_to="utils/joe-logo.png")
            return "Here is your personalized profile picture!", discord.File("utils/joe-logo.png")
        except ValueError:
            return "Please write a HEX color or a RGB color. in these formats: `#00FFFF`, `00FFFF`, `0 255 255` or `0,255,255`"
        except:
            return "Unexpected error..."