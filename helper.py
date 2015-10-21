def format_ns(ns):
    s, ns = divmod(ns, 1000000000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)

    return "%u:%02u:%02u.%09u" % (h, m, s, ns)
