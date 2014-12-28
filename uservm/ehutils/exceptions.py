class ElastichostsError(Exception):
    pass

by_elastic_error = {}
for ee in 'usage', 'auth', 'billing', 'missing', 'method', 'busy', 'failed', 'system', 'full':
    name = 'Elastichosts{}Error'.format(ee.title())
    globals()[name] = by_elastic_error[ee] = type(name, (ElastichostsError,), {})
del ee, name
