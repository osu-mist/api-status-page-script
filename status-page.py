import json
import sys
from urllib.parse import urlparse

import requests


class StatusPage:
    def __init__(self):
        config_data_file = open(sys.argv[1])
        log_file = open(sys.argv[2])
        self.config_json = json.load(config_data_file)
        self.log_json = json.load(log_file)
        self.access_token = self.config_json['access_token']
        self.base_url = self.config_json['base_url']
        self.header = {'x-cachet-token': self.access_token}
        self.broken_components = []
        self.open_incidents = []

    def get_broken_components(self):
        response = requests.get(f'{self.base_url}/components', self.header)
        for component in response.json()['data']:
            status = component['status']
            if status != 1:
                self.broken_components.append(component)

    def get_all_open_incidents(self):
        response = requests.get(f'{self.base_url}/incidents', self.header)
        for incident in response.json()['data']:
            status = incident['status']
            if status != 4:
                self.open_incidents.append(incident)

    def update_incident_status(self):
        # map api version and name to Cachet component IDs
        component_map = {
            'v1/academic-disciplines': 3,
            'v1/advisors': 4,
            'v1/xeapps': 5,
            'v1/beaverbus': 6,
            'v1/directory': 7,
            'v2/directory': 8,
            'v1/finance': 9,
            'v1/hr': 10,
            'v1/identify': 11,
            'v1/locations': 12,
            'v1/oauth2': 13,
            'v1/onbase': 14,
            'v1/persons': 15,
            'v1/staff-fee-privilege': 16,
            'v1/students': 17,
            'v1/terms': 18,
            'v1/textbooks': 19
        }

        # then, if there are any test failures, open an incident if there is none open already
        for failed_test in self.log_json['failed_tests']:
            already_reported = False
            parsed_url = urlparse(failed_test['base_url'])
            split_path = parsed_url.path.split('/')
            api_version = split_path[1]
            api_name = split_path[2]
            version_and_name = f'{api_version}/{api_name}'

            if version_and_name in component_map:
                component_id = component_map[version_and_name]
                for incident in self.open_incidents:
                    if component_id == incident['component_id']:
                        already_reported = True
                if not already_reported:
                    body = {
                        'name': failed_test['base_url'],
                        'message': f'Jenkins has reported an issue with {api_name} api {api_version}.\
                                     Failed test url: {failed_test["base_url"]}',
                        'status': 1,
                        'visible': 1,
                        'component_id': component_id,
                        'component_status': 2,

                    }
                    print('Posting New Incident:')
                    response = requests.post(f'{self.base_url}/incidents', headers=self.header, data=body)
                    print(response)

        # then parse through passed tests and resolve any previously opened incidents if it shares the same endpoint
        for passed_test in self.log_json['passed_tests']:
            already_reported = False
            parsed_url = urlparse(passed_test['base_url'])
            split_path = parsed_url.path.split('/')
            api_version = split_path[1]
            api_name = split_path[2]
            version_and_name = f'{api_version}/{api_name}'
            incident_id = None

            if version_and_name in component_map:
                component_id = component_map[version_and_name]
                for incident in self.open_incidents:
                    if component_id == incident['component_id'] \
                            and passed_test['base_url'] == incident['name']:
                        already_reported = True
                        incident_id = incident['id']

                if already_reported:
                    body = {
                        'status': 4,
                        'component_id': component_id,
                        'component_status': 1
                    }
                    print('Updating Incident Status:')
                    response = requests.put(f'{self.base_url}/incidents/{incident_id}', headers=self.header, data=body)
                    print(response)

    def update_component_status(self):
        for broken_api in self.broken_components:
            for open_incident in self.open_incidents:
                if open_incident['component_id'] == broken_api['id']:
                    body = {'status': 2}
                    requests.put(f'{self.base_url}/components/{broken_api["id"]}', headers=self.header, data=body)
                    break


if __name__ == '__main__':
    status_page = StatusPage()
    # get incidents, then create/update incidents
    status_page.get_all_open_incidents()
    status_page.update_incident_status()

    # get open incidents again after they are updated
    status_page.get_all_open_incidents()

    # get all apis with reported issues and reassign status based on if there's any open incidents
    status_page.get_broken_components()
    status_page.update_component_status()
