"""TCMB doviz kurlari (USD/EUR) cekme servisi."""
from datetime import datetime, timedelta
from urllib.request import urlopen
import xml.etree.ElementTree as ET


_CACHE = {
    'at': None,
    'data': None,
}


def _to_float(text):
    if text is None:
        return None
    s = str(text).strip().replace(',', '.')
    if not s:
        return None
    return float(s)


def get_usd_eur_rates():
    now = datetime.now()
    if _CACHE['at'] and (now - _CACHE['at']) < timedelta(minutes=15):
        return _CACHE['data']

    try:
        with urlopen('https://www.tcmb.gov.tr/kurlar/today.xml', timeout=8) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)

        def find_rate(code):
            node = root.find(f".//Currency[@CurrencyCode='{code}']")
            if node is None:
                return None
            selling = node.findtext('ForexSelling') or node.findtext('BanknoteSelling')
            buying = node.findtext('ForexBuying') or node.findtext('BanknoteBuying')
            return {'buy': _to_float(buying), 'sell': _to_float(selling)}

        data = {
            'source': 'TCMB',
            'updated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
            'USD': find_rate('USD'),
            'EUR': find_rate('EUR'),
        }
        _CACHE['at'] = now
        _CACHE['data'] = data
        return data
    except Exception:
        return _CACHE['data']
