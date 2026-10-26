from PIL.Image import Image
from juiz import juiz_process

@juiz_process
def image_white_ratio_python(img: Image) -> float:
    # 白い画素の割合 (0.0〜1.0)
    histogram = img.convert("L").histogram()
    return histogram[255] / (img.width * img.height)
