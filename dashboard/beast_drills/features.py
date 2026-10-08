from . import paths

def scrimmage_available() -> bool:

    return paths.is_dev_install()
