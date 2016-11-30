from .sina import Sina
from .leverfun import Leverfun


def use(source=None):
    if source in ['sina']:
        return Sina()
    elif source in ['leverfun', 'lf']:
        return Leverfun()
    elif source is None:
        return Sina()
    else:
        raise RuntimeError('不支持的行情source{}'.format(source))
