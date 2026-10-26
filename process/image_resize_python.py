from PIL.Image import Image
from juiz import juiz_process

@juiz_process
def image_resize_python(img: Image, width: int = 320, height: int = 240) -> Image:
    return img.resize((width, height))
