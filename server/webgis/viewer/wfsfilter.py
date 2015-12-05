from owslib.wfs import WebFeatureService
import json
import urllib, urlparse
import logging
from owslib.fes import PropertyIsLike, And, Or, PropertyIsEqualTo, \
    PropertyIsNotEqualTo, PropertyIsGreaterThanOrEqualTo, \
    PropertyIsLessThanOrEqualTo, PropertyIsBetween, FilterRequest
from owslib.namespaces import Namespaces

from lxml import etree


def get_namespaces():
    n = Namespaces()
    ns = n.get_namespaces(["ogc"])
    ns[None] = n.get_namespace("ogc")
    return ns
namespaces = get_namespaces()

def webgisfilter(mapserv, layer, maxfeatures=None, startindex=None, bbox=None,
        filters=None):
    """webgis wfs client

    Each filter format should look like:

    {
        'attribute': ATTRIBUTE_NAME, # e.g. 'NAME'
        'operator': OPERATOR, # e.g. '='
        'value': VALUE # e.g. 'Prague'
    }

    Operators: = != ~ IN

    :param str mapserv: url to mapserver
    :param str layer: layer name
    :param int maxfeatures: number of returned features
    :param int startindex: starting feature index
    :param Tupple.<dict> filters: tupple of filters
    :return: json-encoded result
    :rtype: dict
    """

    mywfs = WebFeatureService(url=mapserv, version='1.0.0')
    fes = None
    if filters:
        fes = get_filter_root(get_filter_fes(filters))
        fes = etree.tostring(fes)
    layer_data = mywfs.getfeature(typename=[layer],
                                  filter=fes,
                                  bbox=bbox,
                                  featureid=None,
                                  outputFormat="GeoJSON",
                                  maxfeatures=maxfeatures,
                                  startindex=startindex)
    data = json.load(layer_data)

    for feature in data['features']:
        feature.pop('geometry') 

    return data

def get_filter_fes(filters, logical_operator=And):
    """Create filter encoding specification (OGC FES) object based on given
    filters

    :param Tupple.<dict> filters: tupple of filters
    :param logical_operator: owslib.fes.And or owslib.fes.Or
    :return: filter encoding specification
    :rtype: owslib.fes.AND
    """

    conditions = []
    filter_request = None

    for myfilter in filters:
        if myfilter['operator'] == '=':
            conditions.append(
                    PropertyIsEqualTo(
                        myfilter['attribute'], myfilter['value']))
        elif myfilter['operator'] == '!=':
            conditions.append(
                    PropertyIsNotEqualTo(
                        myfilter['attribute'], myfilter['value']))
        elif myfilter['operator'] == '~':
            conditions.append(
                    PropertyIsLike(
                        myfilter['attribute'], myfilter['value']))
        elif myfilter['operator'] == '>':
            conditions.append(
                    PropertyIsGreaterThanOrEqualTo(
                        myfilter['attribute'], myfilter['value']))
        elif myfilter['operator'] == '<':
            conditions.append(
                    PropertyIsLessThanOrEqualTo(
                        myfilter['attribute'], myfilter['value']))
        elif myfilter['operator'] == 'IN':
            new_filters = [{
                'value': value,
                'operator': '=',
                'attribute': myfilter['attribute']}\
                        for value in myfilter['value'].split(',')]
            conditions.append(get_filter_fes(new_filters, logical_operator=Or))

    if len(conditions) > 1:
        filter_request = logical_operator(conditions)
    else:
        filter_request = conditions[0]

    return filter_request

def get_filter_root(condition):
    """Return given condition enveloped with <ogc:Filter> tag

    :param (owslib.fes.OgcExpression|owslib.fes.BinaryComparisonOpType) condition: 
    """

    root = etree.Element("{{}}Filter".format(namespaces['ogc']))
    root.append(condition.toXML())
    return root
