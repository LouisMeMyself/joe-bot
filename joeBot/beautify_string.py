def readable(nb, n_decimals=0):
    if n_decimals == 0:
        return '{:,}'.format(int(nb))
    else:
        return '{:,}'.format(round(nb, n_decimals))


def humanFormat(nb, n_decimals):
    magnitude = 0
    while abs(nb) >= 1000:
        magnitude += 1
        nb /= 1000.0
    # add more suffixes if you need them
    return '%.{}f%s'.format(n_decimals) % (nb, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def smartRounding(nb, n_decimals=2):
    if nb < 1:
        if "e" in str(nb):
            return roundScientific(nb, n_decimals)
        else:
            decimals = str(nb)[2:]
            nb = int(decimals)
            n_zero = len(decimals) - len(str(nb))
            round_up = int(str(nb)[n_decimals]) // 5
            return "0.{}{}".format("0" * n_zero, int(str(nb)[:n_decimals]) + round_up)
    return humanFormat(nb, n_decimals)


def roundScientific(nb, decimals=-1):
    nb, exp = str(nb).split("e")
    if decimals == -1:
        return "{}e{}".format(nb, exp)
    else:
        return "{}e{}".format(nb[:decimals + 2], exp)
