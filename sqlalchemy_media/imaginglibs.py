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
            self._i = i = PILImage.open(file)
            self._f = i.format

        @property
        def mimetype(self):
            return PILImage.MIME[self.format]

        @property
        def height(self):
            return self._i.height

        @property
        def width(self):
            return self._i.width

        @property
        def size(self):
            return self._i.size

        @property
        def format(self):
            return self._f

        @format.setter
        def format(self, format):
            if format == 'jpg':
                format = 'jpeg'
            self._f = format

        def __enter__(self):
            return self

        def __exit__(self, *args):
            # We cannot close the image, as that closes also its file descriptor,
            # but the associated StreamDescriptor expects it to be still operable...
            # self._i.close()
            pass

        def resize(self, width, height):
            self._i.thumbnail((width, height))

        def save(self, *, file):
            self._i.save(file, self.format)

        def crop(self, **cropargs):
            # TODO: this surely require many more tests!
            image = self._i
            iwidth = image.width
            iheight = image.height
            gravity = cropargs.get('gravity')
            cleft = cropargs.get('left')
            ctop = cropargs.get('top')
            cright = cropargs.get('right')
            cbottom = cropargs.get('bottom')
            cwidth = cropargs.get('width')
            cheight = cropargs.get('height')
            if gravity is None:
                if cleft is None:
                    cleft = 0
                if ctop is None:
                    ctop = 0
                if cwidth is not None and cright is not None:
                    raise ValueError('Cannot specify both "width" and "right"')
                if cright is None:
                    if cwidth is None:
                        cright = iwidth
                    else:
                        cright = cleft + cwidth
                if cheight is not None and cbottom is not None:
                    raise ValueError('Cannot specify both "height" and "bottom"')
                if cbottom is None:
                    if cheight is None:
                        cbottom = iheight
                    else:
                        cbottom = ctop + cheight
                box = (cleft, ctop, cright, cbottom)
            else:
                if cwidth is None or cheight is None:
                    raise ValueError('When "gravity" is specified "width" and "height" are mandatory')
                if gravity == 'north_west':
                    box = (0, 0, cwidth, cheight)
                elif gravity == 'north':
                    hcut = iwidth - cwidth
                    if hcut < 0:
                        hcut = 0
                    half_hcut = hcut / 2.0
                    box = (half_hcut, 0, cwidth + half_hcut, cheight)
                elif gravity == 'north_east':
                    box = (iwidth - cwidth, 0, iwidth, cheight)
                elif gravity == 'west':
                    vcut = iheight - cheight
                    if vcut < 0:
                        vcut = 0
                    half_vcut = vcut / 2.0
                    box = (0, half_vcut, cwidth, cheight + half_vcut)
                elif gravity == 'center':
                    hcut = iwidth - cwidth
                    if hcut < 0:
                        hcut = 0
                    half_hcut = hcut / 2.0
                    vcut = iheight - cheight
                    if vcut < 0:
                        vcut = 0
                    half_vcut = vcut / 2.0
                    box = (half_hcut, half_vcut, cwidth + half_hcut, cheight + half_vcut)
                elif gravity == 'east':
                    vcut = iheight - cheight
                    if vcut < 0:
                        vcut = 0
                    half_vcut = vcut / 2.0
                    box = (iwidth - cwidth, half_vcut, iwidth, cheight + half_vcut)
                elif gravity == 'south_west':
                    box = (0, iheight - cheight, cwidth, iheight)
                elif gravity == 'south':
                    hcut = iwidth - cwidth
                    if hcut < 0:
                        hcut = 0
                    half_hcut = hcut / 2.0
                    box = (half_hcut, iheight - cheight, cwidth + half_hcut, iheight)
                elif gravity == 'south_east':
                    box = (iwidth - cwidth, iheight - cheight, iwidth, iheight)
            self._i = self._i.crop(box)

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
