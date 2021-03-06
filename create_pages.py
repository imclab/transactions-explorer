#!/usr/bin/env python
import sys
from distutils import dir_util

import unicodecsv
from lib.filters import digest
from lib.params import parse_args_for_create

from lib.service import Service, latest_quarter, sorted_ignoring_empty_values, Department

from lib import templates, filters
from lib.csv import map_services_to_csv_data, map_services_to_dicts

from lib.service import total_transaction_volume
from lib.slugify import slugify
from lib.templates import render, render_csv, render_search_json


OUTPUT_DIR = 'output'

templates.output_dir = OUTPUT_DIR

arguments = parse_args_for_create(sys.argv[1:])
input = arguments.services_data

filters.path_prefix = arguments.path_prefix
filters.asset_prefix = arguments.asset_prefix
filters.static_prefix = arguments.static_prefix

if arguments.static_digests:
    digest.load_digests(arguments.static_digests)

data = open(input)

reader = unicodecsv.DictReader(data)

services = [Service(details=row) for row in reader]

services_with_details = [service for service in services if service.has_details_page]

high_volume_services = [service for service in services if service.high_volume]
latest_quarter = latest_quarter(services)

departments = set(s.department for s in services)


def generate_sorted_pages(items, page_name, output_prefix, sort_orders, extra_variables={}):
    for sort_order, key in sort_orders:
        for direction in ['ascending', 'descending']:
            reverse = (direction == 'descending')
            treemap_url = "treemaps/%s/%s/%s" % (output_prefix, sort_order, direction)
            variables = dict({
                'items': sorted_ignoring_empty_values(items, key=key,
                                                      reverse=reverse),
                'treemap_url': treemap_url,
                'latest_quarter': latest_quarter,
                'current_sort': {
                    'order': sort_order,
                    'direction': direction
                },
            }.items() + extra_variables.items())
            render('%s.html' % page_name,
                   out="%s/%s/%s.html" % (output_prefix, sort_order, direction),
                   vars=variables)


if __name__ == "__main__":
    render("about-the-data.html", "about-data.html", {})
    render("index.html", "index.html", {
        'departments_count': len(departments),
        'services_count': len(services),
        'total_transactions': total_transaction_volume(services)
    })
    for service in services_with_details:
        render('service_detail.html',
               out="%s.html" % service.link,
               vars={'service': service,
                     'department': Department(service.department, [service]),
                     'latest_quarter': latest_quarter })

    sort_orders = [
        ("by-name", lambda service: service.name_of_service),
        ("by-department", lambda service: service.abbr.lower()),
        ("by-total-cost", lambda service: service.latest_kpi_for('cost')),
        ("by-cost-per-transaction", lambda service: service.latest_kpi_for('cost_per_number')),
        ("by-digital-takeup", lambda service: service.latest_kpi_for('takeup')),
        ("by-transactions-per-year", lambda service: service.latest_kpi_for('volume_num')),
    ]
    generate_sorted_pages(high_volume_services, 'high-volume-services', 'high-volume-services',
                          sort_orders)

    departments = Department.from_services(services)
    department_sort_orders = [
        ("by-department", lambda department: department.name),
        ("by-digital-takeup", lambda department: department.takeup),
        ("by-cost", lambda department: department.cost),
        ("by-data-coverage", lambda department: department.data_coverage.percentage if department.data_coverage else None),
        ("by-transactions-per-year", lambda department: department.volume),
    ]
    generate_sorted_pages(departments, 'all-services', 'all-services', department_sort_orders)

    services_sort_orders = [
        ("by-name", lambda service: service.name_of_service),
        ("by-agency", lambda service: service.agency_abbreviation.lower()),
        ("by-category", lambda service: service.category),
        ("by-transactions-per-year", lambda service: service.most_up_to_date_volume),
    ]
    for department in departments:
        generate_sorted_pages(department.services, 'department',
                              'department/%s' % slugify(department.abbr),
                              services_sort_orders, {'department': department})

    csv_map = map_services_to_csv_data(services)
    render_csv(csv_map, 'data/transaction-volumes.csv')

    json_map = map_services_to_dicts(services)
    render_search_json(json_map, 'data/search.json')

    render('search.html', 'search.html', {'latest_quarter': latest_quarter})

    # Copy the assets folder entirely, as well
    dir_util.copy_tree('assets', '%s/transactions-explorer' % OUTPUT_DIR)
