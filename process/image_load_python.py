import PIL.Image
from PIL.Image import Image
from juiz import juiz_process

@juiz_process
def image_load_python(path: str = "images/sample.png") -> Image:
    # juiz に渡す画像は RGB にそろえる
    return PIL.Image.open(path).convert("RGB")
