from PIL import Image, ImageDraw, ImageFont
import os

# Create a new image with a light gray background
width = 600
height = 450
color = (240, 240, 240)
img = Image.new('RGB', (width, height), color)

# Get a drawing context
draw = ImageDraw.Draw(img)

# Draw a darker gray rectangle border
border_color = (200, 200, 200)
border_width = 2
draw.rectangle([(0, 0), (width-1, height-1)], outline=border_color, width=border_width)

# Add text
text = "Property Image\nNot Available"
text_color = (150, 150, 150)

# Calculate text position (center of image)
text_bbox = draw.textbbox((0, 0), text, align="center")
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]

text_position = ((width - text_width) // 2, (height - text_height) // 2)
draw.text(text_position, text, fill=text_color, align="center")

# Save the image
img.save('static/img/placeholder.jpg', 'JPEG', quality=90)
