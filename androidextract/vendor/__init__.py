class Vendor(object):
    def __init__(self, short_name, long_name):
        self.short_name = short_name
        self.long_name = long_name

    def get_short_name(self):
        return self.short_name

    def get_long_name(self):
        return self.long_name

samsung = Vendor("samsung", "Samsung")
lg = Vendor("lg", "LG")
google = Vendor("google", "Google")
asus = Vendor("asus", "ASUS")
htc = Vendor("htc", "HTC")
huawei = Vendor("huawei", "Huawei")
lenovo = Vendor("lenovo", "Lenovo")
motorola = Vendor("motorola", "Motorola")

VENDOR_LIST = [
    samsung, lg, google, asus, htc, huawei, lenovo
]

def register_vendor(vendor):
    global VENDOR_LIST

    try:
        if not issubclass(vendor, Vendor):
            raise ValueError("Vendor must be a class of type %s" % Vendor)
    except TypeError:
        raise TypeError("Vendor must be a class of type %s" % Vendor)

    # TODO: check for duplicate vendors
    VENDOR_LIST += [vendor()]

from .motorola import *

