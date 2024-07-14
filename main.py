"""
A script to convert sprites to use their own width and height for offsets instead of frameX and frameY,
and rotate them back to their original positions if needed.

Copyright (c) 2024 IgorSou3000

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import math
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from PIL import Image

# The multiple is 4 because this tool was made mainly for another tool called PSXFunkin Characters Maker
# The default scale on that tool is usually * 0.25 (or / 4), so this ensures every sprite's position and size are
# multiples of 4, so we will be able to scale without rounding a pixel wrong.
SPRITE_SIZE_MULTIPLE = 4

@dataclass
class Sprite:
	name : str
	x : int
	y : int
	width : int
	height : int

	pos_x : int
	pos_y : int

	rotated : bool

	def __post_init__(self):
		if self.rotated:
			self.width, self.height = self.height, self.width
			self.pos_x, self.pos_y = self.pos_y, self.pos_x

	def __eq__(self, other):
		return (self.x == other.x and self.y == other.y and
				self.width == other.width and self.height == other.height and
				self.pos_x == other.pos_x and self.pos_y == other.pos_y)

def next_power_of_two(number : int):
	"""
	Return the next power of two greater than or equal to the given number.
	"""
	return 1 if number == 0 else 2 ** (number - 1).bit_length()

def next_multiple(number : int, multiple_requested : int) -> int:
	"""
	Return the next multiple of the given number.
	"""
	if number % multiple_requested:
		return number + (multiple_requested - number % multiple_requested)

	return number

def create_output_directory(input_path: str) -> str:
	"""
	Create the export directory if it doesn't exist and return its path.
	"""
	input_dir = os.path.dirname(input_path)
	export_dir = os.path.join(input_dir, "exported")

	if not os.path.isdir(export_dir):
	  os.mkdir(export_dir)

	return export_dir

def load_spritesheet(input_path: str) -> tuple:
	"""
	Load and return it the spritesheet image and XML data.
	"""
	spritesheet_image = Image.open(input_path + ".png")
	xml_tree = ET.parse(input_path + ".xml")
	xml_root = xml_tree.getroot()

	return spritesheet_image, xml_tree, xml_root

def parse_sprites(xml_root) -> list:
	"""
	Parse the XML data and create a list of sprite objects and return the list and
	the max width and max height for each sprite.
	"""
	sprite_list = []
	max_width = 0
	max_height = 0

	for sub_texture in xml_root.findall("SubTexture"):
		sprite = Sprite(
			name=sub_texture.get("name"),
			x=int(sub_texture.get("x")),
			y=int(sub_texture.get("y")),
			width=int(sub_texture.get("width")),
			height=int(sub_texture.get("height")),
			pos_x=int(sub_texture.get("frameX", 0)),
			pos_y=int(sub_texture.get("frameY", 0)),
			rotated=bool(sub_texture.get("rotated", False))
		)

		max_width = max(max_width, sprite.width - sprite.pos_x)
		max_height = max(max_height, sprite.height - sprite.pos_y)

		if sprite not in sprite_list:
		  sprite_list.append(sprite)

	max_width = next_multiple(max_width, SPRITE_SIZE_MULTIPLE)
	max_height = next_multiple(max_height, SPRITE_SIZE_MULTIPLE)

	return sprite_list, max_width, max_height

def create_new_spritesheet(sprite_list: list, max_width: int, max_height: int, spritesheet_image: Image) -> tuple:
	"""
	Create a new spritesheet image with adjusted sprite positions.
	"""
	total_area = sum(max_width * max_height for _ in sprite_list)
	new_dimensions = next_power_of_two(math.ceil(math.sqrt(total_area)))

	new_spritesheet_image = Image.new("RGBA", (new_dimensions, new_dimensions))
	new_sprite_list = []

	current_x = current_y = 0

	for sprite in sprite_list:
		if sprite.rotated:
			image = spritesheet_image.crop((sprite.x, sprite.y, sprite.x + sprite.height, sprite.y + sprite.width))
			image = image.transpose(Image.ROTATE_90)
		else:
			image = spritesheet_image.crop((sprite.x, sprite.y, sprite.x + sprite.width, sprite.y + sprite.height))

		if current_x + max_width > new_spritesheet_image.size[0]:
			current_x = 0
			current_y += max_height

		new_sprite = Sprite(
		  name=sprite.name,
		  x=current_x,
		  y=current_y,
		  width=max_width,
		  height=max_height,
		  pos_x=0,
		  pos_y=0,
		  rotated=False
		)

		new_sprite_list.append(new_sprite)
		new_spritesheet_image.paste(image, (current_x - sprite.pos_x, current_y - sprite.pos_y))
		current_x += max_width

	return new_spritesheet_image, new_sprite_list

def update_xml_with_new_sprites(xml_root, original_sprite_list, new_sprite_list) -> None:
	"""
	Update the XML data with the new sprite coordinates.
	"""
	for sub_texture in xml_root.findall("SubTexture"):
		original_sprite = Sprite(
			name=sub_texture.get("name"),
			x=int(sub_texture.get("x")),
			y=int(sub_texture.get("y")),
			width=int(sub_texture.get("width")),
			height=int(sub_texture.get("height")),
			pos_x=int(sub_texture.get("frameX", 0)),
			pos_y=int(sub_texture.get("frameY", 0)),
			rotated=bool(sub_texture.get("rotated", False))
		)

		index = original_sprite_list.index(original_sprite)
		new_sprite = new_sprite_list[index]

		sub_texture.set("x", str(new_sprite.x))
		sub_texture.set("y", str(new_sprite.y))
		sub_texture.set("width", str(new_sprite.width))
		sub_texture.set("height", str(new_sprite.height))

		# Delete attributes that won't be used anymore
		for attr in ["frameX", "frameY", "frameWidth", "frameHeight", "rotated"]:
			if attr in sub_texture.attrib:
				del sub_texture.attrib[attr]

def save_new_spritesheet_and_xml(new_spritesheet_image: Image, xml_tree: ET.ElementTree, export_dir: str, input_filename: str) -> None:
	"""
	Save the new spritesheet image and XML data.
	"""
	new_spritesheet_image.save(f"{export_dir}/{input_filename}.png")
	xml_tree.write(f"{export_dir}/{input_filename}.xml", encoding="utf-8", xml_declaration=True)

def generate_new_spritesheet(input_path : str) -> None:
	"""
	Main processing function.
	"""
	input_filename = os.path.basename(input_path)
	export_dir = create_output_directory(input_path)

	spritesheet_image, xml_tree, xml_root = load_spritesheet(input_path)
	sprite_list, max_width, max_height = parse_sprites(xml_root)
	new_spritesheet_image, new_sprite_list = create_new_spritesheet(sprite_list, max_width, max_height, spritesheet_image)

	update_xml_with_new_sprites(xml_root, sprite_list, new_sprite_list)
	save_new_spritesheet_and_xml(new_spritesheet_image, xml_tree, export_dir, input_filename)

"""
Main entry loop
"""
if __name__ == "__main__":
	generate_new_spritesheet(sys.argv[1])