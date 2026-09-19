from PIL import Image
import os

def make_square(image_path, output_path, size=256, fill_color=(0, 0, 0, 0), mode="pad"):
    """
    Convert an image to a square format.

    Args:
        image_path: path to the source image (any format Pillow supports).
        output_path: where to save the result (extension determines format,
                      e.g. .png to keep transparency).
        size: final width/height in pixels (output is size x size).
        fill_color: RGBA background color used for padding (default: transparent).
                    Use e.g. (255, 255, 255, 255) for white.
        mode: "pad"  -> keep whole image, add padding to fill square (no cropping)
              "crop" -> crop to square (center crop), no padding, no distortion
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    if mode == "pad":
        # Scale so the larger side fits within `size`, then pad the rest
        scale = size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        square = Image.new("RGBA", (size, size), fill_color)
        offset = ((size - new_w) // 2, (size - new_h) // 2)
        square.paste(img, offset, img)

    elif mode == "crop":
        # Scale so the smaller side fits `size`, then center-crop
        scale = size / min(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        left = (new_w - size) // 2
        top = (new_h - size) // 2
        square = img.crop((left, top, left + size, top + size))

    else:
        raise ValueError("mode must be 'pad' or 'crop'")

    square.save(output_path)
    return output_path


def batch_make_square(input_dir, output_dir, size=256, mode="pad", fill_color=(0, 0, 0, 0)):
    """Process every image file in input_dir and save square versions to output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")

    for fname in os.listdir(input_dir):
        if fname.lower().endswith(exts):
            in_path = os.path.join(input_dir, fname)
            # Always save as PNG to preserve transparency consistently
            out_name = os.path.splitext(fname)[0] + ".png"
            out_path = os.path.join(output_dir, out_name)
            make_square(in_path, out_path, size=size, mode=mode, fill_color=fill_color)
            print(f"Saved: {out_path}")

batch_make_square("Images","Images_changed")