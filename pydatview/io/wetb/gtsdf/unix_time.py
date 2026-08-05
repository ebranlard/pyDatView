from datetime import datetime, date
import numpy as np
timestamp0 = datetime(1970, 1, 1)


def to_unix(dateTime):
    try:
        return (dateTime - timestamp0).total_seconds()
    except Exception:
        if hasattr(dateTime, "__len__"):
            return [(dt - timestamp0).total_seconds() for dt in dateTime]
        raise


# def from_unix_old(sec):
#     if np.isnan(sec):
#         return datetime.utcfromtimestamp(0)
#     return datetime.utcfromtimestamp(sec)

day_dict = {}


def from_unix(sec):
    global day_dict
    if isinstance(sec, (float, int)):
        if np.isnan(sec):
            return datetime.utcfromtimestamp(0)
        return datetime.utcfromtimestamp(sec)
    else:
        sec = np.array(sec).astype(float)
        us = np.atleast_1d((sec * 1000000 % 1000000).astype(int))
        sec = sec.astype(int)
        S = np.atleast_1d(sec % 60)
        M = np.atleast_1d(sec % 3600 // 60)
        H = np.atleast_1d(sec % 86400 // 3600)
        d = np.atleast_1d(sec // 86400)
        for du in np.unique(d):
            if du not in day_dict:
                day_dict[du] = date.fromordinal(719163 + du).timetuple()[:3]
        y, m, d = zip(*[day_dict[d_] for d_ in d])
        return ([datetime(*ymdhmsu) for ymdhmsu in zip(y, m, d, H.tolist(), M.tolist(), S.tolist(), us.tolist())])
