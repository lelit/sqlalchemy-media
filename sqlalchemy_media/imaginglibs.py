from .exceptions import OptionalPackageRequirementError
from .optionals import ensure_pil, ensure_wand


ImageFactory = None


def use_wand():
    "Use Wand as underlying imaging library."

    global ImageFactory

    ensure_wand()

    from wand.image import Image

    ImageFactory = Image

    return Image


def use_pil():
    "Use Pillow as underlying imaging library."

    global ImageFactory

    ensure_pil()

    from PIL import Image as PILImage

    class WandedPILImage:
        "Minimalistic wand-compatibility layer on top of PIL Image."

        def __init__(self, *, file):
            self._i = PILImage.open(file)

        @property
        def mimetype(self):
            return PILImage.MIME[self._i.format]

        @property
        def height(self):
            return self._i.height

        @property
        def width(self):
            return self._i.width

        @property
        def size(self):
            return self._i.size

        def __enter__(self):
            return self

        def __exit__(self, *args):
            # We cannot close the image, as that closes also its file descriptor,
            # but the associated StreamDescriptor expects it to be still operable...
            # self._i.close()
            pass

    ImageFactory = WandedPILImage

    return WandedPILImage


def get_image_factory():
    "Get selected imaging library, or use the first available among the supported ones."

    if ImageFactory is not None:
        return ImageFactory

    try:
        return use_wand()
    except OptionalPackageRequirementError:
        return use_pil()


def reset_choice():
    "Used by unittests, to reset the selection made."

    global ImageFactory

    ImageFactory = None
