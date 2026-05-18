import os
from PIL import Image, ImageOps

def regenerate_icons():
    input_path = 'media/profile_pictures/1847 Logo.png'
    output_dir = 'Farmers/static/Farmers/pwa/icons'
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_path):
        print(f'Error: Input file {input_path} not found.')
        return

    # Load image and ensure RGBA
    img = Image.open(input_path).convert('RGBA')
    datas = img.getdata()

    # Remove light-gray background
    # (R,G,B all > 180 and max-min < 25)
    newData = []
    for item in datas:
        r, g, b, a = item
        if r > 180 and g > 180 and b > 180 and max(r, g, b) - min(r, g, b) < 25:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    img.putdata(newData)

    # Trim transparent borders
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    def create_icon(size, scale_factor, filename):
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        
        # Calculate target size based on scale factor
        target_side = int(size * scale_factor)
        
        # Scale original image to fit within target_side
        img_aspect = img.width / img.height
        if img_aspect > 1:
            w = target_side
            h = int(target_side / img_aspect)
        else:
            h = target_side
            w = int(target_side * img_aspect)
        
        resized_img = img.resize((w, h), Image.Resampling.LANCZOS)
        
        # Paste centered
        offset = ((size - w) // 2, (size - h) // 2)
        canvas.paste(resized_img, offset, resized_img)
        
        path = os.path.join(output_dir, filename)
        canvas.save(path, 'PNG')
        print(f'Created: {path}')
        return path

    outputs = [
        create_icon(192, 0.72, 'icon-192-maskable.png'),
        create_icon(512, 0.72, 'icon-512-maskable.png'),
        create_icon(512, 0.82, 'icon-512-any.png'),
        create_icon(180, 0.82, 'apple-touch-icon-180.png')
    ]

if __name__ == '__main__':
    regenerate_icons()
