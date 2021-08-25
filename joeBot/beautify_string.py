from decimal import Decimal

def readable(nb, rounding=0):
    if rounding == 0:
        return '{:,}'.format(int(nb)).replace(',', ' ')
    else:
        return '{:,}'.format(round(nb, rounding)).replace(',', ' ')


def human_format(num):
    magnitude = 0
    if num < 0.01:
        return getScientific(num, 3)
    elif num < 1:
        return round(num, 4)
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return '%.2f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])

def getScientific(n, rounding=-1):
    return "%.{}E".format(rounding) % Decimal(str(n))