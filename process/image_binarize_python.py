from PIL.Image import Image
from juiz import juiz_process

@juiz_process
def image_binarize_python(img: Image, threshold: int = 128) -> Image:
    # グレーにしてから白黒にする。次の段へ渡すため RGB に戻しておく
    return img.convert("L").point(lambda v: 255 if v >= threshold else 0).convert("RGB")
