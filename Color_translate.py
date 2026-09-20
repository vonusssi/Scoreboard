def hex_to_rgba(color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
	"""Convert a six-digit hex color to Kivy's normalized RGBA format."""
	color = color.removeprefix("#")

	if len(color) != 6:
		raise ValueError("color must contain exactly 6 hexadecimal digits")

	try:
		red, green, blue = (
			int(color[index:index + 2], 16) / 255
			for index in (0, 2, 4)
		)
	except ValueError as error:
		raise ValueError("color must contain only hexadecimal digits") from error

	if not 0 <= alpha <= 1:
		raise ValueError("alpha must be between 0 and 1")

	return red, green, blue, alpha

print(hex_to_rgba("ffe6a7"))

#Some colors listed in comments:
# Brown  or Dark green? 386641
# Light Green 0.76, 0.94, 0.70, 1
# 