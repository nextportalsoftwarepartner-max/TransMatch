from PIL import Image, ImageDraw

def create_gradient(width, height, color1, color2):
    gradient = Image.new('RGB', (width, height), color=color1)
    draw = ImageDraw.Draw(gradient)

    for y in range(height):
        r = int(color1[0] + (color2[0] - color1[0]) * (y / height))
        g = int(color1[1] + (color2[1] - color1[1]) * (y / height))
        b = int(color1[2] + (color2[2] - color1[2]) * (y / height))
        draw.line((0, y, width, y), fill=(r, g, b))
    return gradient

# Generate the gradient image
gradient_image = create_gradient(800, 600, (92, 92, 238), (154, 154, 255))  # Purple to light purple

# Save the image with the correct path
gradient_image.save(r"D:\CHIANWEILON\Software_Dev\TransMatch\gradient_background.png")
print("Gradient image created and saved successfully.")
