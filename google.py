from urllib import urlencode
from urllib2 import urlopen
import logging

logger = logging.getLogger("ggeocoder")

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json

class Google(object):
    """Geocoder using the Google Maps API."""
    
    def __init__(self, api_key=None, domain='maps.googleapis.com',
                 resource=None, format_string='%s', output_format='json',
                 sensor=False
                ):
        """
        Google geocoder uses API v3 and supports reverse geo-coding

        
        Initialize a customized Google geocoder with location-specific
        address information and your Google Maps API key.

        ``api_key`` should be a valid Google Maps API key. Required as per Google Geocoding API
        V2 docs, but the API works without a key in practice.

        ``domain`` should be the localized Google Maps domain to connect to. The default
        is 'maps.google.com', but if you're geocoding address in the UK (for
        example), you may want to set it to 'maps.google.co.uk' to properly bias results.

        ``resource`` is DEPRECATED and ignored -- the parameter remains for compatibility
        purposes.  The supported 'maps/geo' API is used regardless of this parameter.

        ``format_string`` is a string containing '%s' where the string to
        geocode should be interpolated before querying the geocoder.
        For example: '%s, Mountain View, CA'. The default is just '%s'.
        
        ``output_format`` (DEPRECATED) can be 'json', 'xml', or 'kml' and will
        control the output format of Google's response. The default is 'json'. 'kml' is
        an alias for 'xml'.

        ``sensor`` (required) indicates whether or not the geocoding request comes from a 
        device with a location sensor. This value must be either true or false.
        """

        if resource != None:
            from warnings import warn
            warn('geopy.geocoders.google.GoogleGeocoder: The `resource` parameter is deprecated '+
                 'and now ignored. The Google-supported "maps/geo" API will be used.', DeprecationWarning)

        self.api_key = api_key
        self.domain = domain
        self.format_string = format_string
        self.sensor = str(sensor).lower()
        
        if output_format:
            supported_formats = ('json',)
            if output_format not in supported_formats:
                raise ValueError('if defined, `output_format` must be one of: %s' % supported_formats)
            self.output_format = output_format
        else:
            self.output_format = "json"

    @property
    def url(self):
        domain = self.domain.strip('/')
        return "http://%s/maps/api/geocode/%s?%%s" % (domain, self.output_format)

    def geocode(self, string, exactly_one=True):
        params = {'address': self.format_string % string,
                  'sensor': self.sensor,
                  }
        
        if self.api_key:
            params['key'] = self.api_key
        
        url = self.url % urlencode(params)
        return self.geocode_url(url, exactly_one)

    def reverse(self, coord, exactly_one=True):
        (lat,lng) = coord
        params = {'latlng': self.format_string % lat+','+self.format_string % lng,
                  'sensor': self.sensor,
                 }

        url = self.url % urlencode(params)
        return self.geocode_url(url, exactly_one)

    def geocode_url(self, url, exactly_one=True):
        ## preserve "," in the query url
        url = url.replace("%2C", ",")
        logger.debug("Fetching %s..." % url)

        page = urlopen(url)
        
        dispatch = getattr(self, 'parse_' + self.output_format)
        status, results = dispatch(page, exactly_one)
        logger.debug("...%s" % status)
        return results

    def parse_json(self, page, exactly_one=True):
        ##TODO: decode page
        doc = json.loads(page.read())
        results = doc.get('results', [])
        status_code = doc.get("status", 'Empty status')

        if len(results) == 0:
            # Got empty result. Parse out the status code and raise an error if necessary.
            self.check_status_code(status_code)
            return None
        
        def parse_place(place):
            formatted_address = place.get('formatted_address')
            lat = place['geometry']['location']['lat']
            lng = place['geometry']['location']['lng']
            return (formatted_address, (lat, lng), place)
        
        if exactly_one:
            return status_code, parse_place(results[0])
        else:
            return status_code, [parse_place(place) for place in results]

    def check_status_code(self, status_code):
        if status_code != 'OK':
            raise GeocoderResultError(status_code)

import unittest
from random import sample
import numpy as np

class TestGoogleGeocoder(unittest.TestCase):
    def setUp(self):
        GOOGLE_KEY = None
        self.geocoder = Google(GOOGLE_KEY, output_format='json')

    def test_geocoding(self):
        address_str = "1600 Pennsylvania Ave, Washington DC"
        coord = (38.8976777, -77.036517)
        address = u"1600 Pennsylvania Ave NW, Washington, DC 20502, USA"
        results = self.geocoder.geocode(address_str)
        assert len(results) == 3
        assert results[0] == address
        assert np.allclose( np.array(results[1]), np.array(coord), atol=1e-3 )

    def test_reverse_geocoding(self):
        coord = (38.8976777, -77.036517)
        address = u"1600 Pennsylvania Ave NW, Washington, DC 20502, USA"
        results = self.geocoder.reverse(coord)
        assert len(results) == 3
        assert results[0] == address
        assert np.allclose( np.array(results[1]), np.array(coord), atol=1e-3 )

if __name__ == '__main__':
    unittest.main()

