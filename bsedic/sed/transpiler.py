

import json


def transpile(sed):
    inputs = sed.get('inputs', {})
    data = inputs.get('data', {})
    models = inputs.get('models', {})

    tasks = sed.get('tasks', {})

    outputs = sed.get('outputs', {})
    reports = outputs.get('reports', {})
    plots = outputs.get('plots', {})

    styles = plots.get('styles', {})
    figures = plots.get('figures', {})

    import ipdb; ipdb.set_trace()

    document = {}

    return document


def test_one():
    one_path = 'tests/examples/one/sed.json'
    with open(one_path, 'r') as one_file:
        sed = json.load(one_file)

    document = transpile(sed)


if __name__ == '__main__':
    test_one()
